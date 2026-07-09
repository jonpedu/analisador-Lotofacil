from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from src.lotofacil.analyzer import FIBONACCI, MOLDURA, PRIMOS

Validator = Callable[[list[int], "FilterConfig", list[int]], bool]


@dataclass
class FilterConfig:
    allowed_even_odd_pairs: list[list[int]]
    sum_min: int
    sum_max: int
    repeat_min: int
    repeat_max: int
    prime_min: int
    prime_max: int
    fibonacci_min: int
    fibonacci_max: int
    multiple3_min: int
    multiple3_max: int
    moldura_min: int
    moldura_max: int
    row_min: int
    row_max: int
    col_min: int
    col_max: int
    max_consecutive: int


def default_filter_config() -> FilterConfig:
    return FilterConfig(
        allowed_even_odd_pairs=[[7, 8], [8, 7], [9, 6]],
        sum_min=180,
        sum_max=220,
        repeat_min=8,
        repeat_max=10,
        prime_min=4,
        prime_max=6,
        fibonacci_min=3,
        fibonacci_max=5,
        multiple3_min=4,
        multiple3_max=6,
        moldura_min=9,
        moldura_max=11,
        row_min=1,
        row_max=4,
        col_min=1,
        col_max=4,
        max_consecutive=4,
    )


def _row_col_counts(ticket: list[int]) -> tuple[list[int], list[int]]:
    rows = [0, 0, 0, 0, 0]
    cols = [0, 0, 0, 0, 0]

    for n in ticket:
        row = (n - 1) // 5
        col = (n - 1) % 5
        rows[row] += 1
        cols[col] += 1

    return rows, cols


def _max_consecutive_seq(ticket: list[int]) -> int:
    if not ticket:
        return 0

    max_seq = 1
    current = 1
    for idx in range(1, len(ticket)):
        if ticket[idx] == ticket[idx - 1] + 1:
            current += 1
            max_seq = max(max_seq, current)
        else:
            current = 1

    return max_seq


