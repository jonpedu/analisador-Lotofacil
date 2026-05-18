from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_dezenas(values: list[Any]) -> list[int]:
    dezenas = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25:
            dezenas.append(number)

    dezenas = sorted(set(dezenas))
    if len(dezenas) != 15:
        return []
    return dezenas


def read_initial_excel(excel_path: Path) -> list[dict[str, Any]]:
    if not excel_path.exists():
        raise FileNotFoundError(f"Arquivo Excel nao encontrado: {excel_path}")

    df = pd.read_excel(excel_path)
    columns_lower = {col: str(col).strip().lower() for col in df.columns}

    concurso_col = None
    dezenas_cols: list[str] = []

    for col, lower_name in columns_lower.items():
        if concurso_col is None and "concurso" in lower_name:
            concurso_col = col
        if "dezena" in lower_name or "bola" in lower_name:
            dezenas_cols.append(col)

    result: list[dict[str, Any]] = []

    if concurso_col is not None and len(dezenas_cols) >= 15:
        dezenas_cols = dezenas_cols[:15]
        for _, row in df.iterrows():
            try:
                concurso = int(row[concurso_col])
            except (TypeError, ValueError):
                continue

            dezenas = _normalize_dezenas([row[col] for col in dezenas_cols])
            if len(dezenas) == 15:
                result.append(
                    {
                        "concurso": concurso,
                        "data_sorteio": str(row.get("Data Sorteio", "")).strip(),
                        "dezenas": dezenas,
                    }
                )
    else:
        # Fallback para planilhas com colunas fora do padrao.
        numeric_df = df.apply(pd.to_numeric, errors="coerce")
        for _, row in numeric_df.iterrows():
            numeric_values = [int(v) for v in row.dropna().tolist()]
            if len(numeric_values) < 16:
                continue
            concurso = int(numeric_values[0])
            dezenas = _normalize_dezenas(numeric_values[1:])
            if len(dezenas) == 15:
                result.append({"concurso": concurso, "data_sorteio": "", "dezenas": dezenas})

    result.sort(key=lambda item: item["concurso"])
    return result
