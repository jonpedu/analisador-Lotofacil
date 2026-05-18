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


def sliding_window_analysis(
    all_draws: list[dict[str, Any]],
    recent_stats: list[dict[str, int]],
    window: int,
) -> dict[str, Any]:
    if not all_draws:
        return {
            "mais_sorteadas": [],
            "menos_sorteadas": [],
            "atrasos": {},
            "medias": {},
            "modas": {},
            "sugestoes": {},
        }

    recent_draws = all_draws[-window:] if window > 0 else all_draws
    dezenas_flat = [d for draw in recent_draws for d in draw["dezenas"]]
    freq = Counter(dezenas_flat)

    for dezena in range(1, 26):
        freq.setdefault(dezena, 0)

    mais_sorteadas = freq.most_common(10)
    menos_sorteadas = sorted(freq.items(), key=lambda item: item[1])[:10]

    atraso_por_dezena: dict[int, int] = {}
    for dezena in range(1, 26):
        atraso = 0
        for draw in reversed(all_draws):
            if dezena in draw["dezenas"]:
                break
            atraso += 1
        atraso_por_dezena[dezena] = atraso

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
            values = df[col].astype(int).tolist()
            medias[col] = float(mean(values))
            modas[col] = _safe_mode(values)

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
        "max_consecutive": 6,
    }

    return {
        "mais_sorteadas": mais_sorteadas,
        "menos_sorteadas": menos_sorteadas,
        "atrasos": atraso_por_dezena,
        "medias": medias,
        "modas": modas,
        "sugestoes": sugestoes,
    }
