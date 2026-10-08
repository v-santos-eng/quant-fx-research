"""Ingestor F0 — histórico diário de futuros via API do Interactive Brokers (ib_async).

PRÉ-REQUISITO (ação do usuário, como o MT5): TWS ou IB Gateway ABERTO e LOGADO, com a API
habilitada (Configure > API > Settings > Enable ActiveX and Socket Clients; 127.0.0.1 em Trusted
IPs). Portas padrão: 7497 (TWS paper), 7496 (TWS live), 4002/4001 (Gateway paper/live).

Puxa a série CONTÍNUA do contrato PADRÃO/MINI (história longa — ES desde 1997 etc.), não do micro
(que só existe desde ~2019). A série de preço é a mesma; a execução depois usa o micro equivalente
(MES↔ES, MGC↔GC, ÷10 no valor do contrato). Isto é o F0 (contínuo do IB p/ 1ª passada); a F1
constrói/valida o roll próprio a partir dos contratos individuais.

Uso:
  python -m research.ingest_ib_futures --port 7497 --years 20
  python -m research.ingest_ib_futures --port 4002 --symbols ES NQ GC CL
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

# universo-alvo: símbolo de DADOS (padrão/mini) -> (exchange, moeda, micro p/ execução, setor)
UNIVERSE = {
    "ES":  ("CME", "USD", "MES", "index"),    "NQ": ("CME", "USD", "MNQ", "index"),
    "YM":  ("CBOT", "USD", "MYM", "index"),   "RTY": ("CME", "USD", "M2K", "index"),
    "GC":  ("COMEX", "USD", "MGC", "metal"),  "SI": ("COMEX", "USD", "SIL", "metal"),
    "HG":  ("COMEX", "USD", "MHG", "metal"),
    "CL":  ("NYMEX", "USD", "MCL", "energy"), "NG": ("NYMEX", "USD", "MNG", "energy"),
    "6E":  ("CME", "USD", "M6E", "fx"),       "6A": ("CME", "USD", "M6A", "fx"),
    "6B":  ("CME", "USD", "M6B", "fx"),       "6J": ("CME", "USD", "MJY", "fx"),
    "ZT":  ("CBOT", "USD", "-", "rates"),     "ZF": ("CBOT", "USD", "-", "rates"),
    "ZN":  ("CBOT", "USD", "-", "rates"),     "ZB": ("CBOT", "USD", "-", "rates"),
    "ZC":  ("CBOT", "USD", "-", "ag"),        "ZS": ("CBOT", "USD", "-", "ag"),
    "ZW":  ("CBOT", "USD", "-", "ag"),
}
OUT = Path("data/futures")


def _norm_df(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame cru do IB (date/open/high/low/close/volume) -> schema padrão. PURO/testável."""
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    ts = pd.to_datetime(df["date"])
    ts = ts.dt.tz_localize("UTC") if ts.dt.tz is None else ts.dt.tz_convert("UTC")
    out = pd.DataFrame({"timestamp": ts, "open": df["open"], "high": df["high"],
                        "low": df["low"], "close": df["close"],
                        "volume": df["volume"] if "volume" in df else 0})
    return out.dropna(subset=["close"]).reset_index(drop=True)


def _normalize(bars) -> pd.DataFrame:
    """Barras do IB -> schema padrão [timestamp(UTC), open, high, low, close, volume]."""
    from ib_async import util
    return _norm_df(util.df(bars))


def fetch_symbol(ib, symbol: str, exchange: str, currency: str, years: int):
    """Série contínua diária de um futuro. Retorna (status, n_bars, DataFrame)."""
    from ib_async import ContFut
    c = ContFut(symbol, exchange, currency)
    try:
        q = ib.qualifyContracts(c)
    except Exception as e:  # noqa: BLE001
        return f"qualify_erro:{e}", 0, None
    if not q:
        return "nao_qualificou", 0, None
    for what in ("TRADES", "MIDPOINT"):     # alguns contínuos não têm TRADES
        try:
            bars = ib.reqHistoricalData(c, endDateTime="", durationStr=f"{years} Y",
                                        barSizeSetting="1 day", whatToShow=what,
                                        useRTH=True, formatDate=1, timeout=120)
        except Exception as e:  # noqa: BLE001
            return f"hist_erro:{e}", 0, None
        df = _normalize(bars)
        if len(df):
            return "ok", len(df), df
    return "sem_dado", 0, None


def run(port: int, years: int, symbols: list[str], host: str = "127.0.0.1",
        client_id: int = 17) -> int:
    from ib_async import IB
    ib = IB()
    print(f"Conectando ao IB em {host}:{port} (clientId={client_id}) ...", flush=True)
    try:
        ib.connect(host, port, clientId=client_id, timeout=15)
    except Exception as e:  # noqa: BLE001
        print(f"FALHA ao conectar: {e}\n"
              f"-> Abra o TWS/IB Gateway, logue, e habilite a API (porta {port}).", flush=True)
        return 2
    print("Conectado.", flush=True)
    ok = err = 0
    for sym in symbols:
        exchange, currency, micro, sector = UNIVERSE[sym]
        out_path = OUT / sym / "daily.parquet"
        if out_path.exists():
            print(f"  {sym:4} skip (já existe)", flush=True); ok += 1; continue
        status, n, df = fetch_symbol(ib, sym, exchange, currency, years)
        if status == "ok":
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out_path, index=False)
            print(f"  {sym:4} OK  {n:>5} barras  {df['timestamp'].min().date()}"
                  f"..{df['timestamp'].max().date()}  [{sector}, micro={micro}]", flush=True)
            ok += 1
        else:
            print(f"  {sym:4} {status}", flush=True); err += 1
        time.sleep(2.0)                      # pacing (IB: ~60 req/10min)
    ib.disconnect()
    print(f"=== FIM: {ok} ok, {err} erros ===", flush=True)
    return 0 if err == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=7497)
    p.add_argument("--years", type=int, default=20)
    p.add_argument("--symbols", nargs="+", default=list(UNIVERSE))
    p.add_argument("--client-id", type=int, default=17)
    a = p.parse_args()
    bad = [s for s in a.symbols if s not in UNIVERSE]
    if bad:
        print(f"símbolos desconhecidos: {bad}\ndisponíveis: {list(UNIVERSE)}"); return 2
    return run(a.port, a.years, a.symbols, client_id=a.client_id)


if __name__ == "__main__":
    raise SystemExit(main())
