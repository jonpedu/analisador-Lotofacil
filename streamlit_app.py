from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import pandas as pd
import streamlit as st

# Imports Globais
from src.api import fetch_draw_by_concurso
from src.config_manager import load_filter_config, save_filter_config
from src.db import (
    connect_db,
    count_draws,
    get_all_draws,
    get_draw_by_concurso,
    get_last_concurso,
    get_recent_draws,
    get_recent_stats,
    init_db,
    upsert_draw,
    upsert_stats,
)
from src.etl import read_initial_excel

# Imports de Loterias Modulares
import src.lotofacil.analyzer as lf_analyzer
import src.lotofacil.backtest as lf_backtest
import src.lotofacil.filters as lf_filters
import src.lotofacil.scoring as lf_scoring
import src.megasena.analyzer as ms_analyzer
import src.megasena.filters as ms_filters

# Caminhos globais
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "lotofacil_analyzer_pro.db"

# Arquivos de configurações separados
CONFIG_LOTOFACIL = DATA_DIR / "config_filtros_lotofacil.json"
CONFIG_MEGASENA = DATA_DIR / "config_filtros_megasena.json"

# API endpoints
API_LOTOFACIL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_MEGASENA = "https://loteriascaixa-api.herokuapp.com/api/megasena"

# Page config com ícone dinâmico
st.set_page_config(
    page_title="Loterias Pro-Analyzer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Customizada Premium (Dark Mode & Elegância)
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Glassmorphism Cards */
.card-lf {
    background: rgba(138, 43, 226, 0.05);
    border: 1px solid rgba(138, 43, 226, 0.2);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.card-ms {
    background: rgba(32, 201, 151, 0.05);
    border: 1px solid rgba(32, 201, 151, 0.2);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

/* Badges de Categoria de dezenas */
.badge-quente {
    background-color: rgba(220, 53, 69, 0.2);
    color: #ff6b6b;
    padding: 4px 10px;
    border-radius: 8px;
    font-weight: bold;
    border: 1px solid rgba(220, 53, 69, 0.4);
}

.badge-fria {
    background-color: rgba(13, 110, 253, 0.2);
    color: #4dadff;
    padding: 4px 10px;
    border-radius: 8px;
    font-weight: bold;
    border: 1px solid rgba(13, 110, 253, 0.4);
}

.badge-intermediaria {
    background-color: rgba(255, 193, 7, 0.2);
    color: #ffd166;
    padding: 4px 10px;
    border-radius: 8px;
    font-weight: bold;
    border: 1px solid rgba(255, 193, 7, 0.4);
}

.header-pro {
    font-size: 2.2rem;
    font-weight: 700;
    text-align: center;
    background: linear-gradient(45deg, #8A2BE2, #20C997);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 25px;
}

/* --- ESTILOS DE ENGENHARIA VISUAL PRO (UPGRADE) --- */

/* Tabelas e Grids de Movimentação Cronológica */
.table-container {
    overflow-x: auto;
    margin-bottom: 20px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.01);
    padding: 15px;
}

.behavior-table {
    width: 100%;
    border-collapse: collapse;
    text-align: center;
    font-family: 'Outfit', sans-serif;
}

.behavior-table th {
    background: rgba(138, 43, 226, 0.18) !important;
    color: #FFFFFF !important;
    font-weight: 600;
    padding: 10px 4px;
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 13px;
    min-width: 32px;
}

.behavior-table-ms th {
    background: rgba(32, 201, 151, 0.18) !important;
    color: #FFFFFF !important;
    font-weight: 600;
    padding: 8px 2px;
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 11px;
    min-width: 19px;
}

.behavior-table td {
    padding: 6px 4px;
    border: 1px solid rgba(255,255,255,0.05);
    font-size: 13px;
}

.behavior-table-ms td {
    padding: 5px 2px;
    border: 1px solid rgba(255,255,255,0.05);
    font-size: 11px;
}

.th-concurso, .td-concurso {
    font-weight: bold;
    min-width: 90px !important;
    background: rgba(255,255,255,0.04) !important;
    color: #FFFFFF !important;
    border-right: 2px solid rgba(255,255,255,0.1) !important;
}

.circle-drawn-lf {
    width: 25px;
    height: 25px;
    line-height: 25px;
    border-radius: 50%;
    background: linear-gradient(135deg, #8A2BE2, #6a1b9a);
    color: #ffffff !important;
    font-weight: bold;
    font-size: 12px;
    margin: 0 auto;
    box-shadow: 0 0 8px rgba(138, 43, 226, 0.7);
    border: 1px solid rgba(255,255,255,0.2);
}

.circle-drawn-ms {
    width: 19px;
    height: 19px;
    line-height: 19px;
    border-radius: 50%;
    background: linear-gradient(135deg, #20C997, #128c7e);
    color: #ffffff !important;
    font-weight: bold;
    font-size: 10px;
    margin: 0 auto;
    box-shadow: 0 0 8px rgba(32, 201, 151, 0.7);
    border: 1px solid rgba(255,255,255,0.2);
}

.dot-absent {
    color: rgba(255,255,255,0.12);
    font-size: 15px;
    font-weight: bold;
    line-height: 25px;
}

/* Volante do Ciclo (Lotofácil) */
.volante-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin: 20px 0;
}

.volante-card-drawn {
    background: rgba(40, 167, 69, 0.08) !important;
    border: 1px solid rgba(40, 167, 69, 0.3) !important;
    border-radius: 8px;
    padding: 18px 10px;
    text-align: center;
    color: #51cf66 !important;
    font-weight: 600;
    font-size: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.volante-card-absent {
    background: rgba(255, 193, 7, 0.1) !important;
    border: 2px solid #ffd166 !important;
    border-radius: 8px;
    padding: 18px 10px;
    text-align: center;
    color: #ffe066 !important;
    font-weight: 700;
    font-size: 20px;
    box-shadow: 0 0 10px rgba(255, 193, 7, 0.3);
    animation: pulse-border 1.6s infinite;
}

@keyframes pulse-border {
    0% { box-shadow: 0 0 4px rgba(255, 193, 7, 0.2); border-color: rgba(255, 193, 7, 0.4); }
    50% { box-shadow: 0 0 12px rgba(255, 193, 7, 0.6); border-color: #ffd166; }
    100% { box-shadow: 0 0 4px rgba(255, 193, 7, 0.2); border-color: rgba(255, 193, 7, 0.4); }
}

/* Volante de Quadrantes (Mega-Sena) */
.volante-mega-grid {
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 8px;
    margin: 20px 0;
}

.mega-card-cell {
    border-radius: 6px;
    padding: 12px 6px;
    text-align: center;
    font-weight: 500;
    font-size: 16px;
    color: rgba(255,255,255,0.4);
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.mega-card-q1 { background: rgba(138, 43, 226, 0.04); border: 1px solid rgba(138, 43, 226, 0.15); }
.mega-card-q2 { background: rgba(32, 201, 151, 0.04); border: 1px solid rgba(32, 201, 151, 0.15); }
.mega-card-q3 { background: rgba(0, 123, 255, 0.04); border: 1px solid rgba(0, 123, 255, 0.15); }
.mega-card-q4 { background: rgba(255, 193, 7, 0.04); border: 1px solid rgba(255, 193, 7, 0.15); }

.mega-card-drawn {
    background: linear-gradient(135deg, #20C997, #128c7e) !important;
    color: #ffffff !important;
    border: 2px solid #FFD700 !important;
    box-shadow: 0 0 10px rgba(32, 201, 151, 0.8), 0 0 15px #FFD700 !important;
    font-weight: 700 !important;
    transform: scale(1.05);
    animation: pulse-gold 1.8s infinite;
}

@keyframes pulse-gold {
    0% { box-shadow: 0 0 8px rgba(32, 201, 151, 0.6), 0 0 4px #FFD700; }
    50% { box-shadow: 0 0 14px rgba(32, 201, 151, 0.9), 0 0 12px #FFD700; }
    100% { box-shadow: 0 0 8px rgba(32, 201, 151, 0.6), 0 0 4px #FFD700; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _bootstrap_db() -> None:
    with connect_db(DB_PATH) as conn:
        init_db(conn)


def _status_section(lottery_type: str) -> None:
    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, lottery_type)
        last = get_last_concurso(conn, lottery_type)

    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    
    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>📊 Status - {lottery_name}</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Sorteios Registrados", value=total)
    with col2:
        st.metric(label="Último Concurso", value=last if last is not None else "-")
    with col3:
        st.metric(label="Status do Banco", value="Ativo ✅" if total > 0 else "Vazio ⚠️")

    # Beautiful System Paths Info
    st.markdown("#### 📁 Caminhos Locais")
    config_file = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA
    card_class = "card-lf" if lottery_type == "lotofacil" else "card-ms"
    
    st.markdown(
        f"<div class='{card_class}'>"
        f"<b>Banco de Dados SQL:</b> <code>{DB_PATH}</code><br><br>"
        f"<b>Configuração de Filtros:</b> <code>{config_file}</code>"
        f"</div>",
        unsafe_allow_html=True
    )


def _load_excel_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    excel_filename = "Lotofácil.xlsx" if lottery_type == "lotofacil" else "Mega-Sena.xlsx"
    default_excel_path = APP_DIR / excel_filename

    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>📥 Carga Inicial ({lottery_name})</h2>", unsafe_allow_html=True)
    st.caption("Popule a base local com os dados extraídos das planilhas oficiais.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        use_default = st.checkbox(f"Usar '{excel_filename}' da raiz do projeto", value=True)
    with col2:
        overwrite = st.checkbox("Sobrescrever dados existentes no banco", value=False)

    upload = st.file_uploader("Ou envie seu próprio arquivo Excel", type=["xlsx"])
    excel_path = default_excel_path

    if upload is not None:
        temp_path = DATA_DIR / f"upload_{lottery_type}.xlsx"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(upload.read())
        excel_path = temp_path
    elif not use_default:
        excel_path_input = st.text_input("Caminho do arquivo Excel customizado", value=str(default_excel_path))
        excel_path = Path(excel_path_input)

    st.write("")
    if st.button("🚀 Executar Carga", type="primary", use_container_width=True):
        with connect_db(DB_PATH) as conn:
            if not overwrite and count_draws(conn, lottery_type) > 0:
                st.warning("⚠️ O banco já possui dados. Marque 'Sobrescrever' para continuar.")
                return

        with st.spinner("Processando dados e gerando estatísticas no banco..."):
            try:
                draws = read_initial_excel(Path(excel_path), lottery_type)
            except Exception as exc:
                st.error(f"❌ Erro ao ler Excel: {exc}")
                return

            if not draws:
                st.error("❌ Nenhum sorteio válido encontrado no Excel. Verifique a estrutura das colunas.")
                return

            with connect_db(DB_PATH) as conn:
                for draw in draws:
                    upsert_draw(conn, lottery_type, draw["concurso"], draw["data_sorteio"], draw["dezenas"])
                    if lottery_type == "megasena":
                        stats = ms_analyzer.calculate_draw_stats(draw["dezenas"])
                    else:
                        stats = lf_analyzer.calculate_draw_stats(draw["dezenas"])
                    upsert_stats(conn, lottery_type, draw["concurso"], stats)
                conn.commit()

        st.success(f"✅ Sucesso: **{len(draws)}** sorteios de {lottery_name} importados com sucesso!")


def _update_api_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    api_url = API_LOTOFACIL if lottery_type == "lotofacil" else API_MEGASENA

    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>🔄 Atualizar via API - {lottery_name}</h2>", unsafe_allow_html=True)
    st.caption("Faz a varredura e download automático dos concursos mais recentes diretamente dos servidores da Caixa.")
    st.markdown("---")
    
    custom_url = st.text_input("URL base da API de Loterias", value=api_url)

    if st.button("📡 Buscar Concursos Novos", type="primary", use_container_width=True):
        with st.spinner("Conectando à API e sincronizando novos sorteios..."):
            with connect_db(DB_PATH) as conn:
                last = get_last_concurso(conn, lottery_type)
                if last is None:
                    st.warning("⚠️ Banco de dados local vazio. Por favor, faça a carga pelo Excel primeiro.")
                    return

                next_concurso = last + 1
                imported = 0

                while True:
                    try:
                        draw = fetch_draw_by_concurso(custom_url, next_concurso, lottery_type)
                    except Exception as exc:
                        st.error(f"❌ Falha de rede ou API no concurso {next_concurso}: {exc}")
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
            st.info("👍 Excelente! Seu banco de dados local já está 100% atualizado com o último concurso da Caixa!")
        else:
            st.success(f"🎉 Integração Concluída: **{imported}** novos concursos adicionados com sucesso!")


def _analysis_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    card_class = "card-lf" if lottery_type == "lotofacil" else "card-ms"

    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>📈 Análise Estatística Avançada - {lottery_name}</h2>", unsafe_allow_html=True)
    st.markdown("---")

    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, lottery_type)

    if total == 0:
        st.warning("⚠️ Banco de dados local vazio. Por favor, execute a carga inicial antes de realizar análises.")
        return

    col_w, _ = st.columns([1, 2])
    with col_w:
        max_janela = total
        default_val = min(120, max_janela)
        window = st.number_input("Tamanho da Janela de Análise (Últimos Concursos)", min_value=10, max_value=max_janela, value=default_val, step=10)

    with connect_db(DB_PATH) as conn:
        all_draws = get_all_draws(conn, lottery_type)
        recent_stats = get_recent_stats(conn, lottery_type, int(window))

    with st.spinner("Processando dados e rodando análise de tendências..."):
        if lottery_type == "megasena":
            analysis = ms_analyzer.sliding_window_analysis(all_draws, recent_stats, int(window))
        else:
            analysis = lf_analyzer.sliding_window_analysis(all_draws, recent_stats, int(window))

    # Criação das Abas Pro-Visualization
    tab_rank, tab_behavior, tab_volante = st.tabs([
        "📊 Classificação & Tendências",
        "📅 Mapa de Movimentação Cronológica",
        "🌀 Volante e Ciclo Ativo" if lottery_type == "lotofacil" else "🧩 Volante e Quadrantes"
    ])

    # --- ABA 1: CLASSIFICAÇÃO COMPLETA & ESTATÍSTICAS ---
    with tab_rank:
        st.markdown("### 📊 Frequência Completa de Dezenas (Ordem Decrescente)")
        st.caption("Esta tabela exibe todos os números ordenados pela frequência com que aparecem na janela de análise escolhida.")

        df_freq_completa = pd.DataFrame(analysis["frequencia_completa"])
        
        def highlight_category(val):
            if "Quente" in str(val):
                return "color: #ff6b6b; font-weight: bold;"
            elif "Fria" in str(val):
                return "color: #4dadff; font-weight: bold;"
            return "color: #ffd166;"

        styled_df = df_freq_completa.style.map(highlight_category, subset=["Categoria"])
        st.dataframe(styled_df, use_container_width=True, height=350)

        # Médias Globais
        st.markdown("### 📌 Médias e Modas Recentes na Janela")
        medias_data = []
        medias = analysis["medias"]
        modas = analysis["modas"]
        for k, v in medias.items():
            if "count" in k or k in ["soma", "qtd_pares", "qtd_impares", "qtd_primos", "qtd_fibonacci", "qtd_multiplos_3", "qtd_moldura"]:
                metric_name = k.replace("_", " ").replace("qtd", "Quantidade").title()
                medias_data.append({
                    "Métrica Estatística": metric_name,
                    "Média (Matemática)": round(v, 2),
                    "Moda (Mais Comum)": modas.get(k, "-")
                })
        st.table(pd.DataFrame(medias_data))

        # Sugestões Otimizadas
        st.markdown("### 🤖 Configurações de Filtros Recomendadas")
        st.write("Calibração sugerida de filtros com base no comportamento recente na janela:")
        st.json(analysis["sugestoes"])

        if st.button("👉 Aplicar Sugestões ao Gerador de Filtros", type="primary", use_container_width=True):
            config_path = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA
            if lottery_type == "megasena":
                cfg = ms_filters.FilterConfig(**analysis["sugestoes"])
            else:
                cfg = lf_filters.FilterConfig(**analysis["sugestoes"])
            save_filter_config(config_path, cfg)
            st.success("✅ Configurações de filtros salvas com sucesso!")

    # --- ABA 2: MAPA DE MOVIMENTAÇÃO CRONOLÓGICA (TENDÊNCIAS CONCURSO A CONCURSO) ---
    with tab_behavior:
        st.markdown("### 📅 Mapa de Comportamento e Movimentação das Dezenas")
        st.caption("Visão cronológica concurso a concurso (mais recente no topo) permitindo identificar padrões cíclicos, ondas de calor e dezenas em atraso.")
        
        limit_mov = st.slider(
            "Visualizar últimos sorteios:",
            min_value=5,
            max_value=30,
            value=15,
            step=1,
            key=f"slider_mov_{lottery_type}"
        )

        recent_draws_mov = all_draws[-limit_mov:]
        recent_draws_mov.reverse()

        max_num = 60 if lottery_type == "megasena" else 25
        table_class = "behavior-table behavior-table-ms" if lottery_type == "megasena" else "behavior-table"
        circle_class = "circle-drawn-ms" if lottery_type == "megasena" else "circle-drawn-lf"

        # Constrói Tabela de Comportamento Dinâmica
        html_table = f'<div class="table-container"><table class="{table_class}">'
        html_table += '<thead><tr><th class="th-concurso">Concurso</th>'
        for n in range(1, max_num + 1):
            html_table += f'<th>{n:02d}</th>'
        html_table += '</tr></thead><tbody>'

        for draw in recent_draws_mov:
            concurso = draw["concurso"]
            drawn_set = set(draw["dezenas"])
            html_table += f'<tr><td class="td-concurso">{concurso}</td>'
            for n in range(1, max_num + 1):
                if n in drawn_set:
                    html_table += f'<td><div class="{circle_class}">{n:02d}</div></td>'
                else:
                    html_table += '<td><div class="dot-absent">•</div></td>'
            html_table += '</tr>'
        html_table += '</tbody></table></div>'

        st.markdown(html_table, unsafe_allow_html=True)

    # --- ABA 3: VOLANTE E PAINÉIS DE TENDÊNCIA ESTATÍSTICA (CICLOS / QUADRANTES) ---
    with tab_volante:
        if lottery_type == "lotofacil":
            st.markdown("### 🌀 Volante de Acompanhamento do Ciclo (Lotofácil)")
            st.caption("Visão do volante físico 5x5 do ciclo atual. Números que já foram sorteados estão com checkmark e dezenas em atraso (pendentes) piscam em destaque como alvos recomendados.")
            
            ciclo = analysis["ciclo"]
            
            # Métricas rápidas no topo
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.metric(label="Ciclo Atual N°", value=ciclo["ciclo_atual_numero"])
            with col_c2:
                st.metric(label="Concursos Acumulados no Ciclo", value=ciclo["concursos_no_ciclo_atual"])
            with col_c3:
                st.metric(label="Dezenas Faltando para Fechar", value=len(ciclo["dezenas_ausentes_atual"]))

            # Volante do Ciclo
            drawn_in_cycle = set(ciclo["dezenas_sorteadas_atual"])
            
            grid_html = '<div class="volante-grid">'
            for n in range(1, 26):
                if n in drawn_in_cycle:
                    grid_html += f'<div class="volante-card-drawn">{n:02d}<br><span style="font-size:10px; opacity:0.8;">✓</span></div>'
                else:
                    grid_html += f'<div class="volante-card-absent">{n:02d}<br><span style="font-size:10px;">🎯 Ausente</span></div>'
            grid_html += '</div>'
            
            st.markdown(grid_html, unsafe_allow_html=True)

            # Histórico de ciclos recentes
            with st.expander("📜 Histórico de Duração de Ciclos Anteriores"):
                if ciclo["historico_ciclos"]:
                    df_c = pd.DataFrame(ciclo["historico_ciclos"])
                    df_c.columns = ["Número do Ciclo", "Duração (Concursos)", "Concurso de Fechamento"]
                    st.table(df_c.tail(10))
                else:
                    st.write("Nenhum histórico disponível.")

        elif lottery_type == "megasena":
            st.markdown("### 🧩 Volante de Quadrantes da Cartela (Mega-Sena)")
            st.caption("As 60 dezenas divididas por cores representando seus Quadrantes Físicos. As dezenas sorteadas no último sorteio registrado ganham foco dourado neon pulsante.")

            latest_draw = all_draws[-1]["dezenas"] if all_draws else []
            drawn_set = set(latest_draw)

            # Métricas rápidas de Quadrantes do último concurso
            medias = analysis["medias"]
            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            with col_q1:
                st.metric(label="Frequência Média Q1", value=f"{medias.get('q1_count', 0):.2f}")
            with col_q2:
                st.metric(label="Frequência Média Q2", value=f"{medias.get('q2_count', 0):.2f}")
            with col_q3:
                st.metric(label="Frequência Média Q3", value=f"{medias.get('q3_count', 0):.2f}")
            with col_q4:
                st.metric(label="Frequência Média Q4", value=f"{medias.get('q4_count', 0):.2f}")

            # Volante Mega-Sena
            grid_html = '<div class="volante-mega-grid">'
            for n in range(1, 61):
                q = ms_analyzer.get_quadrant(n)
                q_class = f"mega-card-q{q}"
                if n in drawn_set:
                    grid_html += f'<div class="mega-card-cell mega-card-drawn">{n:02d}<br><span style="font-size:9px;">Último</span></div>'
                else:
                    grid_html += f'<div class="mega-card-cell {q_class}">{n:02d}<br><span style="font-size:9px; opacity:0.6;">Q{q}</span></div>'
            grid_html += '</div>'

            st.markdown(grid_html, unsafe_allow_html=True)


def _filters_editor(cfg: Any, lottery_type: str) -> Any:
    title_text = "🛠️ Personalizar Filtros Manualmente"
    config_path = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA

    with st.expander(title_text, expanded=False):
        if lottery_type == "lotofacil":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cfg.sum_min = st.number_input("Soma Mínima", value=cfg.sum_min, step=1)
                cfg.sum_max = st.number_input("Soma Máxima", value=cfg.sum_max, step=1)
                cfg.max_consecutive = st.number_input("Max Consecutivas", value=cfg.max_consecutive, step=1)
            with col2:
                cfg.repeat_min = st.number_input("Repetidas (Anterior) Mín", value=cfg.repeat_min, step=1)
                cfg.repeat_max = st.number_input("Repetidas (Anterior) Máx", value=cfg.repeat_max, step=1)
                
                allowed_pairs = st.text_input(
                    "Pares/Ímpares permitidos (ex: 8,7;7,8)",
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

        elif lottery_type == "megasena":
            col1, col2, col3 = st.columns(3)
            with col1:
                cfg.even_min = st.number_input("Pares Mínimo", value=cfg.even_min, step=1, min_value=0, max_value=6)
                cfg.even_max = st.number_input("Pares Máximo", value=cfg.even_max, step=1, min_value=0, max_value=6)
                cfg.sum_min = st.number_input("Soma Mínima", value=cfg.sum_min, step=5)
                cfg.sum_max = st.number_input("Soma Máxima", value=cfg.sum_max, step=5)
            with col2:
                cfg.prime_min = st.number_input("Primos Mínimo", value=cfg.prime_min, step=1, min_value=0, max_value=6)
                cfg.prime_max = st.number_input("Primos Máximo", value=cfg.prime_max, step=1, min_value=0, max_value=6)
                cfg.fibonacci_min = st.number_input("Fibonacci Mínimo", value=cfg.fibonacci_min, step=1, min_value=0, max_value=6)
                cfg.fibonacci_max = st.number_input("Fibonacci Máximo", value=cfg.fibonacci_max, step=1, min_value=0, max_value=6)
            with col3:
                cfg.q_min = st.number_input("Dezenas por Quadrante Mínimo", value=cfg.q_min, step=1, min_value=0, max_value=6)
                cfg.q_max = st.number_input("Dezenas por Quadrante Máximo", value=cfg.q_max, step=1, min_value=0, max_value=6)

        st.write("")
        if st.button("💾 Salvar Customizações de Filtros"):
            save_filter_config(config_path, cfg)
            st.success("✅ Novos limites de filtros salvos com sucesso!")

    return cfg


def _render_score_rank_result(resultado: dict) -> None:
    jogos = resultado["jogos"]
    st.markdown(
        f"**Resultado da Geração:** pool de **{resultado['pool_gerado']}** candidatos únicos analisados "
        f"({resultado['tentativas']} tentativas, {resultado['descartados_filtro']} reprovados nos filtros). "
        f"Os **{len(jogos)}** melhores foram selecionados com diversificação de carteira."
    )

    if not jogos:
        st.error("😭 Nenhum candidato válido gerado. Relaxe os filtros, desative o modo estrito ou aumente o pool.")
        return

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Score do Melhor Bilhete", f"{jogos[0]['score']['total']:.1f} / 100")
    with col_m2:
        sobre = resultado["sobreposicao_media"]
        st.metric(
            "Sobreposição Média da Carteira",
            "-" if sobre is None else f"{sobre} dezenas",
            help="Média de dezenas em comum entre os pares de bilhetes. Menor = maior cobertura."
        )

    tabela = []
    for i, jogo in enumerate(jogos, 1):
        s = jogo["score"]
        tabela.append({
            "Bilhete": f"#{i}",
            "Dezenas": "  ➖  ".join(f"{n:02d}" for n in jogo["dezenas"]),
            "Score": s["total"],
            "Aderência": s["aderencia"],
            "Equilíbrio Freq.": s["equilibrio_freq"],
            "Repetição": s["repeticao"],
            "Anti-Pop": s["anti_popularidade"],
        })
    st.dataframe(pd.DataFrame(tabela), use_container_width=True, hide_index=True)
    st.caption(
        "ℹ️ O score mede aderência ao perfil histórico e qualidade de rateio — "
        "nenhum score altera a probabilidade matemática de acerto (valide na aba 🔬 Backtest)."
    )
    st.success("🍀 Boa sorte! Registre os bilhetes em uma casa lotérica ou no app oficial da Caixa.")


def _backtest_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2"
    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>🔬 Backtest de Estratégias (Lotofácil)</h2>", unsafe_allow_html=True)
    st.caption(
        "Simulação honesta: para cada concurso do período testado, a estratégia escolhe 15 dezenas "
        "vendo apenas os concursos anteriores, e o acerto é conferido contra o resultado real."
    )
    st.markdown("---")

    if lottery_type != "lotofacil":
        st.info("ℹ️ O backtest está disponível apenas para a Lotofácil por enquanto. Selecione a Lotofácil na barra lateral.")
        return

    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, "lotofacil")

    if total < 200:
        st.warning("⚠️ Histórico insuficiente. Importe os sorteios (mínimo ~200 concursos) antes de rodar o backtest.")
        return

    teoria = lf_backtest.theoretical_summary()
    st.markdown(
        f"<div class='card-lf'><b>📐 Referência matemática (qualquer bilhete):</b> "
        f"média de <b>{teoria['media']:.0f} pontos</b> | 11+ pontos em <b>{teoria['pct_11']}%</b> dos concursos | "
        f"13+ em <b>{teoria['pct_13']}%</b> | 14+ em <b>{teoria['pct_14']}%</b>. "
        f"Uma estratégia só é melhor que o acaso se superar esses números de forma consistente.</div>",
        unsafe_allow_html=True,
    )

    todas = list(lf_backtest.STRATEGIES.keys())
    escolhidas = st.multiselect(
        "Estratégias para comparar",
        todas,
        default=["Aleatório puro (baseline)", "15 mais atrasadas", "Repete 9 do anterior", "Score & Rank (gerador do app)"],
    )

    col1, col2 = st.columns(2)
    with col1:
        n_testes = st.number_input(
            "Concursos a testar (mais recentes)",
            min_value=50, max_value=max(50, total - 101), value=min(300, total - 101), step=50,
        )
    with col2:
        seed = st.number_input("Semente aleatória (reprodutibilidade)", min_value=1, max_value=99999, value=42)

    lentas = [e for e in escolhidas if e in lf_backtest.ESTRATEGIAS_LENTAS]
    if lentas and n_testes > 500:
        st.warning(f"⏳ A estratégia '{lentas[0]}' é pesada: com {int(n_testes)} concursos o teste pode demorar alguns minutos.")

    if st.button("🚀 Rodar Backtest", type="primary", use_container_width=True):
        if not escolhidas:
            st.warning("Selecione ao menos uma estratégia.")
            return

        with connect_db(DB_PATH) as conn:
            all_draws = get_all_draws(conn, "lotofacil")

        barra = st.progress(0.0, text="Simulando concursos...")
        resultados = lf_backtest.run_backtest(
            all_draws,
            escolhidas,
            test_last_n=int(n_testes),
            warmup=100,
            seed=int(seed),
            progress_callback=lambda p: barra.progress(min(p, 1.0), text=f"Simulando concursos... {p*100:.0f}%"),
        )
        barra.empty()

        linhas = [{
            "Estratégia": r.estrategia,
            "Concursos": r.concursos_testados,
            "Média de Pontos": r.media,
            "≥11 pts (%)": r.pct_11,
            "≥12 pts (%)": r.pct_12,
            "≥13 pts (%)": r.pct_13,
            "Melhor Resultado": r.melhor,
        } for r in resultados]
        linhas.append({
            "Estratégia": "📐 Teoria (acaso puro)",
            "Concursos": "-",
            "Média de Pontos": teoria["media"],
            "≥11 pts (%)": teoria["pct_11"],
            "≥12 pts (%)": teoria["pct_12"],
            "≥13 pts (%)": teoria["pct_13"],
            "Melhor Resultado": "-",
        })
        st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

        # Distribuição de pontos por estratégia
        st.markdown("### 📊 Distribuição de Pontos")
        dist_data = {}
        for r in resultados:
            dist_data[r.estrategia] = {
                k: 100 * v / r.concursos_testados for k, v in r.distribuicao.items()
            }
        df_dist = pd.DataFrame(dist_data).fillna(0.0).sort_index()
        df_dist.index.name = "Pontos"
        st.bar_chart(df_dist)
        st.caption(
            "ℹ️ Diferenças de poucos centésimos na média são ruído estatístico, não vantagem. "
            "Se uma estratégia superar a teoria de forma consistente em amostras grandes, ela merece atenção."
        )


def _generate_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"
    config_path = CONFIG_LOTOFACIL if lottery_type == "lotofacil" else CONFIG_MEGASENA

    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>🎲 Gerador Inteligente de Palpites ({lottery_name})</h2>", unsafe_allow_html=True)
    st.caption("Gera volantes com filtros matemáticos dinâmicos para maximizar a assertividade.")
    st.markdown("---")

    # Seletor de Estratégia de Filtros para Geração
    estrategia = st.radio(
        "🛠️ Selecione a Estratégia de Filtros para Geração",
        [
            "⚡ Filtros Otimizados Personalizados (Salvos a partir da Análise)",
            "🟢 Filtros Padrões Originais (Configuração Padrão da Loteria)"
        ],
        index=0,
        key=f"estrategia_geracao_{lottery_type}"
    )

    if "Padrões" in estrategia:
        if lottery_type == "megasena":
            cfg = ms_filters.default_filter_config()
        else:
            cfg = lf_filters.default_filter_config()
        st.info("ℹ️ **Modo Filtros Padrões:** Usando regras padrões originais de fábrica. (Dica: você pode ajustá-las abaixo e clicar em Salvar para criar uma nova configuração personalizada).")
    else:
        cfg = load_filter_config(config_path, lottery_type)
        st.success("🎯 **Modo Filtros Personalizados:** Os limites calibrados na aba de análise de tendências estão ativos.")

    cfg = _filters_editor(cfg, lottery_type)

    # Modo de geração (Score & Rank disponível apenas para Lotofácil)
    modo_score_rank = False
    pool_size = 3000
    max_overlap = 12
    peso_anti_pop = 0.25
    strict_filters = True

    if lottery_type == "lotofacil":
        modo = st.radio(
            "🧮 Modo de Geração",
            [
                "🏆 Score & Rank — gera milhares de candidatos, pontua e escolhe os melhores (recomendado)",
                "🎲 Clássico — aprova o primeiro candidato que passar nos filtros",
            ],
            index=0,
            key="modo_geracao_lf",
        )
        modo_score_rank = "Score & Rank" in modo

        if modo_score_rank:
            with st.expander("⚙️ Parâmetros do Score & Rank", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    pool_size = st.slider("Tamanho do pool de candidatos", 500, 20000, 3000, step=500)
                    max_overlap = st.slider(
                        "Sobreposição máxima entre bilhetes da carteira",
                        8, 14, 12,
                        help="Quanto menor, mais diversificados os jogos entre si (maior cobertura do volante)."
                    )
                with col_b:
                    peso_anti_pop = st.slider(
                        "Peso do Anti-Popularidade", 0.0, 1.0, 0.25, step=0.05,
                        help="Evita padrões muito jogados (sequências, linhas cheias, resultados passados). "
                             "Não muda a chance de acertar — aumenta o rateio esperado nos prêmios de 14/15."
                    )
                    strict_filters = st.checkbox(
                        "Exigir aprovação nos filtros (modo estrito)", value=True,
                        help="Desmarcado: os filtros deixam de ser eliminatórios e viram apenas influência no score."
                    )

    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Quantidade de Bilhetes a Gerar", min_value=1, max_value=500, value=5, step=1)
    with col2:
        max_attempts = st.number_input("Limite Máximo de Tentativas", min_value=1000, max_value=3000000, value=500000, step=100000)

    st.write("")
    if st.button("✨ Executar Geração Inteligente", type="primary", use_container_width=True):
        with connect_db(DB_PATH) as conn:
            total_draws = count_draws(conn, lottery_type)
            draws = get_recent_draws(conn, lottery_type, 1)

        if total_draws == 0:
            st.warning("⚠️ Banco vazio. Faça a carga inicial antes de gerar palpites.")
            return

        with st.spinner("Processando combinações matemáticas e aplicando filtros..."):
            if lottery_type == "lotofacil":
                previous = draws[-1]["dezenas"] if draws else []
                # Calcula ciclo atual para injetar ausentes no gerador
                with connect_db(DB_PATH) as conn:
                    all_draws = get_all_draws(conn, lottery_type)
                ciclo_stats = lf_analyzer.calculate_lotofacil_cycles(all_draws)
                ausentes = ciclo_stats["dezenas_ausentes_atual"]

                if modo_score_rank:
                    context = lf_scoring.build_scoring_context(all_draws, window=120)
                    weights = lf_scoring.ScoringWeights(anti_popularidade=peso_anti_pop)
                    resultado = lf_scoring.generate_ranked_games(
                        cfg,
                        context,
                        amount=int(amount),
                        pool_size=int(pool_size),
                        max_attempts=int(max_attempts),
                        weights=weights,
                        max_overlap=int(max_overlap),
                        strict_filters=strict_filters,
                    )
                    _render_score_rank_result(resultado)
                    return

                games = lf_filters.generate_filtered_games(cfg, previous, int(amount), int(max_attempts), ausentes)
            else:
                # Mega-Sena: Filtro de quentes/frias baseadas nos últimos 120 jogos
                with connect_db(DB_PATH) as conn:
                    all_draws = get_all_draws(conn, lottery_type)
                    recent_stats = get_recent_stats(conn, lottery_type, 120)
                analysis = ms_analyzer.sliding_window_analysis(all_draws, recent_stats, 120)
                
                # Extrai quentes e frias da tabela de frequências
                hot = [item["Dezena"] for item in analysis["frequencia_completa"] if "Quente" in item["Categoria"]]
                cold = [item["Dezena"] for item in analysis["frequencia_completa"] if "Fria" in item["Categoria"]]
                
                games = ms_filters.generate_filtered_games(cfg, int(amount), int(max_attempts), hot, cold)

        st.markdown(f"**Resultado da Geração:** Foram gerados **{len(games)}** bilhetes aprovados pelo pipeline de filtros!")

        if not games:
            st.error("😭 Nenhum bilhete atendeu a todas as restrições estatísticas simultaneamente. Relaxe um pouco os filtros ou aumente o Limite de Tentativas.")
            return

        jogos_formatados = []
        for i, game in enumerate(games, 1):
            s_jogo = "  ➖  ".join(f"{n:02d}" for n in game)
            jogos_formatados.append({"Bilhete": f"Sugestão #{i}", "Dezenas Aprovadas": s_jogo})

        st.dataframe(pd.DataFrame(jogos_formatados), use_container_width=True)
        st.success("🍀 Boa sorte em suas apostas! Registre os bilhetes em uma casa lotérica ou aplicativo oficial da Caixa.")


def _resultados_section(lottery_type: str) -> None:
    accent_color = "#8A2BE2" if lottery_type == "lotofacil" else "#20C997"
    lottery_name = "Lotofácil" if lottery_type == "lotofacil" else "Mega-Sena"

    st.markdown(f"<h2 style='color: {accent_color}; text-align: center;'>🧐 Consulta Histórica de Concursos ({lottery_name})</h2>", unsafe_allow_html=True)
    st.caption("Consulte resultados e dezenas sorteadas de qualquer concurso registrado.")
    st.markdown("---")

    with connect_db(DB_PATH) as conn:
        total = count_draws(conn, lottery_type)
        last_concurso = get_last_concurso(conn, lottery_type)

    if total == 0 or last_concurso is None:
        st.warning("⚠️ Banco de dados vazio. Realize a importação dos dados para habilitar a consulta.")
        return

    # Gerenciamento de estado do concurso ativo
    state_key = f"concurso_active_{lottery_type}"
    if state_key not in st.session_state:
        st.session_state[state_key] = last_concurso

    tab_busca, tab_recentes = st.tabs(["🔍 Busca Individual por Concurso", "📜 Tabela Completa de Resultados"])

    with tab_busca:
        col_search_1, col_search_2 = st.columns([4, 1])
        with col_search_1:
            busca_input = st.number_input(
                "Pesquisar Concurso N°:",
                min_value=1,
                max_value=last_concurso,
                value=st.session_state[state_key],
                label_visibility="collapsed"
            )
        with col_search_2:
            if st.button("🔍 Ir para Sorteio", use_container_width=True):
                st.session_state[state_key] = busca_input
                st.rerun()

        st.write("")

        with connect_db(DB_PATH) as conn:
            draw = get_draw_by_concurso(conn, lottery_type, int(st.session_state[state_key]))

        col_ant, col_titulo, col_prox = st.columns([1, 4, 1])
        
        with col_ant:
            if st.button("⬅️ Sorteio Anterior", use_container_width=True, disabled=(st.session_state[state_key] <= 1)):
                st.session_state[state_key] -= 1
                st.rerun()

        with col_titulo:
            if draw:
                st.markdown(f"<h3 style='text-align: center; color: {accent_color};'>RESULTADO {lottery_name.upper()} - CONCURSO {draw['concurso']}</h3>", unsafe_allow_html=True)
                if draw['data_sorteio']:
                    st.markdown(f"<p style='text-align: center; font-size: 14px;'>Data do Sorteio: {draw['data_sorteio']}</p>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align: center;'>Concurso não localizado no banco.</h3>", unsafe_allow_html=True)

        with col_prox:
            if st.button("Próximo Sorteio ➡️", use_container_width=True, disabled=(st.session_state[state_key] >= last_concurso)):
                st.session_state[state_key] += 1
                st.rerun()

        if draw:
            s_jogo = "  ➖  ".join(f"{n:02d}" for n in draw['dezenas'])
            
            # Moldura visual especial para o resultado sorteado
            st.markdown(
                f"<div style='border: 2px solid {accent_color}; border-radius: 12px; padding: 25px; "
                f"background-color: rgba(255, 255, 255, 0.02); text-align: center; margin: 20px 0;'>"
                f"<p style='font-size: 32px; font-weight: 700; color: #FFFFFF; letter-spacing: 3px; margin: 0;'>{s_jogo}</p>"
                f"</div>",
                unsafe_allow_html=True
            )

    with tab_recentes:
        page_key = f"page_{lottery_type}"
        if page_key not in st.session_state:
            st.session_state[page_key] = 0

        col_qtd, _ = st.columns([1, 4])
        with col_qtd:
            per_page = st.selectbox("Itens por página:", [10, 25, 50], index=0, key=f"sel_per_{lottery_type}")

        with connect_db(DB_PATH) as conn:
            all_draws = get_all_draws(conn, lottery_type)
            
        all_draws.sort(key=lambda x: x["concurso"], reverse=True)
        total_pages = max(1, (len(all_draws) + per_page - 1) // per_page)
        
        if st.session_state[page_key] >= total_pages:
            st.session_state[page_key] = total_pages - 1
            
        col_ant, col_pag, col_prox = st.columns([1, 4, 1])
        with col_ant:
            if st.button("⬅️ Página Anterior", use_container_width=True, disabled=(st.session_state[page_key] <= 0), key=f"btn_p_ant_{lottery_type}"):
                st.session_state[page_key] -= 1
                st.rerun()
                
        with col_pag:
            st.markdown(f"<h4 style='text-align: center; margin-top: 5px;'>Página {st.session_state[page_key] + 1} de {total_pages}</h4>", unsafe_allow_html=True)
            
        with col_prox:
            if st.button("Próxima Página ➡️", use_container_width=True, disabled=(st.session_state[page_key] >= total_pages - 1), key=f"btn_p_prox_{lottery_type}"):
                st.session_state[page_key] += 1
                st.rerun()
                
        start_idx = st.session_state[page_key] * per_page
        end_idx = start_idx + per_page
        page_items = all_draws[start_idx:end_idx]

        st.write("")
        for d in page_items:
            s_jogo = "  ➖  ".join(f"{n:02d}" for n in d['dezenas'])
            data_str = f" ({d['data_sorteio']})" if d['data_sorteio'] else ""
            st.markdown(
                f"<div style='border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 15px; margin-bottom: 10px; background-color: rgba(255,255,255,0.01);'>"
                f"<h5 style='margin: 0; color: {accent_color};'>Concurso N° {d['concurso']} <span style='font-size: 13px; color: gray;'>{data_str}</span></h5>"
                f"<p style='font-size: 18px; font-weight: bold; margin: 10px 0 0 0; letter-spacing: 1.5px;'>{s_jogo}</p>"
                f"</div>",
                unsafe_allow_html=True
            )


def main() -> None:
    _bootstrap_db()

    with st.sidebar:
        st.markdown("<h1 style='text-align: center; color: #8A2BE2;'>🧠 Loterias Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 14px;'>Motor Avançado de Estatística Caixa</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Seletor de Loteria Principal
        loteria = st.radio(
            "🎯 Escolha a Loteria",
            ["🍀 Lotofácil", "💰 Mega-Sena"],
            index=0
        )
        
        lottery_type = "lotofacil" if "Lotofácil" in loteria else "megasena"
        
        st.markdown("---")
        
        # Menu de Navegação da Loteria
        menu = st.radio(
            "📍 Navegação",
            [
                "📊 Painel de Status",
                "📥 Carga de Planilha",
                "🔄 Sincronizar p/ API",
                "📈 Análise Estatística",
                "🎲 Gerador Inteligente",
                "🔬 Backtest de Estratégias",
                "🧐 Histórico e Resultados",
            ],
        )

    # Roteamento de Tela
    if menu == "📊 Painel de Status":
        _status_section(lottery_type)
    elif menu == "📥 Carga de Planilha":
        _load_excel_section(lottery_type)
    elif menu == "🔄 Sincronizar p/ API":
        _update_api_section(lottery_type)
    elif menu == "📈 Análise Estatística":
        _analysis_section(lottery_type)
    elif menu == "🎲 Gerador Inteligente":
        _generate_section(lottery_type)
    elif menu == "🔬 Backtest de Estratégias":
        _backtest_section(lottery_type)
    elif menu == "🧐 Histórico e Resultados":
        _resultados_section(lottery_type)


if __name__ == "__main__":
    main()
