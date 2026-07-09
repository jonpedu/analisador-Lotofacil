from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from src.lotofacil.filters import default_filter_config
from src.lotofacil.scoring import ScoringWeights, build_scoring_context, generate_ranked_games

TODAS_DEZENAS = list(range(1, 26))

# Estratégia recebe o histórico (lista de dicts com "dezenas", em ordem
# cronológica, SEM o concurso a ser previsto) e devolve um bilhete de 15 dezenas.
Strategy = Callable[[list[dict[str, Any]], random.Random], list[int]]


# ---------------------------------------------------------------------------
# Referência teórica: distribuição hipergeométrica de acertos de um bilhete
# qualquer (15 escolhidas de 25, 15 sorteadas). Nenhuma estratégia muda isso;
# o backtest serve para PROVAR esse fato e para comparar estratégias com rigor.
# ---------------------------------------------------------------------------

def theoretical_distribution() -> dict[int, float]:
    total = math.comb(25, 15)
    return {
        k: math.comb(15, k) * math.comb(10, 15 - k) / total
        for k in range(5, 16)
    }


def theoretical_summary() -> dict[str, float]:
    dist = theoretical_distribution()
    return {
        "media": 9.0,
        "pct_11": round(100 * sum(p for k, p in dist.items() if k >= 11), 2),
        "pct_12": round(100 * sum(p for k, p in dist.items() if k >= 12), 2),
        "pct_13": round(100 * sum(p for k, p in dist.items() if k >= 13), 3),
        "pct_14": round(100 * sum(p for k, p in dist.items() if k >= 14), 4),
    }


# ---------------------------------------------------------------------------
# Estratégias disponíveis
# ---------------------------------------------------------------------------

def _atrasos(history: list[dict[str, Any]]) -> dict[int, int]:
    atraso: dict[int, int] = {}
    for n in TODAS_DEZENAS:
        count = 0
        for draw in reversed(history):
            if n in draw["dezenas"]:
                break
            count += 1
        atraso[n] = count
    return atraso


def strat_aleatorio(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    return sorted(rng.sample(TODAS_DEZENAS, 15))


def strat_mais_atrasadas(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    atraso = _atrasos(history)
    return sorted(sorted(TODAS_DEZENAS, key=lambda n: -atraso[n])[:15])


def strat_quentes(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    freq = Counter(n for d in history[-20:] for n in d["dezenas"])
    return sorted(sorted(TODAS_DEZENAS, key=lambda n: -freq.get(n, 0))[:15])


def strat_frias(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    freq = Counter(n for d in history[-20:] for n in d["dezenas"])
    return sorted(sorted(TODAS_DEZENAS, key=lambda n: freq.get(n, 0))[:15])


def strat_repete_anterior(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    prev = list(history[-1]["dezenas"])
    comp = [n for n in TODAS_DEZENAS if n not in prev]
    return sorted(rng.sample(prev, 9) + rng.sample(comp, 6))


def strat_ciclo_ausentes(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    # Reconstrói o ciclo como o app faz: acumula desde o início, zera ao fechar
    cycle: set[int] = set()
    for d in history:
        cycle |= set(d["dezenas"])
        if len(cycle) == 25:
            cycle = set()
    ausentes = [n for n in TODAS_DEZENAS if n not in cycle]
    ticket = list(ausentes)[:15]
    atraso = _atrasos(history)
    for n in sorted(TODAS_DEZENAS, key=lambda x: -atraso[x]):
        if len(ticket) >= 15:
            break
        if n not in ticket:
            ticket.append(n)
    return sorted(ticket)


def strat_score_rank(history: list[dict[str, Any]], rng: random.Random) -> list[int]:
    # Versão leve do gerador Score & Rank para o backtest (pool reduzido)
    context = build_scoring_context(history, window=min(120, len(history)))
    cfg = default_filter_config()
    result = generate_ranked_games(
        cfg,
        context,
        amount=1,
        pool_size=200,
        max_attempts=4000,
        weights=ScoringWeights(),
        strict_filters=False,
        rng=rng,
    )
    if result["jogos"]:
        return result["jogos"][0]["dezenas"]
    return strat_aleatorio(history, rng)


STRATEGIES: dict[str, Strategy] = {
    "Aleatório puro (baseline)": strat_aleatorio,
    "15 mais atrasadas": strat_mais_atrasadas,
    "15 mais quentes (janela 20)": strat_quentes,
    "15 mais frias (janela 20)": strat_frias,
    "Repete 9 do anterior": strat_repete_anterior,
    "Ausentes do ciclo + atrasadas": strat_ciclo_ausentes,
    "Score & Rank (gerador do app)": strat_score_rank,
}

# Estratégias caras: sugere-se limitar a quantidade de concursos testados na UI
ESTRATEGIAS_LENTAS = {"Score & Rank (gerador do app)"}


# ---------------------------------------------------------------------------
# Motor de backtest
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    estrategia: str
    concursos_testados: int
    media: float
    pct_11: float
    pct_12: float
    pct_13: float
    pct_14: float
    melhor: int
    distribuicao: dict[int, int] = field(default_factory=dict)


def run_backtest(
    all_draws: list[dict[str, Any]],
    strategy_names: list[str],
    test_last_n: int = 500,
    warmup: int = 100,
    seed: int = 42,
    progress_callback: Callable[[float], None] | None = None,
) -> list[BacktestResult]:
    """
    Para cada concurso testado, a estratégia escolhe 15 dezenas vendo APENAS os
    concursos anteriores, e o acerto é conferido contra o resultado real.
    `test_last_n` limita o teste aos N concursos mais recentes (0 = todos).
    """
    if len(all_draws) <= warmup + 1:
        raise ValueError("Histórico insuficiente para backtest (aumente a base de dados).")

    start = warmup
    if test_last_n and test_last_n > 0:
        start = max(warmup, len(all_draws) - test_last_n)

    indices = list(range(start, len(all_draws)))
    results: list[BacktestResult] = []
    total_steps = len(indices) * len(strategy_names)
    step = 0

    for name in strategy_names:
        fn = STRATEGIES[name]
        rng = random.Random(seed)
        hits_list: list[int] = []

        for i in indices:
            history = all_draws[:i]
            actual = set(all_draws[i]["dezenas"])
            ticket = fn(history, rng)
            hits_list.append(len(set(ticket) & actual))
            step += 1
            if progress_callback and step % 50 == 0:
                progress_callback(step / total_steps)

        n = len(hits_list)
        dist = dict(sorted(Counter(hits_list).items()))
        results.append(BacktestResult(
            estrategia=name,
            concursos_testados=n,
            media=round(sum(hits_list) / n, 3),
            pct_11=round(100 * sum(1 for h in hits_list if h >= 11) / n, 2),
            pct_12=round(100 * sum(1 for h in hits_list if h >= 12) / n, 2),
            pct_13=round(100 * sum(1 for h in hits_list if h >= 13) / n, 3),
            pct_14=round(100 * sum(1 for h in hits_list if h >= 14) / n, 4),
            melhor=max(hits_list),
            distribuicao=dist,
        ))

    if progress_callback:
        progress_callback(1.0)
    return results