def validate_even_odd(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    pairs = sum(1 for n in ticket if n % 2 == 0)
    odds = 15 - pairs
    return [pairs, odds] in cfg.allowed_even_odd_pairs


def validate_sum(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    total = sum(ticket)
    return cfg.sum_min <= total <= cfg.sum_max


def validate_repeats(ticket: list[int], cfg: FilterConfig, previous: list[int]) -> bool:
    repeats = len(set(ticket).intersection(previous))
    return cfg.repeat_min <= repeats <= cfg.repeat_max


def validate_primes(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    qty = sum(1 for n in ticket if n in PRIMOS)
    return cfg.prime_min <= qty <= cfg.prime_max


def validate_fibonacci(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    qty = sum(1 for n in ticket if n in FIBONACCI)
    return cfg.fibonacci_min <= qty <= cfg.fibonacci_max


def validate_multiples_of_3(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    qty = sum(1 for n in ticket if n % 3 == 0)
    return cfg.multiple3_min <= qty <= cfg.multiple3_max


def validate_moldura(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    qty = sum(1 for n in ticket if n in MOLDURA)
    return cfg.moldura_min <= qty <= cfg.moldura_max


def validate_rows_columns(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    rows, cols = _row_col_counts(ticket)
    rows_ok = all(cfg.row_min <= n <= cfg.row_max for n in rows)
    cols_ok = all(cfg.col_min <= n <= cfg.col_max for n in cols)
    return rows_ok and cols_ok


def validate_consecutive(ticket: list[int], cfg: FilterConfig, _: list[int]) -> bool:
    return _max_consecutive_seq(ticket) <= cfg.max_consecutive


class TicketPipeline:
    def __init__(self) -> None:
        self.validators: list[Validator] = [
            validate_even_odd,
            validate_sum,
            validate_repeats,
            validate_primes,
            validate_fibonacci,
            validate_multiples_of_3,
            validate_moldura,
            validate_rows_columns,
            validate_consecutive,
        ]

    def validate(self, ticket: list[int], cfg: FilterConfig, previous: list[int]) -> bool:
        return all(validator(ticket, cfg, previous) for validator in self.validators)


def build_structured_candidate(
    cfg: FilterConfig,
    previous_set: set[int],
    complementary: list[int],
    cycle_absent_set: set[int],
    rng: random.Random | None = None,
) -> list[int]:
    """
    Constrói um único candidato estruturado:
      - Repete R dezenas do concurso anterior (R sorteado dentro dos limites do filtro).
      - Insere preferencialmente as dezenas ausentes do ciclo.
      - Completa com dezenas do conjunto complementar.
    """
    rnd = rng if rng is not None else random

    # Decide quantas dezenas repetir do concurso anterior
    r_target = rnd.randint(cfg.repeat_min, cfg.repeat_max)
    non_r_target = 15 - r_target

    if r_target > 15 or non_r_target > 10:
        # Fallback seguro caso as configs estejam descalibradas
        r_target = 9
        non_r_target = 6

    # Divide as dezenas ausentes do ciclo entre as que pertencem ao concurso anterior e complementar
    cycle_in_prev = list(previous_set.intersection(cycle_absent_set))
    cycle_in_comp = list(set(complementary).intersection(cycle_absent_set))

    # 1. Escolhe dezenas do concurso anterior
    prev_picked = []
    # Garante algumas do ciclo se disponíveis
    if cycle_in_prev:
        num_to_pick = min(len(cycle_in_prev), rnd.randint(1, max(1, len(cycle_in_prev) // 2)))
        prev_picked = rnd.sample(cycle_in_prev, num_to_pick)

    remaining_prev = list(previous_set - set(prev_picked))
    needed_prev = r_target - len(prev_picked)
    if needed_prev > 0 and len(remaining_prev) >= needed_prev:
        prev_picked.extend(rnd.sample(remaining_prev, needed_prev))
    elif needed_prev > 0:
        # Fallback
        prev_picked.extend(remaining_prev)

    # 2. Escolhe dezenas do complementar
    comp_picked = []
    if cycle_in_comp:
        num_to_pick = min(len(cycle_in_comp), rnd.randint(1, len(cycle_in_comp)))
        comp_picked = rnd.sample(cycle_in_comp, num_to_pick)

    remaining_comp = list(set(complementary) - set(comp_picked))
    needed_comp = non_r_target - len(comp_picked)
    if needed_comp > 0 and len(remaining_comp) >= needed_comp:
        comp_picked.extend(rnd.sample(remaining_comp, needed_comp))
    elif needed_comp > 0:
        # Fallback
        comp_picked.extend(remaining_comp)

    return sorted(prev_picked + comp_picked)


def generate_filtered_games(
    cfg: FilterConfig,
    previous: list[int],
    amount: int,
    max_attempts: int,
    cycle_absent: list[int] = None
) -> list[list[int]]:
    """
    Gerador Inteligente Ponderado da Lotofácil.
    Em vez de força bruta aleatória pura, constrói candidatos estruturados
    (ver build_structured_candidate) e aprova o primeiro que passar nos filtros.
    """
    pipeline = TicketPipeline()
    approved: list[list[int]] = []
    attempts = 0

    if not previous or len(previous) != 15:
        # Fallback para sorteio puramente aleatório se não houver concurso anterior válido
        previous = list(range(1, 16))

    previous_set = set(previous)
    complementary = sorted(list(set(range(1, 26)) - previous_set)) # 10 dezenas que não saíram

    # Lista de dezenas ausentes do ciclo de prioridade
    cycle_absent_set = set(cycle_absent) if cycle_absent else set()

    while len(approved) < amount and attempts < max_attempts:
        attempts += 1
        game = build_structured_candidate(cfg, previous_set, complementary, cycle_absent_set)

        if len(game) == 15 and pipeline.validate(game, cfg, previous):
            approved.append(game)

    return approved
