# Long-Horizon Quantitative System: MT5 + Dukascopy

Design document, evidence-graded. Single operator, local execution, ten-year survival horizon.

---

## 0. How to read this, and one structural objection

**Evidence tags used throughout:**

`[S]` strong scientific evidence (replicated peer-reviewed results, or mathematical necessity)
`[M]` moderate scientific evidence (published, but contested or with documented decay)
`[E]` industry empirical (observed in practice, no controlled study)
`[H]` plausible hypothesis (mechanism is coherent, evidence is thin)
`[SP]` speculative

Citations are written from memory of the literature. Author, approximate year and journal are given so you can verify each one; check the DOI before you build anything on a single paper. Where I am unsure of a specific attribution I say so rather than inventing precision.

This is systems engineering analysis, not investment advice. I am not a licensed advisor, and nothing here is a recommendation to trade capital.

### The objection

Your specification asks for eight specialist roles, twenty-two strategy families, twenty-eight assets, eight timeframes, sixteen indicators, twenty-six features, nineteen model classes and fourteen validation procedures. Executed literally, that is a two-to-three year research program for a funded team.

You have a full-time PPCP job, an MBA in progress, and one pair of hands.

The dominant risk to this project is not overfitting. It is that the specification is large enough that nothing ever reaches production, or that it reaches production as a half-tested composite of twenty-two ideas whose interactions nobody has validated. `[E]`

A system that runs badly for ten years beats a system designed brilliantly for ten years and never deployed. Every section below therefore ends with a cut, not just an analysis. The cuts are the useful part.

---

## Part 1 — What actually produces long-term consistency

Ranked by expected contribution to whether the system is still solvent and running in 2036.

### 1. Cost accuracy relative to edge size

The ratio that decides everything: gross edge per trade divided by round-trip cost per trade. If that ratio is below roughly 3, the system is a cost-transfer mechanism with noise attached, regardless of how good the signal looks. `[S]`

Bajgrowicz and Scaillet (2012, *Journal of Financial Economics*) applied false-discovery-rate control to thousands of technical trading rules on the Dow and found that surviving rules were largely eliminated once realistic transaction costs were imposed. Sullivan, Timmermann and White (1999, *Journal of Finance*) reached a similar conclusion using White's Reality Check. `[S]`

The specific failure mode for you: Dukascopy publishes JForex conditions widely, but Dukascopy's own documentation states that instrument lists, trading conditions and swaps on MT4/MT5 accounts differ from the standard JForex FX account. Backtesting on free Dukascopy tick data (which reflects the SWFX liquidity view) and executing on an MT5 account is a silent model mismatch. Measure it, do not assume it. `[E]`

### 2. Number of hypotheses tested versus number reported

Selection bias is the largest single source of false discovery in quantitative finance, and it is invisible in the equity curve. `[S]`

Concrete arithmetic. Take a true zero-edge strategy and five years of daily returns. The standard error of the annualized Sharpe ratio is approximately 1/√5 ≈ 0.45. The maximum of 1,000 independent trials sits near 3.2 standard errors above zero, so the best of 1,000 worthless backtests will typically show an annualized Sharpe near 1.4. `[S]`

You will run more than 1,000 configurations. Every parameter sweep, every indicator swap, every asset you try and discard is a trial. Harvey, Liu and Zhu (2016, *Review of Financial Studies*) argued that the conventional t-statistic threshold of 2 should be raised to roughly 3 for newly claimed factors precisely because of this. Bailey, Borwein, López de Prado and Zhu (2014, *Notices of the AMS*) formalized the same point as backtest overfitting and minimum backtest length.

The only defense is a research log that counts trials honestly. Nobody does this. It is the highest-value habit in the entire project.

### 3. Position sizing relative to volatility

Kelly's result in continuous time: the growth-optimal leverage produces a portfolio whose annualized volatility equals the strategy's Sharpe ratio. A strategy with a true Sharpe of 0.8 runs at 80% annual volatility at full Kelly. `[S]`

Two consequences. First, half-Kelly and quarter-Kelly are not conservatism, they are the correct response to the fact that your Sharpe estimate has an enormous standard error. Second, overbetting converts a positive-expectation system into a negative-growth one, and no amount of signal quality repairs that. MacLean, Thorp and Ziemba document the growth-versus-security tradeoff in detail. `[S]`

### 4. Non-stationarity and edge decay

McLean and Pontiff (2016, *Journal of Finance*) found that published anomaly returns decayed materially after publication. In FX specifically, Neely, Weller and Ulrich (2009, *JFQA*) and Olson (2004, *Journal of Banking and Finance*) documented that technical trading rule profitability in currencies declined substantially from the 1970s-80s levels. Lo's Adaptive Markets Hypothesis (2004, *Journal of Portfolio Management*) is the framing that fits this best. `[S]`

Design implication: assume every edge you find has a half-life. Build the revalidation machinery before you build the strategy, because you will need it and you will not want to write it later. `[E]`

### 5. Operational reliability

Power loss, VPS reboot, MT5 auto-update, broker symbol rename (`EURUSD` becoming `EURUSD.r`), server-time DST shifts, expired credentials, silent EA detachment after a terminal restart. `[E]`

I have no controlled study here, and neither does anyone else, but the practitioner consensus is that operational failure ends more retail systems than alpha decay does. It is also the cheapest category to fix.

### 6. Data quality

Weekend gaps, holiday half-sessions, broker-specific bar construction, timezone offsets between the Dukascopy export (UTC) and MT5 server time (broker-defined, often UTC+2/+3 with DST). A one-hour misalignment silently destroys any session-of-day or event-window feature. `[E]`

### 7. Drawdown control and probability of ruin

Separate from sizing because it is about the stopping rule, not the bet size. Practitioner rule of thumb: over a decade, expect a peak-to-trough drawdown of two to three times annualized volatility even if nothing is wrong. `[E]` If your circuit breaker triggers inside that band, you will shut down a working system during a normal drawdown.

### 8. Regime adaptation

Real, but usually implemented as a way to add parameters. Volatility-scaling is the version with the best support (see Part 9). Discrete regime classification is weaker than it looks in-sample.

### 9. Execution quality, slippage, latency

Matters at M1 and below. At H4/D1 with market orders on liquid instruments, latency is close to irrelevant and slippage is a small constant. `[E]` Deprioritized deliberately.

