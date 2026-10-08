"""Aquisição de ticks Dukascopy (RF-01) + escrita Parquet versionada por hash (R-09).

Formato .bi5 (por hora): LZMA de registros big-endian de 5 campos por tick:
  int32  ms_offset  (ms desde o início da hora do arquivo)
  int32  ask        (em pontos; dividir por point_value)
  int32  bid        (em pontos)
  float32 ask_volume
  float32 bid_volume
URL: .../datafeed/{SYMBOL}/{YYYY}/{MM-1:02}/{DD:02}/{HH:02}h_ticks.bi5
     (MÊS É 0-INDEXADO na Dukascopy — fonte clássica de bug.)

`fetch_hour` (rede) fica isolado e só roda após autorização de download.
Todo o resto é puro e testável offline.
"""
from __future__ import annotations

import hashlib
import lzma
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_EMPTY = pd.DataFrame({"timestamp": pd.to_datetime([], utc=True), "bid": [], "ask": []})

# pontos -> preço. Dukascopy: 1e5 na maioria FX; 1e3 em pares JPY e XAUUSD.
# CFDs (índices/commodity) usam o CÓDIGO do datafeed como chave e escala 1e3
# (confirmado por smoke 2026-07-25: preços batem níveis históricos reais).
# Calibrar/confirmar na Fase 0.2/0i com dado real antes de fechar o gate.
POINT_VALUE = {
    "EURUSD": 1e5, "GBPUSD": 1e5, "AUDUSD": 1e5, "USDCAD": 1e5,
    "USDJPY": 1e3, "XAUUSD": 1e3,
    "USA500IDXUSD": 1e3, "USATECHIDXUSD": 1e3, "DEUIDXEUR": 1e3, "LIGHTCMDUSD": 1e3,
}

_DTYPE = np.dtype([("ms", ">i4"), ("ask", ">i4"), ("bid", ">i4"),
                   ("av", ">f4"), ("bv", ">f4")])


def dukascopy_url(symbol: str, dt: datetime) -> str:
    return (f"https://datafeed.dukascopy.com/datafeed/{symbol}/"
            f"{dt.year:04d}/{dt.month - 1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5")


def bi5_decode(raw: bytes, symbol: str, hour_start: datetime) -> pd.DataFrame:
    """Decodifica um .bi5 (bytes) em DataFrame [timestamp(UTC), bid, ask]. Puro/offline.

    FORMAT_AUTO cobre o LZMA-alone da Dukascopy e o XZ usado nos testes.
    """
    if not raw:
        return _EMPTY.copy()
    data = lzma.decompress(raw)
    arr = np.frombuffer(data, dtype=_DTYPE)
    pv = POINT_VALUE[symbol]
    hs = pd.Timestamp(hour_start)
    if hs.tz is None:
        hs = hs.tz_localize("UTC")
    ts = hs + pd.to_timedelta(arr["ms"].astype("int64"), unit="ms")
    return pd.DataFrame({"timestamp": ts, "bid": arr["bid"] / pv, "ask": arr["ask"] / pv})


def fetch_hour(symbol: str, dt: datetime, *, timeout: int = 30) -> bytes:
    """Baixa um arquivo .bi5 (1 hora). REDE — só executa após autorização de download."""
    import urllib.request

    req = urllib.request.Request(
        dukascopy_url(symbol, dt), headers={"User-Agent": "forex-research/0.2"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (host fixo)
        return resp.read()


_DUKA_HOST = "datafeed.dukascopy.com"


def fetch_day_raw(symbol: str, day, *, timeout: int = 45, retries: int = 4) -> dict[int, bytes]:
    """Baixa as 24 horas de um dia REUTILIZANDO uma conexão TLS (keep-alive). REDE.

    Através do proxy de inspeção SSL desta rede o handshake custa ~9s; reusar a
    conexão troca 24 handshakes/dia por ~1 — sem isso o download é inviável aqui.
    Retorna {hora: raw_bytes} só das horas COM dado (404/vazio = ausente).
    Levanta RuntimeError se a rede falhar após retries (o dia inteiro é descartado
    a montante, nunca gravado pela metade).
    """
    import http.client

    conn: http.client.HTTPSConnection | None = None
    out: dict[int, bytes] = {}
    try:
        for h in range(24):
            path = (f"/datafeed/{symbol}/{day.year:04d}/{day.month - 1:02d}/"
                    f"{day.day:02d}/{h:02d}h_ticks.bi5")
            for attempt in range(retries):
                try:
                    if conn is None:
                        conn = http.client.HTTPSConnection(_DUKA_HOST, timeout=timeout)
                    conn.request("GET", path, headers={
                        "User-Agent": "forex-research/0.2", "Connection": "keep-alive"})
                    resp = conn.getresponse()
                    body = resp.read()  # sempre drenar p/ reusar a conexão
                    if resp.status == 404:
                        break  # hora legitimamente sem dado
                    if resp.status != 200:
                        raise OSError(f"HTTP {resp.status}")
                    if body:
                        out[h] = body
                    break
                except OSError as e:  # timeout, reset, handshake, etc.
                    if conn is not None:
                        conn.close()
                        conn = None
                    if attempt == retries - 1:
                        raise RuntimeError(f"falha de rede {symbol} {day} {h:02d}h: {e}") from e
                    import time as _t
                    _t.sleep(2 ** attempt)  # backoff 1,2,4s
    finally:
        if conn is not None:
            conn.close()
    return out


def write_parquet_versioned(df: pd.DataFrame, out_dir: str | Path, name: str) -> tuple[Path, str]:
    """Escreve Parquet e devolve (path, sha256 do arquivo) — snapshot versionado (R-09)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()
