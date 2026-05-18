from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from analyzer import FIBONACCI, MOLDURA, PRIMOS

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
        max_consecutive=6,
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


def generate_filtered_games(
    cfg: FilterConfig,
    previous: list[int],
    amount: int,
    max_attempts: int,
) -> list[list[int]]:
    pipeline = TicketPipeline()
    approved: list[list[int]] = []
    attempts = 0

    while len(approved) < amount and attempts < max_attempts:
        attempts += 1
        game = sorted(random.sample(range(1, 26), 15))
        if pipeline.validate(game, cfg, previous):
            approved.append(game)

    return approved
