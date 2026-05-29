from __future__ import annotations

from typing import Any
import requests


def _parse_api_draw(
    payload: dict[str, Any],
    concurso_fallback: int,
    lottery_type: str = "lotofacil"
) -> dict[str, Any] | None:
    concurso = payload.get("concurso") or payload.get("numero") or concurso_fallback
    dezenas = payload.get("dezenas") or payload.get("dezenasOrdemSorteio") or payload.get("listaDezenas")
    data_sorteio = payload.get("data") or payload.get("dataApuracao") or ""

    if not dezenas:
        return None

    try:
        concurso_int = int(concurso)
    except (TypeError, ValueError):
        return None

    if lottery_type == "megasena":
        max_number = 60
        expected_count = 6
    else:
        max_number = 25
        expected_count = 15

    dezenas_int: list[int] = []
    for value in dezenas:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= max_number:
            dezenas_int.append(number)

    dezenas_int = sorted(set(dezenas_int))
    if len(dezenas_int) != expected_count:
        return None

    return {
        "concurso": concurso_int,
        "data_sorteio": str(data_sorteio),
        "dezenas": dezenas_int,
    }


def fetch_draw_by_concurso(
    base_url: str,
    concurso: int,
    lottery_type: str = "lotofacil",
    timeout: int = 15
) -> dict[str, Any] | None:
    # Monta a URL dinamicamente conforme a loteria
    # A base_url geralmente termina com 'lotofacil' ou 'megasena'
    url = f"{base_url.rstrip('/')}/{concurso}"
    response = requests.get(url, timeout=timeout)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    payload = response.json()

    # Algumas APIs retornam uma lista com um único item.
    if isinstance(payload, list):
        if not payload:
            return None
        item = payload[0]
    else:
        item = payload

    if not isinstance(item, dict):
        return None

    return _parse_api_draw(item, concurso, lottery_type)
