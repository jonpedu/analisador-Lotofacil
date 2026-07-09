from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

from src.lotofacil.analyzer import (
    MOLDURA,
    calculate_draw_stats,
    calculate_lotofacil_cycles,
)
from src.lotofacil.filters import (
    FilterConfig,
    TicketPipeline,
    _max_consecutive_seq,
    _row_col_counts,
    build_structured_candidate,
)

# Métricas estatísticas usadas na aderência ao perfil histórico
METRICAS_ADERENCIA = [
    "soma",
    "qtd_pares",
    "qtd_primos",
    "qtd_fibonacci",
    "qtd_multiplos_3",
    "qtd_moldura",
]

# Desvio-padrão mínimo para evitar divisão por zero em janelas muito homogêneas
STD_MINIMO = 0.8


@dataclass
class ScoringWeights:
    """
    Pesos de cada componente do score (0 a 1 cada).
    IMPORTANTE: nenhum componente altera a probabilidade de acerto do bilhete —
    aderência/frequência/repetição apenas moldam o perfil do jogo, e o
    anti-popularidade aumenta o rateio esperado nos prêmios de 14/15 pontos.
    """
    aderencia_estatistica: float = 0.40
    equilibrio_frequencia: float = 0.20
    repeticao_anterior: float = 0.15
    anti_popularidade: float = 0.25


def _gauss_kernel(value: float, media: float, std: float) -> float:
    """Converte distância da média em nota 0..1 (1 = exatamente na média)."""
    z = (value - media) / max(std, STD_MINIMO)
    return math.exp(-0.5 * z * z)


def build_scoring_context(all_draws: list[dict[str, Any]], window: int = 120) -> dict[str, Any]:
    """
    Prepara tudo que o score precisa a partir do histórico:
    médias/desvios da janela, frequência por dezena, concurso anterior,
    dezenas ausentes do ciclo e o conjunto de resultados já sorteados
    (usado pelo anti-popularidade: muita gente joga resultados passados).
    """
    if not all_draws:
        raise ValueError("Histórico vazio: carregue os sorteios antes de gerar jogos.")

    recent = all_draws[-window:] if window > 0 else all_draws
    stats_list = [calculate_draw_stats(d["dezenas"]) for d in recent]

    metric_stats: dict[str, tuple[float, float]] = {}
    for metrica in METRICAS_ADERENCIA:
        valores = [s[metrica] for s in stats_list]
        metric_stats[metrica] = (mean(valores), pstdev(valores))

    # Repetição entre concursos consecutivos dentro da janela
    repeticoes = []
    for idx in range(1, len(recent)):
        repeticoes.append(len(set(recent[idx - 1]["dezenas"]) & set(recent[idx]["dezenas"])))
    rep_media = mean(repeticoes) if repeticoes else 9.0
    rep_std = pstdev(repeticoes) if len(repeticoes) > 1 else 1.0

    # Frequência relativa por dezena na janela
    total = len(recent)
    freq: dict[int, float] = {n: 0.0 for n in range(1, 26)}
    for d in recent:
        for n in d["dezenas"]:
            freq[n] += 1.0
    for n in freq:
        freq[n] /= total
    freq_valores = list(freq.values())
    freq_media_geral = mean(freq_valores)
    freq_std_geral = max(pstdev(freq_valores), 0.005)

    ciclo = calculate_lotofacil_cycles(all_draws)

    return {
        "window": len(recent),
        "metric_stats": metric_stats,
        "repeat_media": rep_media,
        "repeat_std": rep_std,
        "freq": freq,
        "freq_media_geral": freq_media_geral,
        "freq_std_geral": freq_std_geral,
        "previous": list(all_draws[-1]["dezenas"]),
        "cycle_absent": list(ciclo["dezenas_ausentes_atual"]),
        "past_sets": {frozenset(d["dezenas"]) for d in all_draws},
    }


def popularity_penalty(ticket: list[int], past_sets: set[frozenset] | None = None) -> float:
    """
    Estima o quão "popular" (jogado por muita gente) é o padrão do bilhete, 0..1.
    Padrões populares não perdem chance de sair — perdem valor no rateio de 14/15.
    Componentes: sequências longas, linhas/colunas cheias no volante, excesso de
    dezenas "de calendário" (<=12), moldura completa e repetição de resultados passados.
    """
    ticket_sorted = sorted(ticket)

    # Sequências consecutivas longas (ex.: 1-2-3-4-5...) são muito jogadas
    run = _max_consecutive_seq(ticket_sorted)
    p_consec = min(1.0, max(0.0, (run - 3) / 6.0))

    # Linhas ou colunas completas no volante 5x5 formam desenhos visuais populares
    rows, cols = _row_col_counts(ticket_sorted)
    linhas_cheias = sum(1 for r in rows if r == 5) + sum(1 for c in cols if c == 5)
    p_linhas = min(1.0, linhas_cheias / 3.0)

    # Excesso de dezenas <= 12 (meses/aniversários)
    meses = sum(1 for n in ticket_sorted if n <= 12)
    p_datas = min(1.0, max(0.0, (meses - 9) / 5.0))

    # Bilhete inteiro na moldura = desenho de "quadro" no volante
    p_moldura = 1.0 if all(n in MOLDURA for n in ticket_sorted) else 0.0

    # Repetir um resultado que já saiu (muita gente joga o último resultado)
    p_passado = 0.0
    if past_sets and frozenset(ticket_sorted) in past_sets:
        p_passado = 1.0

    penalidade = (
        0.40 * p_consec
        + 0.30 * p_linhas
        + 0.20 * p_datas
        + 0.30 * p_moldura
        + 1.00 * p_passado
    )
    return min(1.0, penalidade)


