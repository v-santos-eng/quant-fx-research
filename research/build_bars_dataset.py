"""Constrói barras H4/H1 do dataset de ticks (Fase 0.4), instrumentado para o monitor.

Lê data/dukascopy/{sym}/**/*.parquet (um dia por arquivo), limpa quotes inválidos,
constrói barras por dia (H4/H1 alinham dentro do dia UTC) e grava
data/bars/{sym}/{tf}.parquet. Publica cada passo via ProgressReporter — dados reais.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from research.bars import build_bars
from research.monitor import ProgressReporter
from research.sanity import drop_invalid_quotes

DATA = Path("data/dukascopy")
OUT = Path("data/bars")
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
TFS = {"4h": "H4", "1h": "H1"}
# Universo intraday: barra de sinal M15 + contexto H1.
TFS_INTRADAY = {"15min": "M15", "1h": "H1"}


def main(symbols: list[str] | None = None, tfs: dict[str, str] | None = None,
         phase: str = "0.4") -> None:
    symbols = symbols or SYMBOLS
    tfs = tfs or TFS
    rep = ProgressReporter(run="build_bars_dataset", phase=phase)
    rep.start_heartbeat(interval=2.0)
    files_by_sym = {s: sorted((DATA / s).rglob("*.parquet")) for s in symbols}
    total = sum(len(v) for v in files_by_sym.values())
    rep.set_step(f"Construção de barras {'/'.join(tfs.values())} do dataset", total=total)

    done_syms: list[str] = []
    try:
        for sym in symbols:
            files = files_by_sym[sym]
            rep.set_queue(pending=[s for s in symbols if s not in done_syms and s != sym],
                          running=[sym], done=done_syms)
            rep.set_task(f"lendo ticks e agregando barras — {sym}",
                         data_source=str(DATA / sym), storage=str(OUT / sym))
            rep.log("INFO", f"iniciando {sym}", files=len(files))
            bars = {tf: [] for tf in tfs}
            n_ticks = n_empty = 0
            for f in files:
                try:
                    df = pd.read_parquet(f)
                except Exception as e:  # noqa: BLE001
                    rep.log("ERROR", f"falha lendo {f.name}", file=str(f), error=str(e))
                    rep.advance(1, current_file=str(f))
                    continue
                df = drop_invalid_quotes(df)
                if df.empty:
                    n_empty += 1
                else:
                    n_ticks += len(df)
                    for tf in tfs:
                        bars[tf].append(build_bars(df, tf))
                rep.advance(1, current_file=str(f.relative_to(DATA)))
            for tf, label in tfs.items():
                out_dir = OUT / sym
                out_dir.mkdir(parents=True, exist_ok=True)
                frame = (pd.concat(bars[tf], ignore_index=True)
                         if bars[tf] else pd.DataFrame())
                out_path = out_dir / f"{tf}.parquet"
                frame.to_parquet(out_path, index=False)
                rep.log("INFO", f"{sym} {label}: {len(frame)} barras",
                        storage=str(out_path), bars=len(frame))
            if n_empty:
                rep.log("WARNING", f"{sym}: {n_empty} arquivos vazios (fim de semana/feriado)")
            done_syms.append(sym)
        rep.set_queue(pending=[], running=[], done=done_syms)
        rep.finish("done")
    except Exception as e:  # noqa: BLE001
        rep.log("ERROR", f"run abortado: {e}")
        rep.finish("error")
        raise


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--intraday", action="store_true", help="usa TFs M15/H1 do universo intraday")
    p.add_argument("--phase", default="0.4")
    a = p.parse_args()
    main(a.symbols, TFS_INTRADAY if a.intraday else None, a.phase)
