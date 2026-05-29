from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS sorteios (
    concurso INTEGER PRIMARY KEY,
    data_sorteio TEXT,
    dezenas_raw TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estatisticas_sorteio (
    concurso INTEGER PRIMARY KEY,
    soma INTEGER NOT NULL,
    qtd_pares INTEGER NOT NULL,
    qtd_impares INTEGER NOT NULL,
    qtd_primos INTEGER NOT NULL,
    qtd_fibonacci INTEGER NOT NULL,
    qtd_multiplos_3 INTEGER NOT NULL,
    qtd_moldura INTEGER NOT NULL,
    FOREIGN KEY (concurso) REFERENCES sorteios(concurso) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sorteios_megasena (
    concurso INTEGER PRIMARY KEY,
    data_sorteio TEXT,
    dezenas_raw TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estatisticas_megasena (
    concurso INTEGER PRIMARY KEY,
    soma INTEGER NOT NULL,
    qtd_pares INTEGER NOT NULL,
    qtd_impares INTEGER NOT NULL,
    qtd_primos INTEGER NOT NULL,
    qtd_fibonacci INTEGER NOT NULL,
    q1_count INTEGER NOT NULL,
    q2_count INTEGER NOT NULL,
    q3_count INTEGER NOT NULL,
    q4_count INTEGER NOT NULL,
    FOREIGN KEY (concurso) REFERENCES sorteios_megasena(concurso) ON DELETE CASCADE
);
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DB_SCHEMA)
    conn.commit()


def _get_table_names(lottery_type: str) -> tuple[str, str]:
    if lottery_type == "megasena":
        return "sorteios_megasena", "estatisticas_megasena"
    return "sorteios", "estatisticas_sorteio"


def count_draws(conn: sqlite3.Connection, lottery_type: str = "lotofacil") -> int:
    t_sorteios, _ = _get_table_names(lottery_type)
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {t_sorteios}").fetchone()
    return int(row["total"]) if row else 0


def upsert_draw(
    conn: sqlite3.Connection,
    lottery_type: str,
    concurso: int,
    data_sorteio: str,
    dezenas: list[int]
) -> None:
    t_sorteios, _ = _get_table_names(lottery_type)
    conn.execute(
        f"""
        INSERT INTO {t_sorteios} (concurso, data_sorteio, dezenas_raw)
        VALUES (?, ?, ?)
        ON CONFLICT(concurso) DO UPDATE SET
            data_sorteio=excluded.data_sorteio,
            dezenas_raw=excluded.dezenas_raw
        """,
        (concurso, data_sorteio, json.dumps(sorted(dezenas), ensure_ascii=False)),
    )


def upsert_stats(
    conn: sqlite3.Connection,
    lottery_type: str,
    concurso: int,
    stats: dict[str, int]
) -> None:
    _, t_stats = _get_table_names(lottery_type)
    if lottery_type == "megasena":
        conn.execute(
            f"""
            INSERT INTO {t_stats} (
                concurso,
                soma,
                qtd_pares,
                qtd_impares,
                qtd_primos,
                qtd_fibonacci,
                q1_count,
                q2_count,
                q3_count,
                q4_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concurso) DO UPDATE SET
                soma=excluded.soma,
                qtd_pares=excluded.qtd_pares,
                qtd_impares=excluded.qtd_impares,
                qtd_primos=excluded.qtd_primos,
                qtd_fibonacci=excluded.qtd_fibonacci,
                q1_count=excluded.q1_count,
                q2_count=excluded.q2_count,
                q3_count=excluded.q3_count,
                q4_count=excluded.q4_count
            """,
            (
                concurso,
                stats["soma"],
                stats["qtd_pares"],
                stats["qtd_impares"],
                stats["qtd_primos"],
                stats["qtd_fibonacci"],
                stats["q1_count"],
                stats["q2_count"],
                stats["q3_count"],
                stats["q4_count"],
            ),
        )
    else:
        conn.execute(
            f"""
            INSERT INTO {t_stats} (
                concurso,
                soma,
                qtd_pares,
                qtd_impares,
                qtd_primos,
                qtd_fibonacci,
                qtd_multiplos_3,
                qtd_moldura
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concurso) DO UPDATE SET
                soma=excluded.soma,
                qtd_pares=excluded.qtd_pares,
                qtd_impares=excluded.qtd_impares,
                qtd_primos=excluded.qtd_primos,
                qtd_fibonacci=excluded.qtd_fibonacci,
                qtd_multiplos_3=excluded.qtd_multiplos_3,
                qtd_moldura=excluded.qtd_moldura
            """,
            (
                concurso,
                stats["soma"],
                stats["qtd_pares"],
                stats["qtd_impares"],
                stats["qtd_primos"],
                stats["qtd_fibonacci"],
                stats["qtd_multiplos_3"],
                stats["qtd_moldura"],
            ),
        )


def get_last_concurso(conn: sqlite3.Connection, lottery_type: str = "lotofacil") -> int | None:
    t_sorteios, _ = _get_table_names(lottery_type)
    row = conn.execute(f"SELECT MAX(concurso) AS ultimo FROM {t_sorteios}").fetchone()
    if not row or row["ultimo"] is None:
        return None
    return int(row["ultimo"])


def get_draw_by_concurso(
    conn: sqlite3.Connection,
    lottery_type: str,
    concurso: int
) -> dict[str, Any] | None:
    t_sorteios, _ = _get_table_names(lottery_type)
    row = conn.execute(
        f"SELECT concurso, data_sorteio, dezenas_raw FROM {t_sorteios} WHERE concurso = ?",
        (concurso,),
    ).fetchone()
    if not row:
        return None
    return {
        "concurso": int(row["concurso"]),
        "data_sorteio": row["data_sorteio"],
        "dezenas": json.loads(row["dezenas_raw"]),
    }


def get_all_draws(conn: sqlite3.Connection, lottery_type: str = "lotofacil") -> list[dict[str, Any]]:
    t_sorteios, _ = _get_table_names(lottery_type)
    rows = conn.execute(
        f"SELECT concurso, data_sorteio, dezenas_raw FROM {t_sorteios} ORDER BY concurso ASC"
    ).fetchall()
    return [
        {
            "concurso": int(row["concurso"]),
            "data_sorteio": row["data_sorteio"],
            "dezenas": json.loads(row["dezenas_raw"]),
        }
        for row in rows
    ]


def get_recent_draws(conn: sqlite3.Connection, lottery_type: str, window: int) -> list[dict[str, Any]]:
    t_sorteios, _ = _get_table_names(lottery_type)
    rows = conn.execute(
        f"""
        SELECT concurso, data_sorteio, dezenas_raw
        FROM {t_sorteios}
        ORDER BY concurso DESC
        LIMIT ?
        """,
        (window,),
    ).fetchall()
    data = [
        {
            "concurso": int(row["concurso"]),
            "data_sorteio": row["data_sorteio"],
            "dezenas": json.loads(row["dezenas_raw"]),
        }
        for row in rows
    ]
    data.reverse()
    return data


def get_recent_stats(conn: sqlite3.Connection, lottery_type: str, window: int) -> list[dict[str, Any]]:
    _, t_stats = _get_table_names(lottery_type)
    if lottery_type == "megasena":
        rows = conn.execute(
            f"""
            SELECT
                concurso,
                soma,
                qtd_pares,
                qtd_impares,
                qtd_primos,
                qtd_fibonacci,
                q1_count,
                q2_count,
                q3_count,
                q4_count
            FROM {t_stats}
            ORDER BY concurso DESC
            LIMIT ?
            """,
            (window,),
        ).fetchall()
    else:
        rows = conn.execute(
            f"""
            SELECT
                concurso,
                soma,
                qtd_pares,
                qtd_impares,
                qtd_primos,
                qtd_fibonacci,
                qtd_multiplos_3,
                qtd_moldura
            FROM {t_stats}
            ORDER BY concurso DESC
            LIMIT ?
            """,
            (window,),
        ).fetchall()
    
    data = [dict(row) for row in rows]
    data.reverse()
    return data
