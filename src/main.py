from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Imports Modulares
from src.config_manager import load_filter_config, save_filter_config
from src.db import (
    connect_db,
    count_draws,
    get_all_draws,
    get_last_concurso,
    get_recent_draws,
    get_recent_stats,
    init_db,
    upsert_draw,
    upsert_stats,
)
from src.etl import read_initial_excel
from src.api import fetch_draw_by_concurso

import src.lotofacil.analyzer as lf_analyzer
import src.lotofacil.filters as lf_filters
import src.megasena.analyzer as ms_analyzer
import src.megasena.filters as ms_filters

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "lotofacil_analyzer_pro.db"

CONFIG_LOTOFACIL = DATA_DIR / "config_filtros_lotofacil.json"
CONFIG_MEGASENA = DATA_DIR / "config_filtros_megasena.json"

API_LOTOFACIL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_MEGASENA = "https://loteriascaixa-api.herokuapp.com/api/megasena"

console = Console()


def _show_header(lottery_type: str) -> None:
    l_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    console.print(
        Panel.fit(
            f"[bold green]Loterias Pro-Analyzer: {l_name}[/bold green]\n"
            "App local em terminal para atualizar historico, analisar padroes e gerar palpites.",
            border_style="green",
        )
    )


def _bootstrap_db() -> None:
    with connect_db(DB_PATH) as conn:
        init_db(conn)


