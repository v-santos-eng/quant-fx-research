# Quant FX Research

A small research platform for testing systematic trading strategies honestly: real tick data, broker-measured costs, a backtester reconciled against MetaTrader 5, and a pre-registered validation gate that every strategy has to pass.

The main result is negative, and that is the point. Four intraday strategies failed the gate; one daily trend strategy showed a real but small edge that does not clear the consistency bar. Nothing here is financial advice.

## The problem

Retail backtests usually look good because of what they leave out: spread and swap costs, the number of variants that were tried before the one that "worked", and any check that the simulator agrees with the broker. This project was built to answer one question with a fixed budget of USD 1,000: is there a strategy that survives all three?

## What it does

- **Data**: downloads Dukascopy ticks, builds bars at several timeframes and reports data quality (`research/download_dukascopy.py`, `bars.py`, `quality_report.py`).
- **Costs**: samples live spreads and reads swap and contract specs from the broker instead of assuming them (`spread_sampler.py`, `spread_model.py`, `costs.py`).
- **Backtester**: reconciled trade by trade against a reference Expert Advisor running in MT5 (`backtester.py`, `reconcile.py`, `mt5/reference_ea.mq5`).
- **Validation**: combinatorial purged cross-validation, probabilistic and deflated Sharpe ratio, Monte Carlo drawdown envelopes (`cv.py`, `validation.py`, `montecarlo.py`).
- **Attempt registry**: every tested variant is recorded, so the deflated Sharpe ratio counts all trials and not only the reported one (`attempt_registry.py`).
- **Strategies tested**: Donchian trend, opening-range breakout, ORB with an ML meta-label filter, intraday mean reversion, daily time-series momentum (`orb.py`, `meanrev.py`, `tsmom.py`, `run_*.py`).
- **Operations**: a local monitor page and Telegram notifications (`monitor_server.py`, `notify.py`).

## Results

Each phase was judged by the same gate, defined before the run. Result files are in `experiments/`.

| Phase | Strategy | Verdict | Deciding number |
| :-- | :-- | :-- | :-- |
| 1 | FX trend (Donchian) | Fail | negative gross return on the majors |
| 1i | Opening-range breakout, M15 | Fail | Sharpe 0.21, PSR 0.81, drawdown 66% |
| 2i | ORB + meta-label | Fail | gradient boosting no better than logistic regression |
| 2a | Intraday mean reversion | Fail | negative gross return on all four symbols |
| 1d | Daily time-series momentum | Partial | gross portfolio Sharpe 0.28; gold + JPY net 0.33, deflated Sharpe about 0.12 |

The daily momentum edge is in line with what the published evidence predicts for a small retail universe, and CFD index swap costs erase it on the full eight-instrument book. The full write-up is in [`docs/relatorio_final.md`](docs/relatorio_final.md).

## Stack

Python 3.14 · pandas · NumPy · PyArrow · PyYAML · pytest · MetaTrader5 · MQL5

## Running it

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest                      # 87 tests, no broker or data needed (test_monitor needs psutil)
```

To reproduce the experiments you need market data and, for the reconciliation and cost sampling, Windows with an MT5 terminal:

```bash
python -m research.download_dukascopy      # fetch ticks into data/
python -m research.build_bars_dataset      # build bars
python -m research.run_tsmom               # run one experiment; output goes to experiments/
```

Credentials are optional and only used for programmatic MT5 login and Telegram alerts. Copy `config/secrets.example.yaml` to `config/secrets.yaml`, which is ignored by git.

## Layout

```
research/      library and experiment runners
tests/         pytest suite
config/        instruments, cost model, risk policy, feature spec
experiments/   result files (JSON) for each phase
docs/          architecture, decisions, gates and the final report (Portuguese)
mt5/           reference Expert Advisor used for reconciliation
```

## Limitations

- Market data is not included; `data/` is generated locally.
- Design documents and the final report are written in Portuguese.
- Results come from one broker's demo feed and cost schedule and will differ elsewhere.

## License

MIT. See [LICENSE](LICENSE).
