"""AttemptRegistry (RF-24): log auditável de TODA tentativa desde o primeiro
backtest. É o insumo do Deflated Sharpe Ratio (Parte 8) — sem a contagem real de
tentativas, o DSR é incalculável e o processo vira data snooping inauditável.

Armazenamento local em SQLite (decisão D-03: mínimo, sem MLflow).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    phase         TEXT NOT NULL,
    name          TEXT NOT NULL,
    config_hash   TEXT NOT NULL,
    params_json   TEXT NOT NULL,
    result_json   TEXT NOT NULL,
    notes         TEXT NOT NULL DEFAULT ''
);
"""


@dataclass(frozen=True)
class Attempt:
    id: int
    timestamp_utc: str
    phase: str
    name: str
    config_hash: str
    params: dict
    result: dict
    notes: str


class AttemptRegistry:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con, con:
            con.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def log(self, phase: str, name: str, config_hash: str,
            params: dict, result: dict, notes: str = "") -> int:
        """Registra uma tentativa e devolve seu id. Timestamp sempre em UTC."""
        ts = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as con, con:
            cur = con.execute(
                "INSERT INTO attempts "
                "(timestamp_utc, phase, name, config_hash, params_json, result_json, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ts, phase, name, config_hash,
                    json.dumps(params, sort_keys=True, ensure_ascii=False),
                    json.dumps(result, sort_keys=True, ensure_ascii=False),
                    notes,
                ),
            )
            return cur.lastrowid

    def get(self, attempt_id: int) -> Attempt | None:
        with closing(self._connect()) as con:
            row = con.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
        return self._row_to_attempt(row) if row else None

    def all(self) -> list[Attempt]:
        with closing(self._connect()) as con:
            rows = con.execute("SELECT * FROM attempts ORDER BY id").fetchall()
        return [self._row_to_attempt(r) for r in rows]

    def count(self) -> int:
        """Número real de tentativas — entra direto no cálculo do DSR."""
        with closing(self._connect()) as con:
            return con.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]

    @staticmethod
    def _row_to_attempt(row: sqlite3.Row) -> Attempt:
        return Attempt(
            id=row["id"],
            timestamp_utc=row["timestamp_utc"],
            phase=row["phase"],
            name=row["name"],
            config_hash=row["config_hash"],
            params=json.loads(row["params_json"]),
            result=json.loads(row["result_json"]),
            notes=row["notes"],
        )
