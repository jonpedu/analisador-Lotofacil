from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from src.megasena.analyzer import FIBONACCI_MEGA, PRIMOS_MEGA, get_quadrant

Validator = Callable[[list[int], "FilterConfig"], bool]


@dataclass
class FilterConfig:
    even_min: int
    even_max: int
    sum_min: int
    sum_max: int
    prime_min: int
    prime_max: int
    fibonacci_min: int
    fibonacci_max: int
    q_min: int
    q_max: int


def default_filter_config() -> FilterConfig:
    return FilterConfig(
        even_min=2,
        even_max=4,
        sum_min=120,
        sum_max=240,
        prime_min=0,
        prime_max=3,
        fibonacci_min=0,
        fibonacci_max=2,
        q_min=0,
        q_max=3,
    )


def validate_even_odd(ticket: list[int], cfg: FilterConfig) -> bool:
    pairs = sum(1 for n in ticket if n % 2 == 0)
    return cfg.even_min <= pairs <= cfg.even_max


def validate_sum(ticket: list[int], cfg: FilterConfig) -> bool:
    total = sum(ticket)
    return cfg.sum_min <= total <= cfg.sum_max


def validate_primes(ticket: list[int], cfg: FilterConfig) -> bool:
    qty = sum(1 for n in ticket if n in PRIMOS_MEGA)
    return cfg.prime_min <= qty <= cfg.prime_max


def validate_fibonacci(ticket: list[int], cfg: FilterConfig) -> bool:
    qty = sum(1 for n in ticket if n in FIBONACCI_MEGA)
    return cfg.fibonacci_min <= qty <= cfg.fibonacci_max


def validate_quadrants(ticket: list[int], cfg: FilterConfig) -> bool:
    counts = [0, 0, 0, 0]
    for n in ticket:
        q = get_quadrant(n)
        counts[q - 1] += 1
    # Verifica se nenhum quadrante excede o limite máximo estabelecido
    return all(cfg.q_min <= c <= cfg.q_max for c in counts)


class TicketPipeline:
    def __init__(self) -> None:
        self.validators: list[Validator] = [
            validate_even_odd,
            validate_sum,
            validate_primes,
            validate_fibonacci,
            validate_quadrants,
        ]

    def validate(self, ticket: list[int], cfg: FilterConfig) -> bool:
        return all(validator(ticket, cfg) for validator in self.validators)


def generate_filtered_games(
    cfg: FilterConfig,
    amount: int,
    max_attempts: int,
    hot_numbers: list[int] = None,
    cold_numbers: list[int] = None
) -> list[list[int]]:
    """
    Gerador Inteligente Ponderado da Mega-Sena.
    Baseia-se em balanceamento de quadrantes e probabilidade estatística.
    Evita jogos concentrados e distribui as dezenas de forma ótima na cartela.
    """
    pipeline = TicketPipeline()
    approved: list[list[int]] = []
    attempts = 0

    # Pool de números com pesos estatísticos se disponíveis
    numbers_pool = list(range(1, 61))
    weights = [1.0] * 60

    if hot_numbers:
        for num in hot_numbers:
            if 1 <= num <= 60:
                weights[num - 1] = 1.8  # Dá mais peso para as quentes

    if cold_numbers:
        for num in cold_numbers:
            if 1 <= num <= 60:
                weights[num - 1] = 0.6  # Reduz a frequência mas não elimina as frias

    while len(approved) < amount and attempts < max_attempts:
        attempts += 1
        
        # Constrói o jogo escolhendo elementos baseados no peso
        game = set()
        # Tenta selecionar 6 dezenas mantendo regras básicas de quadrantes
        # Para velocidade e eficiência, fazemos escolhas com pesos e depois ordenamos
        picked = random.choices(numbers_pool, weights=weights, k=12) # Amostra maior
        
        # Remove duplicados e mantém uma distribuição equilibrada de quadrantes
        quadrant_counts = [0, 0, 0, 0]
        selected_numbers = []
        
        for num in picked:
            if len(selected_numbers) == 6:
                break
            if num in game:
                continue
            
            q = get_quadrant(num)
            if quadrant_counts[q - 1] < cfg.q_max:
                game.add(num)
                selected_numbers.append(num)
                quadrant_counts[q - 1] += 1

        # Se a seleção por quadrantes falhar em completar 6 números, completa aleatoriamente de quadrantes vazios
        if len(selected_numbers) < 6:
            remaining_numbers = list(set(range(1, 61)) - game)
            random.shuffle(remaining_numbers)
            for num in remaining_numbers:
                if len(selected_numbers) == 6:
                    break
                q = get_quadrant(num)
                if quadrant_counts[q - 1] < cfg.q_max:
                    game.add(num)
                    selected_numbers.append(num)
                    quadrant_counts[q - 1] += 1

        final_game = sorted(selected_numbers)

        if len(final_game) == 6 and pipeline.validate(final_game, cfg):
            approved.append(final_game)

    return approved
