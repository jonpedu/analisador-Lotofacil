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
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DB_SCHEMA)
    conn.commit()


def count_draws(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS total FROM sorteios").fetchone()
    return int(row["total"]) if row else 0


def upsert_draw(conn: sqlite3.Connection, concurso: int, data_sorteio: str, dezenas: list[int]) -> None:
    conn.execute(
        """
        INSERT INTO sorteios (concurso, data_sorteio, dezenas_raw)
        VALUES (?, ?, ?)
        ON CONFLICT(concurso) DO UPDATE SET
            data_sorteio=excluded.data_sorteio,
            dezenas_raw=excluded.dezenas_raw
        """,
        (concurso, data_sorteio, json.dumps(sorted(dezenas), ensure_ascii=False)),
    )


def upsert_stats(conn: sqlite3.Connection, concurso: int, stats: dict[str, int]) -> None:
    conn.execute(
        """
        INSERT INTO estatisticas_sorteio (
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


def get_last_concurso(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT MAX(concurso) AS ultimo FROM sorteios").fetchone()
    if not row or row["ultimo"] is None:
        return None
    return int(row["ultimo"])


def get_draw_by_concurso(conn: sqlite3.Connection, concurso: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT concurso, data_sorteio, dezenas_raw FROM sorteios WHERE concurso = ?",
        (concurso,),
    ).fetchone()
    if not row:
        return None
    return {
        "concurso": int(row["concurso"]),
        "data_sorteio": row["data_sorteio"],
        "dezenas": json.loads(row["dezenas_raw"]),
    }


def get_all_draws(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT concurso, data_sorteio, dezenas_raw FROM sorteios ORDER BY concurso ASC"
    ).fetchall()
    return [
        {
            "concurso": int(row["concurso"]),
            "data_sorteio": row["data_sorteio"],
            "dezenas": json.loads(row["dezenas_raw"]),
        }
        for row in rows
    ]


def get_recent_draws(conn: sqlite3.Connection, window: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT concurso, data_sorteio, dezenas_raw
        FROM sorteios
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


def get_recent_stats(conn: sqlite3.Connection, window: int) -> list[dict[str, int]]:
    rows = conn.execute(
        """
        SELECT
            concurso,
            soma,
            qtd_pares,
            qtd_impares,
            qtd_primos,
            qtd_fibonacci,
            qtd_multiplos_3,
            qtd_moldura
        FROM estatisticas_sorteio
        ORDER BY concurso DESC
        LIMIT ?
        """,
        (window,),
    ).fetchall()
    data = [dict(row) for row in rows]
    data.reverse()
    return data
