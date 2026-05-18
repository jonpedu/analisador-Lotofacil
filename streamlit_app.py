from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import pandas as pd
import streamlit as st

from analyzer import calculate_draw_stats, sliding_window_analysis
from api import fetch_draw_by_concurso
from config_manager import load_filter_config, save_filter_config
from db import (
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
from etl import read_initial_excel
from filters import FilterConfig, generate_filtered_games

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "lotofacil_analyzer_pro.db"
CONFIG_PATH = DATA_DIR / "config_filtros.json"
DEFAULT_EXCEL_PATH = APP_DIR / "Lotofácil.xlsx"
DEFAULT_API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"


st.set_page_config(
    page_title="Lotofácil Analyzer Pro",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="expanded"
)


def _bootstrap_db() -> None:
    with connect_db(DB_PATH) as conn:
        init_db(conn)


def _status_section() -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn)
        last = get_last_concurso(conn)

    st.markdown("### 📊 Status do Aplicativo")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Sorteios Registrados", value=total)
    with col2:
        st.metric(label="Último Concurso", value=last if last is not None else "-")
    with col3:
        st.metric(label="Banco de Dados", value="Ativo ✅" if total > 0 else "Vazio ⚠️")

    st.markdown("#### 📁 Caminhos do Sistema")
    st.info(f"**Banco SQL:** `{DB_PATH}`\n\n**Configuração:** `{CONFIG_PATH}`")


