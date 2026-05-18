from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.analyzer import calculate_draw_stats, sliding_window_analysis
from src.api import fetch_draw_by_concurso
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
from src.filters import FilterConfig, generate_filtered_games

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "lotofacil_analyzer_pro.db"
CONFIG_PATH = DATA_DIR / "config_filtros.json"
DEFAULT_EXCEL_PATH = APP_DIR / "Lotofácil.xlsx"
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"

console = Console()


def _show_header() -> None:
    console.print(
        Panel.fit(
            "[bold green]Lotofacil Analyzer Pro[/bold green]\n"
            "App local em terminal para atualizar historico, analisar padroes e gerar palpites.",
            border_style="green",
        )
    )


def _bootstrap_db() -> None:
    with connect_db(DB_PATH) as conn:
        init_db(conn)


def _load_initial_excel_flow() -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn)
        if total > 0:
            console.print("[yellow]O banco ja possui dados. Esta carga e recomendada apenas uma vez.[/yellow]")
            if not questionary.confirm("Deseja continuar mesmo assim?", default=False).ask():
                return

        excel_path_txt = questionary.text(
            "Caminho do arquivo Excel:",
            default=str(DEFAULT_EXCEL_PATH),
        ).ask()
        if not excel_path_txt:
            return

        excel_path = Path(excel_path_txt)
        try:
            draws = read_initial_excel(excel_path)
        except Exception as exc:
            console.print(f"[red]Erro ao ler Excel:[/red] {exc}")
            return

        if not draws:
            console.print("[red]Nenhum sorteio valido encontrado no Excel.[/red]")
            return

        for draw in draws:
            upsert_draw(conn, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
            stats = calculate_draw_stats(draw["dezenas"])
            upsert_stats(conn, draw["concurso"], stats)

        conn.commit()

    console.print(f"[green]Carga concluida: {len(draws)} sorteios importados.[/green]")
    console.print("[cyan]Dica:[/cyan] agora voce pode deletar o Excel para manter apenas o banco local.")


def _update_from_api_flow() -> None:
    with connect_db(DB_PATH) as conn:
        last = get_last_concurso(conn)
        if last is None:
            console.print("[yellow]Banco vazio. Execute primeiro a carga inicial via Excel.[/yellow]")
            return

        next_concurso = last + 1
        imported = 0

        while True:
            try:
                draw = fetch_draw_by_concurso(API_BASE_URL, next_concurso)
            except Exception as exc:
                console.print(f"[red]Erro na API no concurso {next_concurso}:[/red] {exc}")
                break

            if draw is None:
                break

            upsert_draw(conn, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
            upsert_stats(conn, draw["concurso"], calculate_draw_stats(draw["dezenas"]))
            imported += 1
            next_concurso += 1

        conn.commit()

    if imported == 0:
        console.print("[cyan]Nenhum concurso novo encontrado no momento.[/cyan]")
    else:
        console.print(f"[green]Atualizacao concluida: {imported} novos concursos adicionados.[/green]")


def _render_analysis_tables(analysis: dict) -> None:
    hot_table = Table(title="Mais sorteadas (janela)", show_header=True, header_style="bold cyan")
    hot_table.add_column("Dezena", justify="right")
    hot_table.add_column("Frequencia", justify="right")
    for dezena, freq in analysis["mais_sorteadas"]:
        hot_table.add_row(str(dezena), str(freq))

    cold_table = Table(title="Menos sorteadas (janela)", show_header=True, header_style="bold magenta")
    cold_table.add_column("Dezena", justify="right")
    cold_table.add_column("Frequencia", justify="right")
    for dezena, freq in analysis["menos_sorteadas"]:
        cold_table.add_row(str(dezena), str(freq))

    atraso_table = Table(title="Top 10 atrasos", show_header=True, header_style="bold yellow")
    atraso_table.add_column("Dezena", justify="right")
    atraso_table.add_column("Atraso (concursos)", justify="right")
    for dezena, atraso in sorted(analysis["atrasos"].items(), key=lambda item: item[1], reverse=True)[:10]:
        atraso_table.add_row(str(dezena), str(atraso))

    media_table = Table(title="Medias e Modas recentes", show_header=True, header_style="bold green")
    media_table.add_column("Metrica")
    media_table.add_column("Media", justify="right")
    media_table.add_column("Moda", justify="right")

    for key, media in analysis["medias"].items():
        moda = analysis["modas"].get(key)
        media_table.add_row(key, f"{media:.2f}", "-" if moda is None else str(moda))

    console.print(hot_table)
    console.print(cold_table)
    console.print(atraso_table)
    console.print(media_table)


def _analysis_flow() -> None:
    window_txt = questionary.text("Quantos ultimos concursos analisar?", default="120").ask()
    if not window_txt:
        return

    try:
        window = max(20, int(window_txt))
    except ValueError:
        console.print("[red]Valor invalido para janela.[/red]")
        return

    with connect_db(DB_PATH) as conn:
        all_draws = get_all_draws(conn)
        recent_stats = get_recent_stats(conn, window)

    if not all_draws:
        console.print("[yellow]Banco vazio. Faca a carga inicial primeiro.[/yellow]")
        return

    analysis = sliding_window_analysis(all_draws, recent_stats, window)
    _render_analysis_tables(analysis)

    sugestoes = analysis["sugestoes"]
    cfg_table = Table(title="Sugestoes de filtros", show_header=True, header_style="bold blue")
    cfg_table.add_column("Filtro")
    cfg_table.add_column("Sugestao")
    for key, value in sugestoes.items():
        cfg_table.add_row(key, str(value))
    console.print(cfg_table)

    if questionary.confirm("Deseja aplicar estas sugestoes em config_filtros.json?", default=True).ask():
        cfg = FilterConfig(**sugestoes)
        save_filter_config(CONFIG_PATH, cfg)
        console.print("[green]Configuracoes aplicadas com sucesso.[/green]")


def _generate_games_flow() -> None:
    cfg = load_filter_config(CONFIG_PATH)

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
        draws = get_recent_draws(conn, 1)

    if not draws:
        console.print("[yellow]Banco vazio. Faca a carga inicial primeiro.[/yellow]")
        return

    previous = draws[-1]["dezenas"]
    games = generate_filtered_games(cfg, previous, amount, max_attempts)

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


def _show_status() -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn)
        last = get_last_concurso(conn)

    status_table = Table(title="Status do aplicativo", show_header=False)
    status_table.add_row("Banco", str(DB_PATH))
    status_table.add_row("Config filtros", str(CONFIG_PATH))
    status_table.add_row("Total de sorteios", str(total))
    status_table.add_row("Ultimo concurso", "-" if last is None else str(last))
    console.print(status_table)


def main() -> None:
    _bootstrap_db()
    _show_header()

    options = [
        "1) Carga inicial pelo Excel (uma vez)",
        "2) Atualizar com novos sorteios da API",
        "3) Analise dinamica (janela deslizante)",
        "4) Gerar palpites com pipeline de filtros",
        "5) Ver status",
        "0) Sair",
    ]

    while True:
        choice = questionary.select("Escolha uma opcao:", choices=options).ask()
        if choice is None or choice.startswith("0"):
            console.print("[cyan]Encerrando aplicativo.[/cyan]")
            break

        if choice.startswith("1"):
            _load_initial_excel_flow()
            continue

        if choice.startswith("2"):
            _update_from_api_flow()
            continue

        if choice.startswith("3"):
            _analysis_flow()
            continue

        if choice.startswith("4"):
            _generate_games_flow()
            continue

        if choice.startswith("5"):
            _show_status()


if __name__ == "__main__":
    main()