def score_ticket(
    ticket: list[int],
    context: dict[str, Any],
    weights: ScoringWeights | None = None,
) -> dict[str, float]:
    """
    Pontua um bilhete (0..100) combinando:
      - aderência ao perfil estatístico da janela (soma, pares, primos, etc.)
      - equilíbrio de frequência (nem só "quentes", nem só "frias")
      - repetição em relação ao concurso anterior próxima da média histórica
      - anti-popularidade (evita padrões muito jogados -> melhor rateio)
    Retorna o total e a nota de cada componente para exibição.
    """
    w = weights or ScoringWeights()
    stats = calculate_draw_stats(ticket)

    kernels = [
        _gauss_kernel(stats[m], context["metric_stats"][m][0], context["metric_stats"][m][1])
        for m in METRICAS_ADERENCIA
    ]
    aderencia = mean(kernels)

    repeticao = _gauss_kernel(
        len(set(ticket) & set(context["previous"])),
        context["repeat_media"],
        max(context["repeat_std"], STD_MINIMO),
    )

    # Frequência média das dezenas escolhidas vs. média geral da janela:
    # bilhetes só de "quentes" ou só de "frias" se afastam do centro.
    freq_media_ticket = mean(context["freq"][n] for n in ticket)
    sem = context["freq_std_geral"] / math.sqrt(15)
    z_freq = (freq_media_ticket - context["freq_media_geral"]) / max(sem, 0.003)
    equilibrio = math.exp(-0.5 * z_freq * z_freq)

    anti_pop = 1.0 - popularity_penalty(ticket, context.get("past_sets"))

    soma_pesos = (
        w.aderencia_estatistica + w.equilibrio_frequencia
        + w.repeticao_anterior + w.anti_popularidade
    )
    total = 0.0
    if soma_pesos > 0:
        total = (
            w.aderencia_estatistica * aderencia
            + w.equilibrio_frequencia * equilibrio
            + w.repeticao_anterior * repeticao
            + w.anti_popularidade * anti_pop
        ) / soma_pesos

    return {
        "total": round(100 * total, 2),
        "aderencia": round(100 * aderencia, 1),
        "equilibrio_freq": round(100 * equilibrio, 1),
        "repeticao": round(100 * repeticao, 1),
        "anti_popularidade": round(100 * anti_pop, 1),
    }


def generate_ranked_games(
    cfg: FilterConfig,
    context: dict[str, Any],
    amount: int,
    pool_size: int = 3000,
    max_attempts: int | None = None,
    weights: ScoringWeights | None = None,
    max_overlap: int = 12,
    strict_filters: bool = True,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """
    Gerador Score & Rank:
      1. Gera um pool grande de candidatos estruturados (sem repetidos).
      2. Pontua todos com score_ticket.
      3. Seleciona os top-N de forma diversificada: um novo jogo só entra se
         compartilhar no máximo `max_overlap` dezenas com cada jogo já escolhido
         (carteiras com jogos quase iguais desperdiçam cobertura).
    Com strict_filters=True, só entram no pool candidatos aprovados no pipeline
    de filtros; com False, os filtros viram apenas influência do score.
    """
    rnd = rng if rng is not None else random.Random()
    pipeline = TicketPipeline()
    previous = context["previous"]
    previous_set = set(previous)
    complementary = sorted(set(range(1, 26)) - previous_set)
    cycle_absent_set = set(context.get("cycle_absent") or [])

    if max_attempts is None:
        max_attempts = pool_size * 30

    pool: set[tuple[int, ...]] = set()
    descartados_filtro = 0
    attempts = 0
    while len(pool) < pool_size and attempts < max_attempts:
        attempts += 1
        game = build_structured_candidate(cfg, previous_set, complementary, cycle_absent_set, rnd)
        if len(game) != 15:
            continue
        if strict_filters and not pipeline.validate(game, cfg, previous):
            descartados_filtro += 1
            continue
        pool.add(tuple(game))

    scored = [
        {"dezenas": list(t), "score": score_ticket(list(t), context, weights)}
        for t in pool
    ]
    scored.sort(key=lambda item: item["score"]["total"], reverse=True)

    # Seleção gulosa com restrição de sobreposição; relaxa o limite se faltar jogo
    selecionados: list[dict[str, Any]] = []
    overlap_limite = max_overlap
    while len(selecionados) < amount and overlap_limite <= 14:
        for item in scored:
            if len(selecionados) >= amount:
                break
            dezenas_set = set(item["dezenas"])
            if any(set(s["dezenas"]) == dezenas_set for s in selecionados):
                continue
            if all(
                len(dezenas_set & set(s["dezenas"])) <= overlap_limite
                for s in selecionados
            ):
                selecionados.append(item)
        overlap_limite += 1

    # Sobreposição média da carteira final (quanto menor, maior a cobertura)
    overlaps = [
        len(set(a["dezenas"]) & set(b["dezenas"]))
        for i, a in enumerate(selecionados)
        for b in selecionados[i + 1:]
    ]
    sobreposicao_media = round(mean(overlaps), 2) if overlaps else None

    return {
        "jogos": selecionados,
        "pool_gerado": len(pool),
        "tentativas": attempts,
        "descartados_filtro": descartados_filtro,
        "sobreposicao_media": sobreposicao_media,
    }