def _load_excel_section() -> None:
    st.markdown("### 📥 Carga Inicial pelo Excel")
    st.caption("Use esta opção apenas uma vez para popular o banco de dados com seu histórico inicial.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        use_default = st.checkbox("Usar 'Lotofácil.xlsx' da raiz do projeto", value=True)
    with col2:
        overwrite = st.checkbox("Sobrescrever dados existentes no banco", value=False)

    upload = st.file_uploader("Ou envie seu próprio arquivo Excel", type=["xlsx"])
    excel_path = DEFAULT_EXCEL_PATH

    if upload is not None:
        temp_path = DATA_DIR / "upload_excel.xlsx"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(upload.read())
        excel_path = temp_path
    elif not use_default:
        excel_path_input = st.text_input("Caminho do arquivo Excel", value=str(DEFAULT_EXCEL_PATH))
        excel_path = Path(excel_path_input)

    st.write("")
    if st.button("🚀 Executar Carga Inicial", type="primary"):
        with connect_db(DB_PATH) as conn:
            if not overwrite and count_draws(conn) > 0:
                st.warning("⚠️ O banco já possui dados. Marque 'Sobrescrever' para continuar.")
                return

        with st.spinner("Processando Excel e salvando no banco de dados..."):
            try:
                draws = read_initial_excel(Path(excel_path))
            except Exception as exc:
                st.error(f"❌ Erro ao ler Excel: {exc}")
                return

            if not draws:
                st.error("❌ Nenhum sorteio válido encontrado no Excel.")
                return

            with connect_db(DB_PATH) as conn:
                for draw in draws:
                    upsert_draw(conn, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
                    upsert_stats(conn, draw["concurso"], calculate_draw_stats(draw["dezenas"]))
                conn.commit()

        st.success(f"✅ Carga concluída com sucesso: **{len(draws)}** sorteios importados.")


def _update_api_section() -> None:
    st.markdown("### 🔄 Atualizar pela API")
    st.caption("Busca os sorteios mais recentes direto da API das Loterias.")
    st.markdown("---")
    
    api_url = st.text_input("URL base da API", value=DEFAULT_API_BASE_URL)

    if st.button("📡 Buscar Sorteios Novos", type="primary"):
        with st.spinner("Refrescando dados da API..."):
            with connect_db(DB_PATH) as conn:
                last = get_last_concurso(conn)
                if last is None:
                    st.warning("⚠️ Banco vazio. Execute a carga inicial antes de atualizar.")
                    return

                next_concurso = last + 1
                imported = 0

                while True:
                    try:
                        draw = fetch_draw_by_concurso(api_url, next_concurso)
                    except Exception as exc:
                        st.error(f"❌ Erro na API (concurso {next_concurso}): {exc}")
                        break

                    if draw is None:
                        break

                    upsert_draw(conn, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
                    upsert_stats(conn, draw["concurso"], calculate_draw_stats(draw["dezenas"]))
                    imported += 1
                    next_concurso += 1

                conn.commit()

        if imported == 0:
            st.info("👍 Sistema já está atualizado com os sorteios mais recentes!")
        else:
            st.success(f"🎉 Atualização concluída: **{imported}** novos concursos adicionados!")


def _analysis_section() -> None:
    st.markdown("### 📈 Análise Dinâmica (Janela Deslizante)")
    st.caption("Estatísticas móveis para identificar padrões do momento atual do jogo.")
    st.markdown("---")

    with connect_db(DB_PATH) as conn:
        total = count_draws(conn)

    col_w, _ = st.columns([1, 2])
    with col_w:
        max_janela = total if total > 0 else 1
        default_val = min(120, max_janela)
        window = st.number_input("Tamanho da Janela (Últimos Concursos)", min_value=1, max_value=max_janela, value=default_val, step=5)

    with connect_db(DB_PATH) as conn:
        all_draws = get_all_draws(conn)
        recent_stats = get_recent_stats(conn, int(window))

    if not all_draws:
        st.warning("⚠️ Banco vazio. É necessário ter dados para a análise.")
        return

    with st.spinner("Recalculando estatísticas..."):
        analysis = sliding_window_analysis(all_draws, recent_stats, int(window))

    st.markdown("#### 🔢 Frequência das Dezenas")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("🔥 **Mais Sorteados (Quentes)**")
        df_mais = pd.DataFrame(analysis["mais_sorteadas"], columns=["Dezena", "Frequência"])
        st.bar_chart(df_mais.set_index("Dezena"))
        st.dataframe(df_mais, use_container_width=True)

    with col2:
        st.write("❄️ **Menos Sorteados (Frios)**")
        df_menos = pd.DataFrame(analysis["menos_sorteadas"], columns=["Dezena", "Frequência"])
        st.dataframe(df_menos, use_container_width=True)

    st.markdown("#### ⏳ Top Atrasos Atuais")
    atrasos_itens = sorted(analysis["atrasos"].items(), key=lambda x: x[1], reverse=True)[:10]
    df_atrasos = pd.DataFrame(atrasos_itens, columns=["Dezena", "Sorteios em Atraso"])
    st.dataframe(df_atrasos, use_container_width=True)

    st.markdown("#### 📌 Médias e Modas Globais")
    st.caption("ℹ️ **Entendendo a tabela:** A **Média (Matemática)** é o valor médio fracionado exato na janela. A **Moda (Mais Comum)** é o número inteiro que mais se repetiu na prática.")
    medias = analysis["medias"]
    modas = analysis["modas"]
    
    media_data = []
    for k, v in medias.items():
        media_data.append({"Métrica": k.replace("_", " ").title(), "Média (Matemática)": round(v, 2), "Moda (Mais Comum)": modas.get(k, "-")})
    st.table(pd.DataFrame(media_data))

    st.markdown("#### 🤖 Sugestões Inteligentes de Filtros")
    st.info("Essas configurações são otimizadas para as métricas da janela acima.")
    st.json(analysis["sugestoes"])

    if st.button("👉 Aplicar Sugestões ao Gerador", type="primary"):
        cfg = FilterConfig(**analysis["sugestoes"])
        save_filter_config(CONFIG_PATH, cfg)
        st.success("✅ Configurações auto-ajustadas e salvas com sucesso!")


def _filters_editor(cfg: FilterConfig) -> FilterConfig:
    with st.expander("🛠️ Personalizar Filtros Manualmente", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            cfg.sum_min = st.number_input("Soma Mínima", value=cfg.sum_min, step=1)
            cfg.sum_max = st.number_input("Soma Máxima", value=cfg.sum_max, step=1)
            cfg.max_consecutive = st.number_input("Max Consecutivas", value=cfg.max_consecutive, step=1)
        with col2:
            cfg.repeat_min = st.number_input("Repetidas (Ant) Mín", value=cfg.repeat_min, step=1)
            cfg.repeat_max = st.number_input("Repetidas (Ant) Máx", value=cfg.repeat_max, step=1)
            
            allowed_pairs = st.text_input(
                "Pares/Ímpares (ex: 8,7;7,8)",
                value=";".join(f"{p[0]},{p[1]}" for p in cfg.allowed_even_odd_pairs),
            )
            cfg.allowed_even_odd_pairs = [
                [int(pair.split(",")[0]), int(pair.split(",")[1])]
                for pair in allowed_pairs.split(";")
                if "," in pair
            ]
        with col3:
            cfg.prime_min = st.number_input("Primos Mín", value=cfg.prime_min, step=1)
            cfg.prime_max = st.number_input("Primos Máx", value=cfg.prime_max, step=1)
            cfg.fibonacci_min = st.number_input("Fibonacci Mín", value=cfg.fibonacci_min, step=1)
            cfg.fibonacci_max = st.number_input("Fibonacci Máx", value=cfg.fibonacci_max, step=1)
        with col4:
            cfg.multiple3_min = st.number_input("Múltiplos de 3 Mín", value=cfg.multiple3_min, step=1)
            cfg.multiple3_max = st.number_input("Múltiplos de 3 Máx", value=cfg.multiple3_max, step=1)
            cfg.moldura_min = st.number_input("Moldura Mín", value=cfg.moldura_min, step=1)
            cfg.moldura_max = st.number_input("Moldura Máx", value=cfg.moldura_max, step=1)

        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            cfg.row_min = st.number_input("Por Linha Mín", value=cfg.row_min, step=1)
        with col_r2:    
            cfg.row_max = st.number_input("Por Linha Máx", value=cfg.row_max, step=1)
        with col_r3:
            cfg.col_min = st.number_input("Por Coluna Mín", value=cfg.col_min, step=1)
        with col_r4:
            cfg.col_max = st.number_input("Por Coluna Máx", value=cfg.col_max, step=1)

        st.write("")
        if st.button("💾 Salvar Customizações"):
            save_filter_config(CONFIG_PATH, cfg)
            st.success("✅ Novos filtros salvos.")

    return cfg


def _generate_section() -> None:
    st.markdown("### 🎲 Gerador de Palpites de Alta Performance")
    st.caption("Cria jogos aleatórios que passam pelo rigoroso pipeline de filtros matemáticos.")
    st.markdown("---")

    cfg = load_filter_config(CONFIG_PATH)
    cfg = _filters_editor(cfg)

    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Quantidade de Volantes", min_value=1, max_value=200, value=5, step=1)
    with col2:
        max_attempts = st.number_input("Total de Tentativas Máximas", min_value=1000, max_value=2000000, value=300000, step=50000)

    st.write("")
    if st.button("✨ Iniciar Geração Inteligente", type="primary", use_container_width=True):
        with connect_db(DB_PATH) as conn:
            draws = get_recent_draws(conn, 1)

        if not draws:
            st.warning("⚠️ Banco vazio. Faça a carga inicial primeiro.")
            return

        previous = draws[-1]["dezenas"]

        with st.spinner("Gerando e filtrando milhares de combinações..."):
            games = generate_filtered_games(cfg, previous, int(amount), int(max_attempts))

        st.markdown(f"**Resultado:** Encontramos **{len(games)}** jogo(s) que sobreviveu(eram) aos filtros!")

        if not games:
            st.error("😭 Nenhum jogo aprovado. Aumente o número de tentativas ou relaxe os filtros.")
            return

        jogos_formatados = []
        for i, game in enumerate(games, 1):
            s_jogo = " ➖ ".join(f"{n:02d}" for n in game)
            jogos_formatados.append({"Palpite": f"Bilhete {i}", "Dezenas": s_jogo})

        st.dataframe(pd.DataFrame(jogos_formatados), use_container_width=True)
        st.success("🍀 Boa sorte!")


def main() -> None:
    _bootstrap_db()

    with st.sidebar:
        st.title("🍀 Analyzer Pro")
        st.caption("Motor Local de Análise Caixa")
        st.markdown("---")
        menu = st.radio(
            "📍 Navegação",
            [
                "📊 Status",
                "📥 Carga Inicial",
                "🔄 Atualizar p/ API",
                "📈 Análise Inteligente",
                "🎲 Gerador Filtros",
            ],
        )

    if menu == "📊 Status":
        _status_section()
    elif menu == "📥 Carga Inicial":
        _load_excel_section()
    elif menu == "🔄 Atualizar p/ API":
        _update_api_section()
    elif menu == "📈 Análise Inteligente":
        _analysis_section()
    elif menu == "🎲 Gerador Filtros":
        _generate_section()


if __name__ == "__main__":
    main()

