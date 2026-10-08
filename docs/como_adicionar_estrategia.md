# Como adicionar e testar uma nova estratégia

> Guia prático para o seu eu futuro. A plataforma vet uma ideia com o **mesmo rigor** que
> reprovou 4 baselines (FX trend, ORB, ORB+ML, reversão — ver `docs/GATES.md`). Seguir este
> fluxo garante um veredito honesto, não um resultado curvado. Interpretador: **`.venv`**.
>
> Regra-mãe: **hipótese com racional econômico ANTES do teste. Nunca garimpar até "passar".**

---

## O padrão (anatomia de uma estratégia)
Toda estratégia tem 2 peças, espelhando `research/orb.py` e `research/meanrev.py`:

1. **Engine** (`research/<nome>.py`): função pura que, sobre barras M15 de um instrumento,
   gera trades determinísticos (sinal → bracket → custo). Reaproveita o encanamento comum.
2. **Runner de busca** (`research/run_<nome>_search.py`): roda uma grade de parâmetros, seleciona
   a config pelo desempenho **out-of-sample** do CPCV e aplica o **gate 1i** (deflacionado por DSR).

O que já existe e você reusa (NÃO reescreva):
- `research/orb._session_mask(ts, session_utc)` — fatia as barras para a janela de sessão.
- `research/orb._mk_trade(...)` — monta um `Trade` com gross/custo (spread par×hora + comissão, swap=0).
- `research/orb._summary(symbol, trades)` — resumo (n_trades, gross, cost, net, win_rate).
- `research/indicators.wilder_atr / adx` — indicadores.
- `research/costs.SymbolCost` + `round_trip_cost_usd` — modelo de custo medido.
- `research/run_orb_pilot._spread_by_hour(code)` e `CAPITAL` — spread p75 por hora, capital $1.000.
- `research/run_orb_search.{_sharpe_pp,_daily_returns,ANN}` — helpers de avaliação.
- `research/cv`, `research/validation`, `research/montecarlo` — CPCV, PSR/DSR, Monte Carlo.

---

## Passo a passo

### 0. Escreva a hipótese (antes de qualquer código)
Uma frase de racional econômico a priori: *por que* esse padrão existiria e *por que* não estaria
arbitrado. Sem isso, você está garimpando. Ex.: "a extensão da abertura reverte porque o excesso
de fluxo de liquidez se esgota" (foi a 2a — reprovou, mas a hipótese era legítima).

### 1. Engine — `research/<nome>.py`
Copie a estrutura de `meanrev.py` (o exemplo mais enxuto). Contrato inegociável:
- **Sem look-ahead:** gatilho decidido no **fechamento** da barra `j`; entrada na **abertura** de `j+1`.
- **Fills intrabar:** stop/alvo checados por `high`/`low` de cada barra (fill honesto).
- **Flat no fim da sessão** (swap=0). Uma entrada por instrumento por sessão (baseline).
- Retorne `{"trades": [...], "summary": _summary(...)}` — mesma forma de `orb_trades`.

Esqueleto mínimo:
```python
from dataclasses import asdict, dataclass
import numpy as np, pandas as pd
from research.indicators import wilder_atr
from research.orb import _mk_trade, _session_mask, _summary

@dataclass(frozen=True)
class MyParams:
    ...  # hiperparâmetros do sinal

def _iter_signals(bars, session_utc, params):
    b = bars.loc[_session_mask(bars["timestamp"], session_utc)].reset_index(drop=True)
    # ... calcule sinal; para cada sessão com trade, yield:
    #   {"dirn": +1/-1, "entry_time": ts, "entry": float, "exit_time": ts, "exit_price": float}

def my_trades(bars, session_utc, sc, spread_by_hour, params=MyParams(), lots=0.1, slippage_mult=0.0):
    trades = [_mk_trade(sc, g["dirn"], g["entry_time"], g["entry"], g["exit_time"],
                        g["exit_price"], lots, spread_by_hour, slippage_mult)
              for g in _iter_signals(bars, session_utc, params)]
    return {"trades": [asdict(t) for t in trades], "summary": _summary(sc.symbol, trades)}
```