### 10-15. Everything else

Indicator choice, model architecture, feature engineering sophistication, timeframe micro-optimization. These consume 90% of retail research effort and determine perhaps 10% of the outcome. `[E]`

**Ranked summary:**

| # | Factor | Evidence | Effort it deserves |
|---|--------|----------|--------------------|
| 1 | Edge-to-cost ratio | `[S]` | High |
| 2 | Trial counting / multiple testing | `[S]` | High |
| 3 | Sizing vs. volatility | `[S]` | High |
| 4 | Non-stationarity, decay monitoring | `[S]` | High |
| 5 | Operational reliability | `[E]` | Medium-high |
| 6 | Data quality and alignment | `[E]` | Medium-high |
| 7 | Drawdown / ruin control | `[S]`/`[E]` | Medium |
| 8 | Regime adaptation | `[M]` | Medium |
| 9 | Execution, slippage, latency | `[E]` | Low at D1 |
| 10+ | Indicators, model class, features | `[E]` | Low |

---

## Part 2 — Strategy families

### Verdict table

| Family | Evidence | Retail-viable on MT5/Dukascopy | Verdict |
|--------|----------|-------------------------------|---------|
| Time-series momentum / trend following | `[S]` but contested | Yes | **Core** |
| Cross-sectional momentum (FX) | `[M]` | Yes | Secondary |
| Carry | `[S]` academically, `[E]` degraded by retail swaps | Partially | Sizing input only |
| Volatility targeting overlay | `[S]` | Yes | **Core overlay** |
| Regime switching (HMM) | `[M]` | Yes | Filter only |
| Mean reversion (intraday) | `[M]` | Structurally adverse | Exclude |
| Breakout / pullback | `[M]`, mostly a trend re-parameterization | Yes | Redundant |
| Pairs / cointegration / stat arb | `[S]` origin, `[M]` decayed | Poorly | Exclude |
| Seasonality, calendar effects | `[M]`, small and fragile | Yes | Micro-tilt at most |
| Ensemble across horizons | `[S]` (variance reduction) | Yes | **Core** |
| ML (supervised, tabular) | `[M]` | Yes | Constrained overlay |
| VWAP strategies | `[S]` for execution, `[SP]` as alpha | Partially | Execution only |
| Order flow | `[S]` in theory, unavailable to you | No | Exclude |
| Volume profile | `[SP]` on FX | No | Exclude |
| Liquidity sweep / "smart money" | `[SP]` | No | Exclude |
| Market making | `[S]` theory, requires infrastructure you lack | No | Exclude |
| Reinforcement learning | `[H]` for live trading | No | Exclude |

### The families worth your time

**Time-series momentum.** Moskowitz, Ooi and Pedersen (2012, *Journal of Financial Economics*) documented positive time-series momentum across 58 futures and forward instruments over roughly 25 years. Hurst, Ooi and Pedersen (2017, *Journal of Portfolio Management*) extended a trend-following simulation back more than a century across four asset classes.

Now the honest counterweight, which most write-ups omit: Huang, Li, Wang and Zhou (2020, *Journal of Financial Economics*) re-examined time-series momentum and concluded the evidence for it is considerably weaker than originally reported once the test statistic is constructed properly. Goyal and Jegadeesh have also argued that much of what looks like time-series momentum overlaps with cross-sectional effects and a net-long bias.

Net position: `[S]` that trend-following returns existed over long samples in futures and FX, `[M]` that the effect is currently large enough to survive retail costs, and `[E]` that it has compressed since the 2010s. It remains the best-evidenced strategy family available to you, which says as much about the alternatives as about trend.

Why it fits your constraints specifically: it is low-turnover (cost-tolerant), it works at D1 (data you can trust), it has few parameters (low overfitting surface), and it has a coherent economic rationale (slow information diffusion, risk transfer from hedgers, behavioral under-reaction). `[M]` on the rationale, `[S]` on the return series.

**Volatility targeting.** Moreira and Muir (2017, *Journal of Finance*) showed that scaling exposure inversely to recent realized volatility improved risk-adjusted returns across several factors. Harvey and co-authors (2018, *Journal of Portfolio Management*) analyzed volatility targeting across asset classes and found the benefit is strongest where volatility is persistent and the return-volatility relationship is weak, which describes equity indices better than it describes FX. Barroso and Santa-Clara (2015, *JFE*) and Daniel and Moskowitz (2016, *JFE*) showed volatility scaling mitigates momentum crashes.

This is the single highest-value non-signal component in the design. `[S]`

**Carry, with a caveat that kills the naive version.** Lustig, Roussanov and Verdelhan (2011, *Review of Financial Studies*) and Menkhoff, Sarno, Schmeling and Schrimpf (2012, *Journal of Finance*) established the carry premium and its link to global FX volatility. Brunnermeier, Nagel and Pedersen (2008, NBER Macro Annual) documented the crash asymmetry: carry goes up by the stairs and down by the elevator.

The retail problem is mechanical. Broker swap rates carry a markup on both sides of the interest differential. The academic carry premium is computed on interbank forward points; what reaches your account is that premium minus the broker's spread on financing. On many retail books the long-carry leg keeps a fraction of the differential and the short-carry leg pays more than the differential. Verify your actual swap table before treating carry as a return source. `[E]`

Use it as a tie-breaker or a small tilt, not as a standalone strategy.

**Regime switching.** Hamilton (1989, *Econometrica*) is the canonical reference. Two-state Gaussian HMMs on returns reliably identify a low-volatility and a high-volatility state. The trap: smoothed state probabilities (which use the full sample) look far more decisive than filtered probabilities (which use only past data), and only the filtered version is tradeable. In real time, regime detection lags the transition by roughly the length of the estimation window. `[S]` on the mathematics, `[M]` on tradeability.

For your purposes a realized-volatility percentile achieves 80% of what an HMM achieves, with one parameter instead of a fitted transition matrix. Prefer it.

### The families that do not survive contact with your setup

**Mean reversion at intraday horizons.** The effect is real. The problem is that it is compensation for supplying liquidity, and you are structurally a liquidity *taker*. You pay the spread on entry and exit; the market maker earns it. Kyle (1985, *Econometrica*) and Glosten and Milgrom (1985, *JFE*) formalize why the spread exists and who collects it. Trading short-horizon reversal through a retail spread is attempting to harvest a premium while paying it. `[S]`