def _load_initial_excel_flow(lottery_type: str) -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, lottery_type)
        if total > 0:
            console.print("[yellow]O banco ja possui dados para esta loteria. Esta carga e recomendada apenas uma vez.[/yellow]")
            if not questionary.confirm("Deseja continuar mesmo assim?", default=False).ask():
                return

        excel_filename = "Lotofácil.xlsx" if lottery_type == "lotofacil" else "Mega-Sena.xlsx"
        default_path = APP_DIR / excel_filename

        excel_path_txt = questionary.text(
            "Caminho do arquivo Excel:",
            default=str(default_path),
        ).ask()
        if not excel_path_txt:
            return

        excel_path = Path(excel_path_txt)
        try:
            draws = read_initial_excel(excel_path, lottery_type)
        except Exception as exc:
            console.print(f"[red]Erro ao ler Excel:[/red] {exc}")
            return

        if not draws:
            console.print("[red]Nenhum sorteio valido encontrado no Excel.[/red]")
            return

        for draw in draws:
            upsert_draw(conn, lottery_type, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
            
            if lottery_type == "megasena":
                stats = ms_analyzer.calculate_draw_stats(draw["dezenas"])
            else:
                stats = lf_analyzer.calculate_draw_stats(draw["dezenas"])
                
            upsert_stats(conn, lottery_type, draw["concurso"], stats)

        conn.commit()

    console.print(f"[green]Carga concluida: {len(draws)} sorteios importados.[/green]")


def _update_from_api_flow(lottery_type: str) -> None:
    api_url = API_LOTOFACIL if lottery_type == "lotofacil" else API_MEGASENA
    with connect_db(DB_PATH) as conn:
        last = get_last_concurso(conn, lottery_type)
        if last is None:
            console.print("[yellow]Banco vazio. Execute primeiro a carga inicial via Excel.[/yellow]")
            return

        next_concurso = last + 1
        imported = 0

        while True:
            try:
                draw = fetch_draw_by_concurso(api_url, next_concurso, lottery_type)
            except Exception as exc:
                console.print(f"[red]Erro na API no concurso {next_concurso}:[/red] {exc}")
                break

            if draw is None:
                break

            upsert_draw(conn, lottery_type, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
            
            if lottery_type == "megasena":
                stats = ms_analyzer.calculate_draw_stats(draw["dezenas"])
            else:
                stats = lf_analyzer.calculate_draw_stats(draw["dezenas"])
                
            upsert_stats(conn, lottery_type, draw["concurso"], stats)
            imported += 1
            next_concurso += 1

        conn.commit()

    if imported == 0:
        console.print("[cyan]Nenhum concurso novo encontrado no momento.[/cyan]")
    else:
        console.print(f"[green]Atualizacao concluida: {imported} novos concursos adicionados.[/green]")


def _render_analysis_tables(analysis: dict, lottery_type: str) -> None:
    # Tabela completa ordenada
    freq_table = Table(title="Tabela de Frequência Completa Ordenada", show_header=True, header_style="bold green")
    freq_table.add_column("Dezena", justify="right")
    freq_table.add_column("Frequência", justify="right")
    freq_table.add_column("Frequência (%)", justify="right")
    freq_table.add_column("Atraso Atual", justify="right")
    freq_table.add_column("Categoria")

    for item in analysis["frequencia_completa"]:
        freq_table.add_row(
            str(item["Dezena"]),
            str(item["Frequência"]),
            f"{item['Frequência (%)']}%",
            str(item["Atraso Atual"]),
            item["Categoria"]
        )

    console.print(freq_table)

    if lottery_type == "lotofacil":
        ciclo = analysis["ciclo"]
        console.print(f"\n[bold yellow]Ciclo das Dezenas (Lotofácil):[/bold yellow]")
        console.print(f"Ciclo Atual: [cyan]{ciclo['ciclo_atual_numero']}[/cyan] | Concursos acumulados: [cyan]{ciclo['concursos_no_ciclo_atual']}[/cyan]")
        s_ausentes = ", ".join(f"{n:02d}" for n in ciclo["dezenas_ausentes_atual"])
        console.print(f"Dezenas Ausentes: [red]{s_ausentes}[/red]\n")

    media_table = Table(title="Medias e Modas recentes", show_header=True, header_style="bold green")
    media_table.add_column("Metrica")
    media_table.add_column("Media", justify="right")
    media_table.add_column("Moda", justify="right")

    for key, media in analysis["medias"].items():
        moda = analysis["modas"].get(key)
        media_table.add_row(key, f"{media:.2f}", "-" if moda is None else str(moda))

    console.print(media_table)


def _analysis_flow(lottery_type: str) -> None:
    window_txt = questionary.text("Quantos ultimos concursos analisar?", default="120").ask()
    if not window_txt:
        return

    try:
        window = max(10, int(window_txt))
    except ValueError:
        console.print("[red]Valor invalido para janela.[/red]")
        return

    with connect_db(DB_PATH) as conn:
        all_draws = get_all_draws(conn, lottery_type)
        recent_stats = get_recent_stats(conn, lottery_type, window)

    if not all_draws:
        console.print("[yellow]Banco vazio. Faca a carga inicial primeiro.[/yellow]")
        return

    if lottery_type == "megasena":
        analysis = ms_analyzer.sliding_window_analysis(all_draws, recent_stats, window)
    else:
        analysis = lf_analyzer.sliding_window_analysis(all_draws, recent_stats, window)
        
    _render_analysis_tables(analysis, lottery_type)

    sugestoes = analysis["sugestoes"]
    cfg_table = Table(title="Sugestoes de filtros", show_header=True, header_style="bold blue")
    cfg_table.add_column("Filtro")
    cfg_table.add_column("Sugestao")
    for key, value in sugestoes.items():
        cfg_table.add_row(key, str(value))
    console.print(cfg_table)

    config_path = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA

    if questionary.confirm("Deseja aplicar estas sugestoes?", default=True).ask():
        if lottery_type == "megasena":
            cfg = ms_filters.FilterConfig(**sugestoes)
        else:
            cfg = lf_filters.FilterConfig(**sugestoes)
        save_filter_config(config_path, cfg)
        console.print("[green]Configuracoes aplicadas com sucesso.[/green]")


def _generate_games_flow(lottery_type: str) -> None:
    config_path = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA
    cfg = load_filter_config(config_path, lottery_type)

    amount_txt = questionary.text("Quantos palpites deseja gerar?", default="5").ask()
    attempts_txt = questionary.text("Tentativas maximas?", default="300000").ask()
    if not amount_txt or not attempts_txt:
        return

    try:
        amount = max(1, int(amount_txt))
        max_attempts = max(1000, int(attempts_txt))
    except ValueError:
        console.print("[red]Valores invalidos para geracao.[/red]")
        return

    with connect_db(DB_PATH) as conn:
        draws = get_recent_draws(conn, lottery_type, 1)

    if not draws:
        console.print("[yellow]Banco vazio. Faca a carga inicial primeiro.[/yellow]")
        return

    if lottery_type == "lotofacil":
        previous = draws[-1]["dezenas"]
        with connect_db(DB_PATH) as conn:
            all_draws = get_all_draws(conn, lottery_type)
        ciclo_stats = lf_analyzer.calculate_lotofacil_cycles(all_draws)
        ausentes = ciclo_stats["dezenas_ausentes_atual"]
        games = lf_filters.generate_filtered_games(cfg, previous, amount, max_attempts, ausentes)
    else:
        with connect_db(DB_PATH) as conn:
            all_draws = get_all_draws(conn, lottery_type)
            recent_stats = get_recent_stats(conn, lottery_type, 120)
        analysis = ms_analyzer.sliding_window_analysis(all_draws, recent_stats, 120)
        hot = [item["Dezena"] for item in analysis["frequencia_completa"] if "Quente" in item["Categoria"]]
        cold = [item["Dezena"] for item in analysis["frequencia_completa"] if "Fria" in item["Categoria"]]
        games = ms_filters.generate_filtered_games(cfg, amount, max_attempts, hot, cold)

    filtro_table = Table(title="Filtros ativos", show_header=True, header_style="bold cyan")
    filtro_table.add_column("Filtro")
    filtro_table.add_column("Valor")
    for key, value in asdict(cfg).items():
        filtro_table.add_row(key, str(value))
    console.print(filtro_table)

    if not games:
        console.print("[yellow]Nenhum jogo aprovado. Aumente tentativas ou ajuste filtros.[/yellow]")
        return

    game_table = Table(title="Palpites aprovados", show_header=True, header_style="bold green")
    game_table.add_column("#", justify="right")
    game_table.add_column("Jogo")

    for idx, game in enumerate(games, start=1):
        game_table.add_row(str(idx), " - ".join(f"{n:02d}" for n in game))

    console.print(game_table)


def _show_status(lottery_type: str) -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, lottery_type)
        last = get_last_concurso(conn, lottery_type)

    status_table = Table(title=f"Status da loteria: {lottery_type}", show_header=False)
    status_table.add_row("Banco", str(DB_PATH))
    config_file = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA
    status_table.add_row("Config filtros", str(config_file))
    status_table.add_row("Total de sorteios", str(total))
    status_table.add_row("Ultimo concurso", "-" if last is None else str(last))
    console.print(status_table)


def main() -> None:
    _bootstrap_db()

    lotaria_choice = questionary.select(
        "Escolha a loteria para gerenciar:",
        choices=["1) Lotofácil", "2) Mega-Sena", "0) Sair"]
    ).ask()

    if not lotaria_choice or lotaria_choice.startswith("0"):
        console.print("[cyan]Encerrando aplicativo.[/cyan]")
        return

    lottery_type = "lotofacil" if lotaria_choice.startswith("1") else "megasena"
    _show_header(lottery_type)

    options = [
        "1) Carga inicial pelo Excel (uma vez)",
        "2) Atualizar com novos sorteios da API",
        "3) Analise dinamica (tabela ordenada e ciclo)",
        "4) Gerar palpites com pipeline de filtros",
        "5) Ver status",
        "0) Voltar"
    ]

    while True:
        choice = questionary.select("Escolha uma opcao:", choices=options).ask()
        if choice is None or choice.startswith("0"):
            break

        if choice.startswith("1"):
            _load_initial_excel_flow(lottery_type)
        elif choice.startswith("2"):
            _update_from_api_flow(lottery_type)
        elif choice.startswith("3"):
            _analysis_flow(lottery_type)
        elif choice.startswith("4"):
            _generate_games_flow(lottery_type)
        elif choice.startswith("5"):
            _show_status(lottery_type)


if __name__ == "__main__":
    main()