### 2. Teste unitário — `tests/test_<nome>.py`
Construa UMA sessão sintética que produz um trade conhecido (assert entry/exit/direção/gross) +
um caso sem gatilho (assert `[]`). Veja `tests/test_meanrev.py`. Rode:
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_<nome>.py -q
```

### 3. Runner de busca — `research/run_<nome>_search.py`
Copie `run_mr_search.py` e troque o engine + a `GRID`. O protocolo anti-p-hacking (não altere):
- Seleciona a config pelo **Sharpe OOS médio do CPCV** (`n_groups=8, n_test_groups=2`), NÃO no full sample.
- **DSR deflaciona por `n_trials = len(grade)`** — corrige a escolha do melhor de N.
- Reporta Sharpe, PSR, % caminhos+ do CPCV, DSR, MaxDD-p99 (Monte Carlo).

### 4. Rode o gate e interprete
```bash
.\.venv\Scripts\python.exe -m research.run_<nome>_search --instrument GER40 --commission 0
```
- **1º corte — bruto positivo por instrumento.** Se o bruto (pré-custo) é ≤ 0, PARE: nenhum ajuste
  de custo/risco/ML cria edge onde não há (lição do FX e da reversão). Faça o scan dos 4 CFDs.
- Comissão = 0 é o caso **otimista** (spread-only). Se falha assim, comissão não salva.

### 5. Registre (pré-registrando o critério)
- **ANTES** de rodar: escreva o critério do gate em `docs/GATES.md` (proibido ajustar depois).
- **DEPOIS**: acrescente o veredito em `docs/GATES.md` e a decisão em `docs/DECISIONS.md`.
  Rode o comando `/checkpoint` para consolidar. O `AttemptRegistry` (SQLite) conta as tentativas
  para o DSR — cada run já loga; não apague.

### 6. Só se PASSAR o gate
Aí sim, e só então, escalar (na ordem):
1. **Meta-label** (padrão `orb_dataset` + `run_metalabel.py`): filtrar para o subconjunto de alta
   qualidade. Exige bater o baseline **com folga**, senão cai (Navalha de Occam).
2. **Medir a comissão real** do CFD (a atual é 0 otimista) e re-testar — corte final.
3. **Reconciliar com o MT5** Strategy Tester (R-01): escrever o EA MQL5 equivalente e bater o
   blotter (padrão `research/reconcile.py`, tolerância pré-registrada).
4. Só depois: risco/sizing (Fase 2), demo, live — **sempre com humano** (nunca autônomo).

---

## O gate 1i (o critério, e por que cada um)
Na série diária líquida da melhor config:

| Critério | Limiar | Por quê |
| :-- | :-- | :-- |
| Bruto por instrumento | > 0 | 1º corte: sem edge bruto, nada salva |
| Sharpe líquido anual | > 0 | precisa ganhar depois do custo |
| **PSR** | > 0,95 | o Sharpe é real, não sorte da amostra (corrige skew/kurtose) |
| CPCV % caminhos+ | ≥ 60% | robusto ao caminho de backtest, não a um split feliz |
| **DSR** | > 0 | sobrevive à deflação por ter testado muitas configs (anti data-mining) |
| MC MaxDD-p99 | tolerável p/ $1.000 | o pior caso plausível não quebra a conta |

**Falha em UM → FAIL honesto.** Diagnostique, registre, decida. Não afrouxe o critério.

---

## As 5 armadilhas (o que reprovou os outros)
1. **Otimizar no full sample** → overfit garantido. Sempre seleção OOS via CPCV.
2. **Ignorar o DSR** → um Sharpe alto entre 81 tentativas é ruído. Deflacione por `len(grade)`.
3. **Assumir custo** → meça do MT5 (`broker_specs_intraday.json`), nunca chute comissão/tick value.
4. **Pular o corte de bruto** → gestão de risco e ML não criam edge; só o realocam.
5. **Confundir menos-trades com melhor** → o filtro tem de subir o Sharpe, não só reduzir o número.

---

## Checklist rápido
- [ ] Hipótese com racional a priori escrita.
- [ ] Engine `research/<nome>.py` (sem look-ahead, fills intrabar, flat na sessão).
- [ ] Teste `tests/test_<nome>.py` verde (1 trade conhecido + 1 no-trade).
- [ ] Critério do gate pré-registrado em `docs/GATES.md`.
- [ ] Runner `run_<nome>_search.py` (seleção OOS + DSR deflacionado).
- [ ] Rodado; bruto+ conferido; veredito interpretado sem afrouxar.
- [ ] Registrado em GATES.md/DECISIONS.md; `/checkpoint`.
- [ ] Só se PASS: meta-label → comissão real → reconciliação MT5 → (humano) demo/live.

---
**Artefatos:** dados `data/bars/<code>/15min.parquet`; specs `config/instruments_intraday.yaml` +
`experiments/broker_specs_intraday.json`; spread `experiments/spread_model_intraday.json`;
resultados `experiments/*.json`. Templates vivos: `research/orb.py`, `research/meanrev.py`,
`research/run_orb_search.py`, `research/run_metalabel.py`.
