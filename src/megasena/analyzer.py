from __future__ import annotations

from collections import Counter
from statistics import StatisticsError, mean, mode
from typing import Any

import pandas as pd

PRIMOS_MEGA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
FIBONACCI_MEGA = {1, 2, 3, 5, 8, 13, 21, 34, 55}


def get_quadrant(n: int) -> int:
    """
    Retorna o quadrante de uma dezena da Mega-Sena (1 a 60).
    A cartela possui 6 linhas e 10 colunas:
      Q1 (Superior Esquerdo): Linhas 1-3, Colunas 1-5
      Q2 (Superior Direito): Linhas 1-3, Colunas 6-10
      Q3 (Inferior Esquerdo): Linhas 4-6, Colunas 1-5
      Q4 (Inferior Direito): Linhas 4-6, Colunas 6-10
    """
    row = (n - 1) // 10  # 0 a 5
    col = (n - 1) % 10   # 0 a 9
    if row <= 2:
        return 1 if col <= 4 else 2
    else:
        return 3 if col <= 4 else 4


def calculate_draw_stats(dezenas: list[int]) -> dict[str, int]:
    qtd_pares = sum(1 for d in dezenas if d % 2 == 0)
    q1 = sum(1 for d in dezenas if get_quadrant(d) == 1)
    q2 = sum(1 for d in dezenas if get_quadrant(d) == 2)
    q3 = sum(1 for d in dezenas if get_quadrant(d) == 3)
    q4 = sum(1 for d in dezenas if get_quadrant(d) == 4)

    return {
        "soma": int(sum(dezenas)),
        "qtd_pares": int(qtd_pares),
        "qtd_impares": int(len(dezenas) - qtd_pares),
        "qtd_primos": int(sum(1 for d in dezenas if d in PRIMOS_MEGA)),
        "qtd_fibonacci": int(sum(1 for d in dezenas if d in FIBONACCI_MEGA)),
        "q1_count": q1,
        "q2_count": q2,
        "q3_count": q3,
        "q4_count": q4,
    }


def _safe_mode(values: list[int]) -> int | None:
    try:
        return int(mode(values))
    except StatisticsError:
        return None


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
        }

    recent_draws = all_draws[-window:] if window > 0 else all_draws
    dezenas_flat = [d for draw in recent_draws for d in draw["dezenas"]]
    freq = Counter(dezenas_flat)

    # Garante que todos os 60 números existam na contagem
    for dezena in range(1, 61):
        freq.setdefault(dezena, 0)

    # Calcula o atraso atual para cada dezena da Mega-Sena
    atraso_por_dezena: dict[int, int] = {}
    for dezena in range(1, 61):
        atraso = 0
        for draw in reversed(all_draws):
            if dezena in draw["dezenas"]:
                break
            atraso += 1
        atraso_por_dezena[dezena] = atraso

    # Tabela unificada de frequências ordenadas (do mais sorteado para o menos)
    total_sorteios = len(recent_draws)
    frequencia_completa = []
    
    sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    # Classificação em Quentes, Frias e Intermediárias
    # Top 15 -> Quentes, Bottom 15 -> Frias, Resto -> Intermediárias
    quentes = {item[0] for item in sorted_items[:15]}
    frias = {item[0] for item in sorted_items[-15:]}

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
            "q1_count",
            "q2_count",
            "q3_count",
            "q4_count",
        ]:
            if col in df.columns:
                values = df[col].astype(int).tolist()
                medias[col] = float(mean(values))
                modas[col] = _safe_mode(values)

    sugestoes = {
        "even_min": max(1, int(round(medias.get("qtd_pares", 3)) - 1)),
        "even_max": min(5, int(round(medias.get("qtd_pares", 3)) + 1)),
        "sum_min": max(60, int(medias.get("soma", 183) - 40)),
        "sum_max": min(300, int(medias.get("soma", 183) + 40)),
        "prime_min": max(0, int(round(medias.get("qtd_primos", 1.5)) - 1)),
        "prime_max": min(4, int(round(medias.get("qtd_primos", 1.5)) + 1)),
        "fibonacci_min": max(0, int(round(medias.get("qtd_fibonacci", 1.0)) - 1)),
        "fibonacci_max": min(3, int(round(medias.get("qtd_fibonacci", 1.0)) + 1)),
        "q_min": 0,
        "q_max": 3,  # Máximo de dezenas por quadrante para evitar alta concentração
    }

    return {
        "frequencia_completa": frequencia_completa,
        "atrasos": atraso_por_dezena,
        "medias": medias,
        "modas": modas,
        "sugestoes": sugestoes,
    }
