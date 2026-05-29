from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _normalize_dezenas(values: list[Any], max_number: int, expected_count: int) -> list[int]:
    dezenas = []
    for value in values:
        try:
            # Converte float para int (ex: 2.0 -> 2)
            number = int(float(value))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= max_number:
            dezenas.append(number)

    dezenas = sorted(set(dezenas))
    if len(dezenas) != expected_count:
        return []
    return dezenas


def read_initial_excel(excel_path: Path, lottery_type: str = "lotofacil") -> list[dict[str, Any]]:
    if not excel_path.exists():
        raise FileNotFoundError(f"Arquivo Excel nao encontrado: {excel_path}")

    # Configuração com base na loteria
    if lottery_type == "megasena":
        max_number = 60
        expected_count = 6
    else:
        max_number = 25
        expected_count = 15

    df = pd.read_excel(excel_path)
    columns_lower = {col: str(col).strip().lower() for col in df.columns}

    concurso_col = None
    data_col = None
    dezenas_cols: list[str] = []

    # Mapeamento inteligente de colunas
    for col, lower_name in columns_lower.items():
        if concurso_col is None and "concurso" in lower_name:
            concurso_col = col
        if data_col is None and ("data" in lower_name or "sorteio" in lower_name) and "ganhadores" not in lower_name and "rateio" not in lower_name:
            data_col = col
        if "dezena" in lower_name or "bola" in lower_name:
            dezenas_cols.append(col)

    # Caso a coluna de data não seja encontrada de forma específica
    if data_col is None:
        for col, lower_name in columns_lower.items():
            if "data" in lower_name:
                data_col = col
                break

    result: list[dict[str, Any]] = []

    # Ordenação das colunas de dezena para garantir Bola1, Bola2...
    # Ex: Bola10 não deve vir antes de Bola2 se ordenado puramente alfabeticamente, por isso usamos ordenação inteligente.
    def extract_num(col_name: str) -> int:
        import re
        nums = re.findall(r"\d+", col_name)
        return int(nums[0]) if nums else 0

    dezenas_cols = sorted(dezenas_cols, key=extract_num)

    if concurso_col is not None and len(dezenas_cols) >= expected_count:
        dezenas_cols = dezenas_cols[:expected_count]
        for _, row in df.iterrows():
            try:
                concurso = int(float(row[concurso_col]))
            except (TypeError, ValueError):
                continue

            dezenas = _normalize_dezenas([row[col] for col in dezenas_cols], max_number, expected_count)
            if len(dezenas) == expected_count:
                data_val = ""
                if data_col is not None:
                    data_val = str(row[data_col]).strip()
                    # Limpa data em formato datetime (.0 ou timestamp)
                    if " " in data_val:
                        data_val = data_val.split(" ")[0]
                result.append(
                    {
                        "concurso": concurso,
                        "data_sorteio": data_val,
                        "dezenas": dezenas,
                    }
                )
    else:
        # Fallback para planilhas com colunas totalmente fora do padrao (leitura posicional)
        numeric_df = df.apply(pd.to_numeric, errors="coerce")
        for _, row in numeric_df.iterrows():
            numeric_values = [int(v) for v in row.dropna().tolist() if v.is_integer()]
            if len(numeric_values) < (expected_count + 1):
                continue
            concurso = int(numeric_values[0])
            dezenas = _normalize_dezenas(numeric_values[1:], max_number, expected_count)
            if len(dezenas) == expected_count:
                result.append({"concurso": concurso, "data_sorteio": "", "dezenas": dezenas})

    result.sort(key=lambda item: item["concurso"])
    return result
