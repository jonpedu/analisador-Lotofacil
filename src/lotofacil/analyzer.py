from __future__ import annotations

from collections import Counter
from statistics import StatisticsError, mean, mode
from typing import Any

import pandas as pd

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}


def calculate_draw_stats(dezenas: list[int]) -> dict[str, int]:
    dezenas_set = set(dezenas)
    qtd_pares = sum(1 for d in dezenas if d % 2 == 0)

    return {
        "soma": int(sum(dezenas)),
        "qtd_pares": int(qtd_pares),
        "qtd_impares": int(len(dezenas) - qtd_pares),
        "qtd_primos": int(sum(1 for d in dezenas if d in PRIMOS)),
        "qtd_fibonacci": int(sum(1 for d in dezenas if d in FIBONACCI)),
        "qtd_multiplos_3": int(sum(1 for d in dezenas if d % 3 == 0)),
        "qtd_moldura": int(sum(1 for d in dezenas_set if d in MOLDURA)),
    }


def _safe_mode(values: list[int]) -> int | None:
    try:
        return int(mode(values))
    except StatisticsError:
        return None


def calculate_lotofacil_cycles(all_draws: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calcula o histórico de ciclos da Lotofácil e o estado do ciclo atual.
    Um ciclo se inicia no concurso 1 (ou após o fechamento do ciclo anterior)
    e termina quando todas as 25 dezenas foram sorteadas pelo menos uma vez.
    """
    if not all_draws:
        return {
            "ciclo_atual_numero": 1,
            "concursos_no_ciclo_atual": 0,
            "dezenas_sorteadas_atual": [],
            "dezenas_ausentes_atual": list(range(1, 26)),
            "historico_ciclos": [],
        }

    ciclos = []
    concursos_ciclo_atual = 0
    sorteadas_no_ciclo = set()
    inicio_concurso = all_draws[0]["concurso"]
    ciclo_numero = 1

    for draw in all_draws:
        concursos_ciclo_atual += 1
        sorteadas_no_ciclo.update(draw["dezenas"])

        if len(sorteadas_no_ciclo) == 25:
            # Ciclo fechou!
            ciclos.append({
                "ciclo": ciclo_numero,
                "duracao": concursos_ciclo_atual,
                "fim_concurso": draw["concurso"],
            })
            # Reseta para o próximo ciclo
            sorteadas_no_ciclo = set()
            concursos_ciclo_atual = 0
            ciclo_numero += 1

    dezenas_ausentes = sorted(list(set(range(1, 26)) - sorteadas_no_ciclo))

    return {
        "ciclo_atual_numero": ciclo_numero,
        "concursos_no_ciclo_atual": concursos_ciclo_atual,
        "dezenas_sorteadas_atual": sorted(list(sorteadas_no_ciclo)),
        "dezenas_ausentes_atual": dezenas_ausentes,
        "historico_ciclos": ciclos,
    }


def sliding_window_analysis(
    all_draws: list[dict[str, Any]],
    recent_stats: list[dict[str, int]],
    window: int,
) -> dict[str, Any]:
    if not all_draws:
        return {
            "frequencia_completa": [],
            "atrasos": {},
            "medias": {},
            "modas": {},
            "sugestoes": {},
            "ciclo": {},
        }

    recent_draws = all_draws[-window:] if window > 0 else all_draws
    dezenas_flat = [d for draw in recent_draws for d in draw["dezenas"]]
    freq = Counter(dezenas_flat)

    # Garante que todos os 25 números existam na contagem
    for dezena in range(1, 26):
        freq.setdefault(dezena, 0)

    # Calcula o atraso atual para cada dezena
    atraso_por_dezena: dict[int, int] = {}
    for dezena in range(1, 26):
        atraso = 0
        for draw in reversed(all_draws):
            if dezena in draw["dezenas"]:
                break
            atraso += 1
        atraso_por_dezena[dezena] = atraso

    # Tabela unificada de frequências ordenadas
    total_sorteios = len(recent_draws)
    frequencia_completa = []
    
    # Classificação de Quente, Fria, Intermediária baseada em limites de freq
    sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    # Top 8 mais frequentes -> Quentes
    # Bottom 8 menos frequentes -> Frias
    # O resto -> Intermediárias
    quentes = {item[0] for item in sorted_items[:8]}
    frias = {item[0] for item in sorted_items[-8:]}

    for dezena, count in sorted_items:
        pct = (count / total_sorteios) * 100 if total_sorteios > 0 else 0.0
        
        if dezena in quentes:
            categoria = "🔥 Quente"
        elif dezena in frias:
            categoria = "❄️ Fria"
        else:
            categoria = "⚡ Intermediária"

        frequencia_completa.append({
            "Dezena": dezena,
            "Frequência": count,
            "Frequência (%)": round(pct, 1),
            "Atraso Atual": atraso_por_dezena[dezena],
            "Categoria": categoria
        })

    medias: dict[str, float] = {}
    modas: dict[str, int | None] = {}
    if recent_stats:
        df = pd.DataFrame(recent_stats)
        for col in [
            "soma",
            "qtd_pares",
            "qtd_impares",
            "qtd_primos",
            "qtd_fibonacci",
            "qtd_multiplos_3",
            "qtd_moldura",
        ]:
            if col in df.columns:
                values = df[col].astype(int).tolist()
                medias[col] = float(mean(values))
                modas[col] = _safe_mode(values)

    # Média de dezenas repetidas do concurso anterior
    repeticoes = []
    for idx in range(1, len(recent_draws)):
        prev_set = set(recent_draws[idx - 1]["dezenas"])
        curr_set = set(recent_draws[idx]["dezenas"])
        repeticoes.append(len(prev_set.intersection(curr_set)))
    media_repeticao = float(mean(repeticoes)) if repeticoes else 9.0

    pares_impares_counter = Counter()
    for draw in recent_draws:
        pares = sum(1 for d in draw["dezenas"] if d % 2 == 0)
        impares = 15 - pares
        pares_impares_counter[(pares, impares)] += 1

    top_pares_impares = [
        [int(k[0]), int(k[1])] for k, _ in pares_impares_counter.most_common(3)
    ] or [[7, 8], [8, 7], [9, 6]]

    # Calcula ciclos
    ciclo_stats = calculate_lotofacil_cycles(all_draws)

    sugestoes = {
        "allowed_even_odd_pairs": top_pares_impares,
        "sum_min": max(150, int(medias.get("soma", 200) - 15)),
        "sum_max": min(260, int(medias.get("soma", 200) + 15)),
        "repeat_min": max(6, int(round(media_repeticao) - 1)),
        "repeat_max": min(12, int(round(media_repeticao) + 1)),
        "prime_min": max(2, int(round(medias.get("qtd_primos", 5) - 1))),
        "prime_max": min(8, int(round(medias.get("qtd_primos", 5) + 1))),
        "fibonacci_min": max(2, int(round(medias.get("qtd_fibonacci", 4) - 1))),
        "fibonacci_max": min(7, int(round(medias.get("qtd_fibonacci", 4) + 1))),
        "multiple3_min": max(2, int(round(medias.get("qtd_multiplos_3", 5) - 1))),
        "multiple3_max": min(8, int(round(medias.get("qtd_multiplos_3", 5) + 1))),
        "moldura_min": max(7, int(round(medias.get("qtd_moldura", 10) - 1))),
        "moldura_max": min(13, int(round(medias.get("qtd_moldura", 10) + 1))),
        "row_min": 1,
        "row_max": 4,
        "col_min": 1,
        "col_max": 4,
        "max_consecutive": 4,
    }

    return {
        "frequencia_completa": frequencia_completa,
        "atrasos": atraso_por_dezena,
        "medias": medias,
        "modas": modas,
        "sugestoes": sugestoes,
        "ciclo": ciclo_stats,
    }
