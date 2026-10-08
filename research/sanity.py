"""Sanidade e normalização de ticks (RF-02): UTC/DST, gaps, spikes, quotes inválidos.

Opera sobre um DataFrame de ticks com colunas ['timestamp', 'bid', 'ask'].
Funções puras, testáveis sem download. A fonte de pesquisa (Dukascopy) já vem em
UTC; para dados do broker use `normalize_to_utc` com o tz do servidor (o horário
do servidor MT5 raramente é UTC — Parte 11).

Os thresholds NÃO são fixados aqui: são calibrados na Fase 0.2 com dados reais.
Este módulo entrega a lógica; a régua vem depois.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("timestamp", "bid", "ask")


def _check_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")


def normalize_to_utc(df: pd.DataFrame, source_tz: str = "UTC") -> pd.DataFrame:
    """'timestamp' -> UTC tz-aware, ordenado. DST tratado por `zoneinfo` no localize.

    Já tz-aware: apenas converte. Naive: localiza em `source_tz` (horários
    inexistentes/ambíguos de DST viram shift_forward / NaT para não inventar dado).
    """
    _check_columns(df)
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"])
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(source_tz, nonexistent="shift_forward", ambiguous="NaT")
    out["timestamp"] = ts.dt.tz_convert("UTC")
    return out.sort_values("timestamp").reset_index(drop=True)


def drop_invalid_quotes(df: pd.DataFrame) -> pd.DataFrame:
    """Remove ticks inválidos: preço não-positivo ou quote cruzado (bid > ask).

    Aplicar no CARREGAMENTO para features (Fase 1); os Parquet brutos ficam imutáveis
    (snapshot versionado). AUDUSD tinha ~0,015% de quotes cruzados no dataset Dukascopy.
    """
    _check_columns(df)
    mask = (df["bid"] > 0) & (df["ask"] > 0) & (df["bid"] <= df["ask"])
    return df[mask].reset_index(drop=True)


def detect_gaps(df: pd.DataFrame, max_gap: pd.Timedelta) -> pd.DataFrame:
    """Intervalos entre ticks consecutivos > max_gap (buracos de feed).

    Fins de semana são gaps esperados e devem ser filtrados a montante (por sessão).
    Retorna colunas start/end/duration.
    """
    _check_columns(df)
    ts = pd.to_datetime(df["timestamp"]).sort_values().reset_index(drop=True)
    delta = ts.diff()
    idx = np.where((delta > max_gap).to_numpy())[0]  # delta[0] é NaT -> nunca entra
    return pd.DataFrame(
        {"start": ts.iloc[idx - 1].to_numpy(),
         "end": ts.iloc[idx].to_numpy(),
         "duration": delta.iloc[idx].to_numpy()}
    )


def detect_spikes(df: pd.DataFrame, k: float = 8.0, window: int = 50) -> np.ndarray:
    """Índices de spikes de tick isolados: salto grande seguido de reversão imediata.

    Escala robusta pela mediana móvel de |retorno| (MAD-like). ponytail: heurística;
    teto = falsos positivos em vol real alta -> recalibrar k/window com dados reais.
    """
    _check_columns(df)
    mid = (df["bid"].to_numpy() + df["ask"].to_numpy()) / 2.0
    ret = pd.Series(mid).diff()
    scale = ret.abs().rolling(window, min_periods=max(window // 2, 2)).median()
    thr = k * scale
    jump = ret.abs() > thr
    reverts = (ret * ret.shift(-1) < 0) & (ret.shift(-1).abs() > thr)
    spike = (jump & reverts).fillna(False).to_numpy()
    return np.where(spike)[0]


@dataclass(frozen=True)
class QualityReport:
    n_ticks: int
    start: str | None
    end: str | None
    n_gaps: int
    n_spikes: int
    n_crossed: int        # bid > ask
    n_nonpositive: int    # bid<=0 ou ask<=0
    n_dup_timestamps: int

    def as_dict(self) -> dict:
        return asdict(self)


def quality_report(df: pd.DataFrame, max_gap: pd.Timedelta,
                   spike_k: float = 8.0) -> QualityReport:
    """Relatório de qualidade auditável (insumo do gate da Fase 0.2)."""
    _check_columns(df)
    if len(df) == 0:
        return QualityReport(0, None, None, 0, 0, 0, 0, 0)
    ts = pd.to_datetime(df["timestamp"])
    bid, ask = df["bid"].to_numpy(), df["ask"].to_numpy()
    return QualityReport(
        n_ticks=len(df),
        start=str(ts.min()),
        end=str(ts.max()),
        n_gaps=len(detect_gaps(df, max_gap)),
        n_spikes=len(detect_spikes(df, k=spike_k)),
        n_crossed=int((bid > ask).sum()),
        n_nonpositive=int(((bid <= 0) | (ask <= 0)).sum()),
        n_dup_timestamps=int(ts.duplicated().sum()),
    )