**Pairs trading and cointegration.** Gatev, Goetzmann and Rouwenhorst (2006, *RFS*) documented profitability in US equities from 1962 to 2002. Do and Faff (2010, 2012, *Financial Analysts Journal* and related) documented substantial decline in later periods, with remaining profits concentrated in illiquid pairs. On MT5 you have no true multi-leg order, you pay two spreads and two swaps, and the FX cross-rate relationships that look cointegrated are mostly arithmetic identities (EURGBP is definitionally close to EURUSD/GBPUSD) rather than statistical opportunities. `[S]` that the identity holds, `[E]` that the residual is smaller than your costs.

**Order flow, volume profile, liquidity sweeps.** Order flow analysis is genuinely powerful and genuinely well-supported in the microstructure literature (Kyle 1985; Easley, López de Prado and O'Hara 2012, *RFS*, on VPIN). It requires actual signed order flow from a centralized venue. Spot FX has no consolidated tape. What MT5 gives you on FX is *tick volume*, a count of price updates from one broker's feed, not traded volume. Volume profile built on tick volume is a proxy of a proxy.

"Liquidity sweep", "smart money concepts", "order blocks" and similar have no peer-reviewed empirical support that I am aware of. They are chart-pattern taxonomies with new names. `[SP]` Excluded, and this is exactly the separation you asked for between academic support and social-media popularity.

**Market making.** Avellaneda and Stoikov (2008, *Quantitative Finance*) give the theory. The practice requires queue priority, rebates or at minimum zero-commission passive fills, and co-location. Dukascopy's marketplace does allow limit orders that can be passive, but you have no rebate structure and no latency advantage. `[S]` that the theory is correct, `[S]` that you cannot implement it.

**Reinforcement learning.** Moody and Saffell (2001, *IEEE Transactions on Neural Networks*) started direct reinforcement for trading; Zhang, Zohren and Roberts (2020, *Journal of Financial Data Science*) is a reasonable modern reference. The blockers: RL needs a simulator, your simulator is a backtest, and the backtest is exactly the thing you cannot trust. PPO/SAC/TD3/DQN are sample-hungry in an environment where you have roughly 5,000 daily observations per instrument and the data-generating process shifts underneath you. Every published success is either in a simulated market or in a high-data regime you do not have. `[H]` at best for live retail deployment. Excluded, and this is one of the clearest exclusions in the document.

---

## Part 3 — Asset selection

### The one metric that matters most

Rank by **round-trip cost divided by average daily range**, not by spread alone. Spread in isolation is meaningless; a 30-cent spread on gold is cheap and a 3-pip spread on EURUSD is expensive, because the denominators differ by an order of magnitude.

Approximate figures below. These are order-of-magnitude anchors, `[E]`, and the entire point is that **you must measure them on your own MT5 account**, because Dukascopy's MT5 conditions differ from JForex conditions and both differ from what the free tick export implies.

| Instrument | Typical round-trip cost | Typical daily range | Cost / range | Data depth | Verdict |
|---|---|---|---|---|---|
| EURUSD | ~0.6-1.0 pip | ~55-75 pips | ~1.0-1.5% | 2003+ tick | **Tier 1** |
| USDJPY | ~0.7-1.1 pip | ~60-90 pips | ~1.0-1.5% | 2003+ | **Tier 1** |
| GBPUSD | ~0.9-1.4 pip | ~75-110 pips | ~1.0-1.6% | 2003+ | **Tier 1** |
| AUDUSD | ~0.8-1.3 pip | ~50-70 pips | ~1.3-2.0% | 2003+ | Tier 1-2 |
| USDCAD | ~1.0-1.6 pip | ~55-80 pips | ~1.5-2.2% | 2003+ | Tier 2 |
| USDCHF | ~1.0-1.6 pip | ~45-65 pips | ~1.8-2.5% | 2003+ | Tier 2, SNB-tail risk |
| XAUUSD | ~$0.20-0.40 | ~$25-45 | ~1.0-1.5% | 2003+ | **Tier 1** |
| US500 CFD | ~0.5-1.0 index pt | ~50-90 pts | ~1.0-1.8% | shorter | Tier 1-2, financing |
| US100 CFD | ~1.5-3.0 pts | ~250-450 pts | ~0.7-1.2% | shorter | Tier 1-2 |
| DAX CFD | ~1.0-2.0 pts | ~250-400 pts | ~0.4-0.8% | shorter | Tier 2 |
| WTI CFD | ~3-6 ticks | ~$1.50-2.50 | ~1.5-3.0% | shorter, rollover | Tier 2-3 |
| EURJPY, AUDJPY, CADJPY | ~1.5-2.5 pips | ~80-120 pips | ~1.8-3.0% | good | Tier 3 |
| GBPJPY | ~2-4 pips | ~110-170 pips | ~1.8-3.0% | good | Tier 3 |
| XAGUSD | wide, variable | high | ~2-4% | good | Tier 3 |
| Natural gas | very wide | very high | ~3-6% | rollover mess | **Exclude** |
| BTC/ETH/LTC CFD | very wide | very high | ~2-5%, weekend gaps | short | **Exclude** |
| FTSE, Nikkei, CAC40 | moderate | moderate | ~1-2% | shorter | Optional Tier 3 |
| Platinum | thin | moderate | high | poor | **Exclude** |

### The diversification illusion

Twelve FX pairs is not twelve bets. Run a PCA on daily returns of the majors: the first component (essentially the dollar factor) typically explains a large majority of the variance, and the second (risk-on/risk-off, often JPY and AUD loading opposite) most of the rest. `[E]`, and measure it yourself on your Dukascopy data before believing my numbers.

Grinold's fundamental law of active management gives IR ≈ IC × √BR, where BR is the number of *independent* bets. `[M]` Trading twelve correlated USD pairs gives you an effective breadth closer to three or four. Adding GBPJPY to a book that already holds GBPUSD and USDJPY adds turnover and cost, not breadth.

Real breadth comes from crossing asset classes: currencies, metals, equity indices, energy. That argues for a small number of instruments spread across sectors rather than a large number within FX.

### Recommended universe

Eight to ten instruments: EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, XAUUSD, US500, US100, plus optionally DAX and WTI.

Excluded and why: crypto CFDs (cost, weekend gap risk, short history, and the CFD wrapper adds broker-specific behavior on top of an already unstable asset); natural gas (contract rollover and cost); platinum (liquidity); the JPY crosses (redundant given the majors already held); silver (cost-to-range roughly double gold with correlated exposure).

---

## Part 4 — Timeframes

Two arithmetic constraints decide this, and neither is a matter of taste.

**Constraint one: cost.** Cost per round trip is roughly fixed. Expected move per bar scales with the square root of the bar duration. Halving the timeframe multiplies your cost drag per unit of signal by roughly √2. Going from D1 to M5 multiplies it by roughly √288 ≈ 17. An edge that is comfortably profitable at D1 is invisible under costs at M5. `[S]`

**Constraint two: sample size.** Twenty years gives you roughly 5,200 D1 bars, 31,000 H4 bars, 125,000 H1 bars. The D1 number looks small, and it is: with ten instruments sharing a dominant common factor, your effective independent sample for a directional strategy is in the low thousands, not tens of thousands. This is the single hardest constraint on model complexity in the whole project, and it is why a deep network is the wrong tool (Part 7). `[S]`

The counterargument for lower timeframes is that they generate more observations. The catch is that high-frequency observations are not independent draws from a stationary process; they are heavily autocorrelated samples of the same regimes. Microstructure noise dominates below roughly the five-minute scale (the volatility signature plot literature: Andersen and Bollerslev 1998; Zhang, Mykland and Aït-Sahalia 2005, *JASA*; Bandi and Russell on optimal sampling). `[S]`

| Timeframe | Noise | Cost drag | Overfit risk | Verdict |
|---|---|---|---|---|
| Tick | Extreme | Fatal | Extreme | Research/cost measurement only |
| M1 | Very high | Very high | Very high | Exclude |
| M5 | High | High | High | Exclude |
| M15 | High | Moderate-high | High | Exclude |
| M30 | Moderate | Moderate | Moderate | Marginal |
| H1 | Moderate | Moderate-low | Moderate | Usable for entry timing |
| **H4** | Low-moderate | Low | Moderate | **Signal candidate** |
| **D1** | Low | Very low | Low (few params) | **Primary** |

**Decision: signals computed on D1, execution timed on H1 or H4.** Tick data used only to measure realistic spread and slippage distributions, never for signal research.

---

## Part 5 — Technical indicators

Nearly all of the sixteen indicators you listed are measuring one of three underlying quantities.

**Quantity A, direction:** price relative to a smoothed price. EMA, SMA, MACD, SuperTrend, Ichimoku's cloud, ROC and the mid-line of Bollinger and Keltner are all transformations of this. Their pairwise correlations on the same lookback are typically above 0.9. `[E]`

**Quantity B, dispersion:** ATR, Bollinger bandwidth, Keltner width, realized volatility, Donchian channel width. Same quantity, different estimator.

**Quantity C, normalized position within a recent range:** RSI, CCI, Stochastic, %B, and the Donchian position. Bounded oscillators are monotone-ish transforms of "where is price in its recent distribution".

Everything else is either a combination of A, B and C, or a volume derivative.

| Indicator | Unique information | Verdict |
|---|---|---|
| ATR | Volatility scale, robust to gaps | **Keep.** Sizing input, not signal |
| EMA / SMA | Direction (A) | **Keep one.** Difference of two lengths |
| Realized volatility (close-to-close or Parkinson) | Better volatility estimator than ATR for scaling | **Keep** |
| ADX | Trend strength, but it is a nonlinear function of A and B | Optional filter, weak evidence `[M]` |
| Donchian | Direction via breakout, low parameter count | Keep as an alternative direction estimator |
| Bollinger, Keltner | A + B repackaged | Drop, redundant |
| RSI, CCI, ROC, Stochastic | C, mutually redundant | Drop all but at most one |
| MACD | Difference of two EMAs, i.e. A | Drop, redundant with EMA spread |
| SuperTrend, Ichimoku | A + B with more parameters | Drop. More knobs, no new information |
| VWAP | Real information intraday on centralized markets | Drop for FX at D1. No true volume |
| OBV, MFI | Require real volume | **Drop on FX.** Tick volume is not volume |

Brock, Lakonishok and LeBaron (1992, *Journal of Finance*) found predictive value in simple moving-average and range-breakout rules on the Dow. Their result is the strongest academic support any of these indicators has, and it applied to the simplest rules, not the elaborate ones. Sullivan, Timmermann and White (1999) subsequently showed much of that result weakens under data-snooping correction. `[S]` that simple rules had historical value, `[M]` that it persists net of costs.

**Cut to four inputs:** a fast/slow moving-average spread, ATR, realized volatility, and Donchian position. That is it.

---

## Part 6 — Feature engineering

### Features with real published support

Log returns at multiple horizons, volatility-normalized. This is the time-series momentum signal itself (Moskowitz, Ooi, Pedersen 2012). `[S]` for construction, `[M]` for current strength.

Realized volatility, and its persistence. Volatility is the most predictable quantity in finance, far more so than returns. Corsi (2009, *Journal of Financial Econometrics*) introduced the HAR-RV model, which uses daily, weekly and monthly realized volatility components and is hard to beat with anything more complex. Andersen, Bollerslev, Diebold and Labys (2003, *Econometrica*) is the foundational realized-volatility reference. `[S]`

This asymmetry deserves emphasis: you can forecast volatility well and direction barely at all. Design the system so that the well-forecast quantity does the heavy lifting (sizing) and the poorly-forecast quantity does as little as possible (direction, coarse).

Cross-sectional rank of momentum across the universe. `[M]`, from the currency momentum literature (Menkhoff, Sarno, Schmeling, Schrimpf 2012, *JFE*).

Interest rate differential / carry, as a slow-moving state variable rather than a signal. `[S]` academically, `[E]` degraded by retail swap markups.

Rolling correlation to the dollar factor and to a risk proxy, used for exposure netting rather than prediction. `[E]`

Scheduled-event proximity (hours to the next tier-1 release). Ederington and Lee (1993, *Journal of Finance*) and Andersen, Bollerslev, Diebold and Vega (2003, *American Economic Review*) established that scheduled macro announcements produce sharp, systematic volatility responses. This is one of the best-supported intraday regularities in FX. `[S]`

### Features that sound good and do not deliver

The Hurst exponent. Estimation is the problem, not the concept. Classical R/S is severely biased in small samples and confounded by short-memory autocorrelation and heteroskedasticity; Lo (1991, *Econometrica*) introduced a modified R/S statistic and found little evidence of genuine long memory in stock returns once short-range dependence was accounted for. Weron (2002, *Physica A*) documented the finite-sample bias. On 250-day rolling windows the estimate is mostly noise. `[S]` that it is badly estimated. Drop it.

Rolling skewness and kurtosis of returns. Both are dominated by a handful of extreme observations, so the rolling estimate is a lagged indicator of "was there a big move recently", which ATR already tells you more cleanly. `[E]` Drop.

Rolling autocorrelation of returns. Very low signal-to-noise at daily frequency. Interesting for diagnostics, useless as a feature. `[E]`

Support and resistance distance. No agreed operational definition, therefore a large hidden researcher-degrees-of-freedom surface. Every implementation choice is an untracked trial. `[SP]` Drop.

Day of week and hour of day, as raw categorical features. There is genuine session structure in FX volatility, and it belongs in the *cost and execution* model, not in the return-prediction model. As direction features they are pure multiple-testing surface: five days times twenty-four hours is 120 buckets, several of which will look significant by construction. `[E]`

### Feature set to actually build

About twelve columns per instrument:

Volatility-scaled returns over 21, 63 and 126 days. Realized volatility over 21 and 63 days, plus the ratio between them (a volatility-trend term). ATR(14) normalized by price. Donchian position over 63 days. Cross-sectional momentum rank within the universe. Correlation to the equal-weighted universe over 63 days. Hours to next tier-1 scheduled event. Current spread relative to its own 63-day median (this one is a *cost* feature and a live health check, and it is the most under-used variable in retail systems).

Fractional differentiation (López de Prado 2018) is worth knowing about: it makes a series stationary while retaining more memory than integer differencing. `[M]` Optional, not required for a D1 trend design.

---

## Part 7 — Machine learning

### The binding constraint

You have roughly 5,000 daily observations per instrument, ten instruments, and a dominant common factor. Signal-to-noise in daily directional prediction is on the order of an R² of 0.001 to 0.01 in published work. That combination admits models with tens of effective parameters, not millions. `[S]`

| Model | Interpretability | Data need | Overfit risk | Evidence in finance | Verdict |
|---|---|---|---|---|---|
| Linear / ridge regression | High | Low | Low | `[S]` | **Baseline, always** |
| Logistic regression | High | Low | Low | `[S]` | Baseline for classification |
| Random forest / extra trees | Medium | Medium | Medium | `[M]` | Acceptable |
| **LightGBM / XGBoost / CatBoost** | Medium | Medium | Medium-high | `[M]`, strongest of the ML group | **Chosen if any ML is used** |
| SVM | Low | Medium | High | `[M]`, dated | Skip |
| Hidden Markov models | Medium | Low | Medium | `[M]` | Optional regime filter |
| Bayesian / hierarchical models | High | Low | Low | `[M]`, underused | Worth exploring for shrinkage |
| LSTM / GRU | Low | Very high | Very high | `[M]`, mixed replication | Skip |
| Transformers / TFT | Very low | Extreme | Extreme | `[M]` in forecasting, `[H]` in trading | Skip |
| TCN | Low | Very high | Very high | `[H]` | Skip |
| PPO / SAC / TD3 / DQN | Very low | Extreme | Extreme | `[H]` | **Exclude** |

Gu, Kelly and Xiu (2020, *Review of Financial Studies*) found that trees and neural networks outperformed linear models for equity return prediction, which is the strongest single result supporting ML in asset pricing. Note the setting: thousands of stocks, hundreds of characteristics, decades of monthly data. Your setting is ten instruments and twelve features. The result does not transfer automatically. `[M]`

Krauss, Do and Huck (2017, *European Journal of Operational Research*) compared deep networks, gradient boosting and random forests on S&P 500 constituents and found the ensemble of all three did best, with returns decaying sharply in later years. Fischer and Krauss (2018, *EJOR*) reported LSTM results on the same universe with the same decay pattern.

On architecture fashion, Zeng and co-authors (2023, AAAI, "Are Transformers Effective for Time Series Forecasting?") showed that a single-layer linear model beat several transformer variants on standard long-horizon forecasting benchmarks. The M5 forecasting competition was won by gradient-boosted trees, not deep networks. `[S]` Take the hint.

### How to use ML without it eating the project

Use it as a **meta-labeler**, following López de Prado (2018, *Advances in Financial Machine Learning*). The primary signal (trend) decides direction. A LightGBM classifier decides only whether to take the trade, outputting a size multiplier in [0, 1]. It can never flip direction and it can never increase size beyond the base.

This has three properties that matter. Failure is bounded: the worst case is that the filter is uninformative and you get the base strategy back. It is testable in isolation: precision and recall of the filter are measurable independently of the strategy return. And it keeps the economically motivated component in charge, which is the thing you can still reason about in 2033 when performance degrades.

Build the system to work with the meta-labeler disabled. Turn it on only if it clears the Part 8 gates on its own.

---

## Part 8 — Statistical validation

### What each method detects

| Method | Detects | Priority |
|---|---|---|
| Walk-forward optimization | Whether parameters chosen on past data work on subsequent data | High |
| Nested walk-forward | Contamination from selecting the walk-forward configuration itself | High |
| Purged K-fold CV | Leakage from overlapping labels and serial correlation across fold boundaries | High |
| Combinatorial purged CV (CPCV) | Same as above, plus generates a *distribution* of Sharpe ratios instead of one number | High |
| Probability of backtest overfitting (PBO) | Probability that the configuration you selected will underperform the median out of sample | **Highest** |
| Deflated Sharpe ratio | Whether the observed Sharpe survives correction for number of trials, non-normal returns, and sample length | **Highest** |
| Probabilistic Sharpe ratio | Confidence that true Sharpe exceeds a threshold, given skew and kurtosis | High |
| White's Reality Check | Whether the best of many rules beats a benchmark once data snooping is accounted for | Medium |
| Hansen's SPA test | Same, less sensitive to poor rules dragging the null distribution | Medium |
| Stationary bootstrap (Politis and Romano 1994) | Sampling uncertainty while preserving serial dependence | High |
| Monte Carlo trade-order shuffling | Path dependence of drawdown, sequencing risk | Medium |
| Sensitivity analysis | Whether the result sits on a parameter plateau or a spike | High |
| Stress testing on historical crises | Behavior in 2008, 2011, 2015 SNB, 2020, 2022 | High |
| Temporal degradation analysis | Whether performance is monotonically decaying across the sample | **Highest** |

References: purged CV, CPCV, PBO and meta-labeling are from López de Prado (2018) and Bailey, Borwein, López de Prado, Zhu (2014, *Notices of the AMS*). Deflated Sharpe: Bailey and López de Prado (2014, *Journal of Portfolio Management*). Probabilistic Sharpe and minimum track record length: Bailey and López de Prado (2012). Reality Check: White (2000, *Econometrica*). SPA: Hansen (2005, *Journal of Business and Economic Statistics*). Sharpe ratio standard errors under non-IID returns: Lo (2002, *Financial Analysts Journal*).

### The three that matter most, and why

**Temporal degradation analysis** is first because it is the only one that tests the assumption your entire ten-year premise rests on. Split the sample into five equal blocks and compute performance in each. If the pattern is 2005-2010 strong, 2011-2016 moderate, 2017-2022 weak, 2023+ flat, the aggregate Sharpe is a historical artifact and the strategy is already dead. This test alone would have prevented a large fraction of retail FX system failures. `[S]`

**Deflated Sharpe ratio** is second because it is the only one that prices in the trials you ran. It requires you to know the number of trials, which requires the research log, which is why the log is not optional bookkeeping.

**Probability of backtest overfitting** is third because it answers the question you actually care about: given that I selected this configuration, what is the chance it underperforms the median configuration out of sample? A PBO above 0.5 means your selection procedure is worse than random.

### Acceptance thresholds

These are my proposed gates. They are `[E]`, not derived from theory, and they are deliberately harsh:

- Deflated Sharpe ratio significant at p < 0.05 accounting for the true trial count
- PBO < 0.35
- Positive net performance in at least 4 of 5 temporal blocks
- Performance within one standard error across a parameter neighborhood of ±30%
- Net Sharpe after modeled costs at least 60% of gross Sharpe (if costs eat more than 40%, the edge is too thin)
- Survives a doubling of assumed transaction costs with positive expectancy remaining

If a strategy fails any of these, it does not proceed. Not "with reduced size". It does not proceed.

---

## Part 9 — Risk management

### Sizing, layered

**Layer 1, instrument-level volatility scaling.** Position size in instrument i is proportional to (target risk contribution) / (σ_i), where σ_i is an exponentially-weighted realized volatility, typically 21 to 63 day. This equalizes risk across instruments rather than equalizing notional. `[S]`

**Layer 2, portfolio volatility targeting.** Scale the whole book so ex-ante portfolio volatility (using the full covariance matrix, not the sum of individual volatilities) hits a target. Recompute daily, but apply the change only when it exceeds a band of roughly 20%, otherwise you pay turnover for noise. `[S]` for the concept (Moreira and Muir 2017; Harvey et al. 2018), `[E]` for the band.

**Layer 3, fractional Kelly cap.** With a true Sharpe of 0.8, full Kelly implies about 80% annualized volatility. Set the target at 8% to 10%. That is roughly one-eighth Kelly, deliberately below the usual quarter-Kelly recommendation, because your Sharpe estimate has a standard error of similar magnitude to the estimate itself. `[S]`

At 10% annualized volatility, expect a worst-decade drawdown around 20% to 30%. `[E]` Write that number down before you start, because you will experience it, and the decision you make at that moment determines the ten-year outcome more than any modeling choice.

### Limits and circuit breakers

| Control | Proposed level | Rationale |
|---|---|---|
| Per-instrument risk cap | 25% of total portfolio risk | Prevents single-instrument concentration after a volatility collapse |
| Asset-class cap | 50% of total risk | FX, metals, indices, energy |
| Correlation-adjusted gross cap | Portfolio vol ≤ 1.5× target | Catches correlation spikes in crises |
| Daily loss halt | 2% of equity | Stops runaway execution bugs, not market moves |
| Monthly de-risk trigger | 8% drawdown, halve exposure | Deep enough not to fire in normal drawdowns |
| Hard stop | 20% peak-to-trough, full flat, mandatory review | Approximately the expected worst case, so hitting it is genuine evidence of a problem |
| Recovery rule | Return to full size only after 60 trading days above the trigger level | Prevents whipsaw de-risking |

The daily halt is set tight on purpose because at D1 frequency a 2% single-day loss is more likely to indicate a software fault (duplicated orders, wrong lot calculation, stale signal file) than a market event. It is an operational tripwire disguised as a risk limit.

### VaR, Expected Shortfall, and their honest limitations

Compute both, use historical simulation rather than a Gaussian assumption, and treat them as monitoring instruments rather than sizing inputs. Artzner and co-authors (1999, *Mathematical Finance*) showed VaR is not a coherent risk measure because it fails subadditivity, while Expected Shortfall is coherent. The Basel framework moved toward ES for the same reason. `[S]`

The limitation you cannot engineer away: both are estimated from history, and FX tail events are exactly the ones history under-samples. The January 2015 CHF move was roughly a 30-standard-deviation event under any pre-2015 estimated distribution. `[S]` No risk measure protects you from that. Only a hard cap on gross leverage and an instrument choice that avoids pegged or managed currencies does.

### Operational risk, which is the one that will actually bite

Broker insolvency (split capital across venues once size justifies it), symbol renames breaking the EA, MT5 terminal updates changing behavior, VPS failure, credential expiry, a signal file written half-way when the terminal reads it. Every one of these is a real failure mode with a cheap fix. `[E]`

---

## Part 10 — Macroeconomic events

Ederington and Lee (1993, *Journal of Finance*) documented that scheduled macro releases produce sharp volatility spikes concentrated in the minutes after release. Andersen, Bollerslev, Diebold and Vega (2003, *AER*) quantified the announcement effect on exchange rates in high-frequency data. Lucca and Moench (2015, *Journal of Finance*) documented the pre-FOMC announcement drift in equities. Savor and Wilson (2013) showed a disproportionate share of the equity risk premium accrues on announcement days. All `[S]`.

What follows for a D1 trend system is less dramatic than most people assume. If your holding period is measured in weeks, an event that moves the market 60 pips in ten minutes is not a threat to the strategy. It is a threat to your *execution*, because spreads widen by a factor of five to twenty and slippage on market orders becomes unbounded. `[E]`

| Event class | Action |
|---|---|
| FOMC, ECB, BoJ rate decisions | No new entries in a window of 30 minutes before to 30 minutes after. Existing positions held. |
| CPI, PCE, NFP | Same window. These are the three largest scheduled FX movers. |
| PPI, PMI, GDP, retail sales | No entry restriction. Log the timestamp for post-hoc analysis. |
| Central bank speeches, unscheduled | No filter possible. Rely on volatility targeting. |
| Geopolitical / unscheduled crises | No prediction attempted. Volatility scaling reduces exposure with a lag of days, which is the honest limit of the design. |

Do not flatten positions before events. For a trend system, the round-trip cost of exiting and re-entering across a few dozen events per year exceeds the expected saving, and you convert a market-risk exposure you are paid for into a certain cost. `[E]`

Do not attempt to trade the announcements. Post-announcement drift in FX at the minute scale is a latency game against firms with direct feeds and co-location. `[S]` that they are faster, `[S]` that you cannot compete.

One practical detail: the calendar itself is a dependency. If you filter on scheduled events, the system needs the calendar loaded before the session, and it needs to fail safe (no new entries) if the calendar is missing rather than fail open.

---

## Part 11 — Software architecture

### The single most important architectural decision

**MT5 is an execution shell. Nothing else.** All research, feature computation, model fitting and signal generation happen in Python. The MQL5 Expert Advisor receives target positions and does four things: reconcile current positions against targets, place and manage orders, enforce local hard limits (max lots, max positions, daily loss halt), and emit a heartbeat.

Three reasons. MQL5 is a poor research environment and its Strategy Tester actively invites the failure mode you are trying to avoid, since genetic optimization over thousands of parameter combinations is exactly the trial-count explosion Part 8 exists to control. Second, coupling research to the platform makes broker migration a rewrite, and over ten years you will change brokers. Third, a thin EA is auditable; you can read all 400 lines of it and know what it does.

### Components

```
data/          Dukascopy tick + bar ingestion, immutable raw store (Parquet)
               Broker feed capture (live spreads, fills) for cost model calibration
               Schema validation, gap detection, timezone normalization to UTC
features/      Deterministic, versioned, pure functions. Point-in-time correct.
               Every feature has a unit test asserting no forward leakage.
models/        Trend signal (primary). Optional LightGBM meta-labeler (secondary).
               Model artifacts versioned with the exact feature set and data hash.
portfolio/     Covariance estimation, volatility targeting, risk caps, netting
               Output: target position per instrument, in lots
risk/          Pre-trade checks, circuit breaker state machine, kill switch
execution/     Signal file writer (atomic write then rename, never partial)
               MQL5 EA: reconciliation loop, order placement, heartbeat
monitor/       Live vs. backtest tracking error, spread anomaly detection,
               position reconciliation alarm, heartbeat watchdog
research/      Backtest engine, CPCV, DSR, PBO. Trial log (append-only).
```

### Non-negotiable engineering practices

Raw data is immutable and append-only. Cleaned data is a derived artifact you can rebuild from raw at any time, with the cleaning code versioned. If you cannot regenerate a 2019 backtest byte-for-byte three years from now, you cannot diagnose a 2029 failure.

Point-in-time correctness is enforced by test, not by care. Every feature gets a test that shifts the input series forward and asserts the feature at time t is unchanged. This catches the leakage bug class that produces beautiful, worthless backtests.

The trial log is append-only and machine-readable: timestamp, hypothesis, configuration hash, data range, result. This is what makes deflated Sharpe computable. It is also the thing you will be tempted to skip.

Reconciliation runs every cycle: what the EA believes it holds, what the broker reports, and what the portfolio module intended. Any mismatch halts new orders and alerts. Silent position drift is the most common way a working system quietly stops being the system you tested.

Atomic file handoff. Write to a temp file, fsync, rename. A partially written signal file read by the EA mid-write is a real and expensive bug.

CI runs the full test suite plus a fixed-seed backtest on a frozen data slice, and fails if the equity curve changes. That single test catches most accidental behavior changes.

---

## Part 12 — Roadmap with quantitative gates

No phase begins until the prior phase's exit criteria are met and recorded.

**Phase 0, cost and data audit. Four weeks.**
Deliverables: Dukascopy tick data ingested for the candidate universe from 2010; broker-side spread and fill logging running on a demo account for at least 20 trading days; a measured cost distribution per instrument (median, 90th percentile, event-window).
Exit criteria: measured round-trip cost per instrument documented with an uncertainty band; the divergence between Dukascopy quotes and broker MT5 quotes quantified; the universe re-ranked using measured rather than assumed costs.
This phase alone eliminates most of the failure modes in Part 1. Do not skip it, and do not run it in parallel with strategy research.

**Phase 1, baseline. Four weeks.**
Deliverable: a single-parameter D1 time-series momentum strategy on the full universe, volatility-scaled, no filters, no ML, no optimization.
Exit criteria: net-of-cost Sharpe above 0.3 across the full sample, positive in at least 3 of 5 temporal blocks. If the naive baseline is negative net of measured costs, stop and reconsider the entire premise rather than adding complexity to rescue it.

**Phase 2, portfolio construction. Four weeks.**
Deliverable: covariance estimation, portfolio volatility targeting, risk caps.
Exit criteria: realized volatility within ±25% of target in backtest; maximum drawdown reduced versus Phase 1; Sharpe not degraded by more than 10%.

**Phase 3, statistical validation. Six to eight weeks.**
Deliverable: CPCV distribution, DSR, PBO, sensitivity surface, stress tests, temporal degradation report.
Exit criteria: the six thresholds in Part 8. Expect to fail here. Failing here is the system working.

**Phase 4, paper trading. Six months minimum.**
Deliverable: full stack running against a demo account, generating the same signals the backtest would.
Exit criteria: tracking error between live-generated and backtest-generated signals below 5%; zero unreconciled position events in the final 60 days; realized cost per trade within the Phase 0 band; heartbeat uptime above 99%.
Six months is not negotiable. It is the minimum time to encounter a month-end, a quarter-end, a DST transition, a broker maintenance window and at least one surprise.

**Phase 5, minimum capital. Six months.**
Size at the smallest amount where lot granularity does not distort the portfolio, which for a ten-instrument book means micro lots.
Exit criteria: realized slippage within the modeled distribution; no operational incident requiring manual intervention in the final 90 days.

**Phase 6, scaling. Twelve to eighteen months.**
Double the capital only after each level has run three months without an operational incident and with realized volatility inside the target band.

**Phase 7, continuous operation.**
Monthly: performance versus the backtest distribution from CPCV. Are you inside the 90% band?
Quarterly: cost re-measurement, correlation structure review.
Annually: full revalidation on data including the newest year, with the trial count updated. If DSR fails on the extended sample, reduce size by half and investigate. Predefine this rule now, while you are calm.

Realistic total: roughly two and a half to three years to full production. If that timeline is unacceptable, the honest response is to reduce scope, not to compress validation.

---

## Part 13 — The system I would build

### Specification

Universe of eight: EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, XAUUSD, US500, US100.

Signal: time-series momentum, computed as the volatility-scaled return over three lookbacks (roughly 21, 63 and 126 days), averaged into a single score per instrument. Positions proportional to the score, capped. Direction changes only when the blended score crosses zero, with a small deadband to control turnover.

Sizing: inverse volatility at instrument level, portfolio volatility targeted at 10% annualized, ex-ante covariance from a shrunk 126-day estimator, rebalanced when drift exceeds 20%.

Regime overlay: exposure scaled down when portfolio realized volatility exceeds its own 90th percentile.

Optional secondary: LightGBM meta-labeler outputting a multiplier in [0, 1], deployed only if it independently clears the Part 8 gates. The system is designed to run correctly with it disabled.

Execution: signals computed after the D1 close, orders placed at a fixed time in the following session, market orders, no stop-loss orders resting at the broker. Position sizing is the risk control; a stop at a fixed distance is a second, uncalibrated risk control that interacts badly with the first and creates a visible resting order in an environment where you cannot verify how it is handled.

Event filter: no new entries in the 30-minute window around FOMC, ECB, BoJ, CPI, PCE and NFP.

### Subsystem assessment

| Subsystem | Evidence | Expected contribution | Degradation risk over 10y | Maintenance |
|---|---|---|---|---|
| Multi-horizon TSMOM signal | `[S]` historically, `[M]` currently | The entire directional edge | **High.** Documented compression | Low |
| Volatility scaling | `[S]` | Large risk-adjusted improvement | Low. Volatility persistence is stable | Low |
| Portfolio vol targeting | `[S]` | Large. Controls the ruin channel | Low | Medium |
| Instrument diversification | `[S]` (variance math) | Moderate, limited by common factors | Medium. Correlations rise in crises | Low |
| Fractional Kelly cap | `[S]` | Prevents the dominant failure mode | None. It is arithmetic | None |
| Circuit breakers | `[E]` | Bounds the operational tail | Low | Low |
| Event filter | `[S]` on the volatility effect, `[E]` on the filter's value | Small | Low | Medium (calendar dependency) |
| Realized-vol regime overlay | `[M]` | Small to moderate | Medium | Low |
| LightGBM meta-labeler | `[M]` | Uncertain, possibly zero | **High.** Retraining invites drift | **High** |
| Monitoring and reconciliation | `[E]` | Indirect but decisive | None | Medium |

The meta-labeler is the only component whose maintenance cost is high and whose contribution is uncertain. It is therefore the first thing to remove if the project is running behind, and the first suspect if live performance diverges from backtest.

### Deliberate exclusions, with reasons

Reinforcement learning: no trustworthy simulator, sample requirements you cannot meet, no interpretable failure mode. `[H]` evidence for live retail use.

Deep sequence models (LSTM, GRU, TCN, Transformer, TFT): parameter counts incompatible with a few thousand effective observations. The forecasting literature itself has walked this back.

Order flow, volume profile, VWAP as alpha, liquidity sweeps, smart money concepts: the required data does not exist in retail spot FX, or the concept has no empirical support. `[SP]`

Market making: requires infrastructure you do not have. `[S]`

Pairs trading and cointegration on FX: cross-rate relationships are arithmetic identities, residuals are smaller than costs, and MT5 has no multi-leg execution.

Crypto CFDs, natural gas, platinum, silver, JPY crosses: cost-to-range ratios two to five times worse than the chosen universe, or redundant exposure.

Timeframes below H1 for signal generation: cost drag scales as the inverse square root of bar duration and destroys the edge.

MT5 Strategy Tester genetic optimization: it is a trial-count generator with a friendly interface.

Stop-loss orders at fixed distances: uncalibrated interaction with volatility-based sizing. If sizing is correct, stops are redundant; if sizing is wrong, stops do not fix it. `[E]` and I hold this one loosely, since the practitioner literature is genuinely split.

Trading the news, martingale or grid sizing, hedging opposing positions in the same instrument, any strategy requiring sub-second reaction.

### What would change my mind

If Phase 0 shows your measured round-trip costs are materially below my table, more instruments and H4 signals become viable. If the temporal degradation analysis in Phase 3 shows trend performance is flat or improving across blocks, weight the signal more heavily and consider a second signal family. If the meta-labeler clears the gates with a precision improvement above 5 percentage points on held-out folds, it earns permanent status. If FX trend is dead in the last two blocks but index trend is not, the universe should shift toward indices and the FX component becomes a diversifier rather than the core.

---

## First thirty days

Nothing here involves a model.

Log broker-side spread and fill quality on a Dukascopy MT5 demo account, every tick, for twenty trading days, across the eight candidate instruments. Store it.

Download Dukascopy tick history for the same eight from 2010 and compare quote-by-quote against your logged broker feed for the overlapping period. Quantify the divergence. That number is your model risk, and almost nobody measures it.

Run a PCA on daily returns of your candidate universe over the last ten years. Count how many components explain 90% of variance. That number, not eight, is your real breadth.

Build the append-only trial log before you run the first backtest.

Then, and only then, write the momentum baseline.
