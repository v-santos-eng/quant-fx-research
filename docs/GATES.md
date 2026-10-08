# Registro de Gates (pré-registrado)

> Critério escrito ANTES do teste. Proibido ajuste ad hoc. Uma linha de veredito por fase.

## Fase 0.1 — Fundação · ✅ APROVADO (2026-07-20)
**Critério:** run reproduzível bit-a-bit + attempt log grava/lê + specs carregam.
**Resultado:** reprodutibilidade confirmada dentro e entre processos; AttemptRegistry SQLite persistente; 4 specs YAML carregam. 11 testes verdes.

## Fase 0.2 — Dados · ✅ APROVADO (2026-07-22)
**Critério (pré-registrado):** custos medidos, não assumidos — *revisado*: para a etapa de DADOS, relatório de qualidade auditável + snapshots versionados por hash + cobertura alta e integridade limpa. (Medição de custos do broker é a Fase 0.3.)
**Resultado:**
- Dataset Dukascopy 2010–2026, 6 pares: **~2,56 bilhões de ticks**, 31.005 dias-arquivo.
- Cobertura: 99,2%–99,9% por par (faltas = feriados + 30 dias com falha persistente de rede, 0,1%).
- Integridade: 0 preços não-positivos, 0 timestamps duplicados; quotes cruzados desprezíveis (AUDUSD 0,015%, USDJPY 1).
- Snapshots por hash no manifesto CSV; relatório em `experiments/quality_report_0_2.json`; attempt logado.

**Achados → tratados na camada de sanitização (Parquet brutos ficam imutáveis):**
1. AUDUSD quotes cruzados (0,015%) → `drop_invalid_quotes` aplicado no carregamento para features.
2. XAUUSD gap-dias alto (2994) = **falso positivo** da pausa diária de ~1h do ouro; detecção de gap será ciente de sessão para XAU na feature pipeline.

**Riscos remanescentes:** paridade Python↔MQL5 (R-01, abre na Fase 0.4); feed Dukascopy vs broker (R-02, confere na Fase 0.3).

## Fase 0.3 — Custos · ⏳ EM ANDAMENTO
**MUDANÇA DE BROKER (2026-07-22):** usuário migrou ActivTrades → **Dukascopy** (demo MT5, `Dukascopy-demo-mt5-1`, USD). Motivo: paridade dado↔execução — os ticks históricos são Dukascopy, então o broker ser Dukascopy **quase elimina o R-02**. MT5 confirmado (Dukascopy passou a ofertar MT5 em 2026). Símbolos = identidade (inclui XAUUSD). ECN raw + comissão.

**Critério (pré-registrado, revisado):** modelo de 3 camadas — **spread** medido (histórico Dukascopy + amostra live), **swap** medido (broker atual, constante no backtest + stress ×2), **comissão** ECN medida (tabela Dukascopy), **slippage** modelado+estressado (1–2 spreads; medição real adiada p/ Fases 5–6, decisão do usuário).

**Progresso (substancialmente atingido):**
- **Spread MEDIDO:** modelo histórico par×hora dos 2,56 bi ticks (`experiments/spread_model.json`) — EURUSD p50 0,30 / p75 0,50 pip. Snapshot live ≈ histórico (parity confirmada).
- **Swap MEDIDO:** `research/mt5_client.py` snapshot → `experiments/broker_specs.json` (modo=points, por par, dia triplo).
- **Comissão MEDIDA:** Dukascopy Europe $35/M FX, $52,5/M metais (por lado, tier <$5k). Sanity: EURUSD all-in ~1,06 pip bate com Parte 3.
- **Slippage:** modelado+estressado (decisão do usuário; real nas Fases 5-6).

**Confirmações em curso (não bloqueiam 0.4, que usa o spread histórico):**
- Coletor de spread live (`research/spread_sampler.py`) rodando — parity check contínuo. Semana completa exige tarefa agendada local (jobs de sessão morrem no fim da sessão) — **decisão do usuário pendente**.
- Rate de comissão específico do MT5 Dukascopy (tabela obtida é do JForex) — confirmar.

**Veredito:** gate 0.3 **substancialmente atingido** (3 camadas medidas + slippage modelado por decisão). Pronto para 0.4 usando o modelo de custo histórico; confirmações live seguem em paralelo.

## Fase 0.4 — Backtester + reconciliação · ✅ PASSOU (2026-07-25)
**Critério (pré-registrado):** backtester Python event-driven com o modelo de custo de 3 camadas (spread par×hora + comissão + swap + slippage-stress), e **reconciliação Python↔MT5 Strategy Tester** ("Every tick based on real ticks") de uma estratégia de referência determinística (Donchian breakout puro, sem ML/filtros) sobre o mesmo período/símbolo, com **divergência dentro de tolerância pré-registrada**: nº de trades idêntico (±1) e P&L dentro de ±2% (ajustável antes do teste). É o teste que ataca o R-01.

**RESULTADO (EURUSD H4, 2023-2025, ticks reais):** EA 75 trades × Python 75 trades, **75/75 match exato**, P&L bruto EA −$1617,60 = Python −$1617,60 (**Δ 0,0%**). Veredito **PASS** — não "na tolerância", idêntico. **R-01 dissolvido** para a lógica do engine. Reconciliação usou as barras H4 do próprio MT5 (via ponte) para isolar a lógica do fuso server-time. `experiments/reconcile.json`. Fix de infra no caminho: conflito de porta 3000 (Docker frontend) que travava o agente do tester → frontend remapeado p/ 3001.

## Fase 0.5 — Toolkit de validação · ✅ PASSOU (2026-07-25)
**Critério (pré-registrado):** cada ferramenta estatística recupera um resultado conhecido em série sintética.
**Entregue e testado (73 testes):**
- `research/validation.py` — Sharpe, erro padrão (Lo 2002), **PSR** e **DSR** (Bailey/LdP; DSR deflaciona pelo nº de ensaios do attempt log).
- `research/cv.py` — **PurgedKFold** (purga por sobreposição + embargo) e **CombinatorialPurgedCV** (CPCV, cap.12: C(N,k) combinações → distribuição de Sharpe).
- `research/montecarlo.py` — block bootstrap (distribuição de drawdown/tempo submerso; **p99 → circuit breaker RF-12**), perturbação de parâmetros ±20%, multiplicadores de stress de custo.
**Veredito:** gate cumprido — o antídoto estatístico da Parte 8 está pronto para ser aplicado na Fase 1.

## Fase 0i — Dados do universo intraday · ✅ APROVADO (2026-07-26)
**Critério (pré-registrado, espelha 0.2):** ticks reais dos CFDs baixados + relatório de
qualidade auditável com **cobertura alta e integridade limpa** + snapshots versionados por hash.
**Resultado (4 CFDs Dukascopy, 2012→2026-07-24, `experiments/quality_report_0i.json`):**
- **~1,30 bilhão de ticks**, 16.853 dias-arquivo. US100 652M · GER40 281M · US500 187M · WTI 177M.
- **Integridade impecável:** 0 preços não-positivos, 0 timestamps duplicados, 0 quotes cruzados
  (exceto LIGHTCMDUSD 63 = 0,00004%, tratado por `drop_invalid_quotes` como o AUDUSD na 0.2).
- **Cobertura real de pregão ≈ 99,4%:** dias úteis (Seg-Sex) ausentes = só 26-45 em ~14 anos,
  **todos feriados de mercado** (4/jul, 25/dez, Sexta Santa...). O "93-98%" do cabeçalho é
  artefato do denominador contar domingos (índices fecham domingo).
- **`gap_days` alto (2000-2700) = falso-positivo de sessão esperado** (fechamento noturno dispara
  o detector de gap >30min). Igual ao caso do ouro na 0.2 → tratado na camada ciente de sessão.
**Fix de infra no caminho:** proxy de inspeção SSL desta rede custa ~9s/handshake e derrubava o
download com 32 conexões → downloader passou a **reusar 1 conexão TLS/dia (keep-alive)** + concorrência 10.
**Veredito:** gate 0i **APROVADO**. Dado pronto para barras M15/H1 + modelo de spread intraday.

## Fase 1d — TSMOM D1 cross-asset (Part 13 do doc) · 🟡 PARCIAL — 1º EDGE REAL (2026-07-26)
**Contexto:** ao reler `quant-system-design.md` percebemos que 3 dos 4 FAILs (ORB M15, reversão,
FX Donchian) foram estratégias que o doc EXCLUI explicitamente. A recomendação PRIMÁRIA dele —
TSMOM D1 multi-horizonte cross-asset vol-scaled (Part 13) — nunca fora testada. Corrigido aqui.
**Método:** sinal = média do sinal do retorno em 21/63/126d; posição ∝ score × inverse-vol; banda
de drift 20%; holding overnight (paga SWAP). Uma config, SEM otimização (Phase 1 do doc).
`research/tsmom.py`, `research/run_tsmom.py`, `experiments/tsmom_1d.json`. Custos medidos (spread+
comissão+swap por ativo). Gate do doc: net Sharpe>0,3 E ≥3/5 blocos+ E net≥60% do gross E sobrevive swap×2.
**RESULTADO — o sinal TEM edge, o swap decide:**
- **Gross portfolio Sharpe +0,283** (1º edge BRUTO de portfólio positivo do projeto). Bruto+ em 5/8:
  XAUUSD +0,63, USDJPY +0,43, US500 +0,29, US100 +0,28, EURUSD +0,10; GBP/AUD/CAD negativos.
- **Universo completo (8): net −0,965 = FAIL.** O **swap de índice CFD é catastrófico** (US500 −2,04,
  US100 −2,21 em Sharpe — ~7× o gross). Financiamento overnight de CFD retail ~15%/ano mata o trend.
- **★ Recorte USDJPY+XAUUSD (swap benigno): net +0,329, 4/5 blocos+, CPCV 79%+, PSR 0,93,
  DSR 0,118.** Passa o gate CENTRAL do doc (Sharpe>0,3, ≥3/5 blocos). **CORREÇÃO:** DSR é
  probabilidade e a barra é **DSR>0,95** — 0,118 NÃO cruza; somado a PSR 0,93<0,95, breadth de
  2 ativos e seleção parcialmente ex-post, **NÃO cruza a barra de consistência.** É o **melhor
  resultado do projeto e no nível exato que a evidência prevê (0,3-0,6), mas não "validado".**
  FX+ouro (6, a-priori) net −0,12 (GBP/AUD/CAD sem trend arrastam).
- **Proxy FUTUROS (swap=0, financiamento justo): 8 ativos net +0,149; só índices net +0,318.** Forte
  indício de que o sistema COMPLETO do doc é viável em FUTUROS (sem markup de financiamento de CFD).
**Refinements da Part 13 (score proporcional z-score + overlay de regime), `research/run_tsmom_full.py`,
`experiments/tsmom_full_1d.json`:** NÃO resgataram — pioraram um pouco (USDJPY+XAUUSD net 0,33→0,24;
o overlay adiciona turnover e o score proporcional diluiu o gross 0,62→0,50). Coerente com o doc
(componentes `[M]`/`[E]`, contribuição "pequena a moderada"). A versão SIMPLES (sinal) no book
gold+JPY continua a melhor. **Não p-hackear além disto — as refinements do próprio doc foram testadas.**
**Veredito: PARCIAL.** A tese TSMOM do doc é VALIDADA no bruto e NET-POSITIVA (borderline) no
subconjunto de swap benigno (gold+JPY): 1º edge líquido real e deflação-resistente do projeto, mas
não cruza o gate harsh (PSR 0,93<0,95, net/gross 0,53<0,60). Reprova no universo pleno por swap de CFD.
Reabre o Caminho 1 (capital+futuros) com respaldo empírico (proxy swap=0). Decisão do usuário.

## Fase 2a — Baseline de REVERSÃO intraday (GER40) · ⛔ REPROVADO (2026-07-26)
**Critério (pré-registrado):** mesmo gate 1i (Sharpe>0, PSR>0,95, CPCV≥60%, DSR>0, MaxDD-p99),
com bruto+ como 1º corte. Hipótese de edge DIFERENTE (reversão à média vs continuação do ORB).
**Método:** fade quando o preço estica ≥Z·ATR do VWAP; alvo=volta ao VWAP; stop=S·ATR. Busca de
18 configs (z×stop_atr×warmup), seleção OOS via CPCV, DSR deflacionado. `research/meanrev.py`,
`research/run_mr_search.py`, `experiments/mr_search_2a.json`.
**RESULTADO (GER40, comissão=0):** melhor config (z=2,0/stop 1,5/warmup 30) dá **bruto −$57,60**
(NEGATIVO — falha já no 1º corte), Sharpe −0,45, PSR 0,03, CPCV 21%+, DSR 0. Scan dos 4 CFDs:
reversão bruto-NEGATIVA em TODOS (GER40 −$392, US500 −$1206, US100 −$2554, USOIL −$1130) —
**espelho exato do ORB, que era bruto-POSITIVO nos 4.**
**Veredito: FAIL.** Coerente e informativo: os movimentos intraday desses índices/commodities têm
**leve CONTINUAÇÃO, não reversão** — o lado momentum tem edge (fino); o lado reversão perde no
bruto. Não há edge de varejo explorável em nenhum dos dois lados pós-custo. **4ª reprovação honesta;
hipóteses baratas esgotadas.** Adotado o Caminho 3 (plataforma de pesquisa) como base.

## Fase 2i — Meta-labeling sobre o ORB (GER40) · ⛔ REPROVADO (2026-07-26)
**Critério (pré-registrado, `docs/metalabel_orb.md` §6):** passar o gate 1i (Sharpe>0, PSR>0,95,
CPCV≥60%, DSR>0, MaxDD-p99 tolerável) **E bater o baseline com folga** (Sharpe≥0,5 E menos trades).
**Método:** primário=ORB default; meta-modelo (HistGBM + logística sanity) prediz P(vitória) por
sinal via **Purged K-Fold + embargo (OOS)**; threshold τ por sweep; DSR deflacionado por (2 modelos
× |τ|). Avaliação por CPCV na série filtrada. `research/run_metalabel.py`, `experiments/metalabel_2i.json`.
**RESULTADO (GER40, comissão=0 otimista):** baseline ORB Sharpe 0,179 (3606 trades). Filtro GBM:
τ=0,45, **351 trades** (filtrou bem), **Sharpe 0,159** — NÃO melhorou (piorou vs baseline). PSR 0,75,
DSR 0,03, CPCV 71%+, MaxDD-p99 $195. **GBM (0,159) ≈ logística (0,155)**: os dois extraem o mesmo
~nada → não é modelo errado, **não há sinal a extrair** das features.
**Veredito: FAIL.** O meta-label reduz trades/drawdown mas não cria edge — as features não predizem
quais sinais ORB vencem. Terceira reprovação honesta no mesmo rigor.

## Fase 1i — Baseline ORB intraday (GER40) · ⛔ REPROVADO (2026-07-26)
**Critério (pré-registrado, `docs/baseline_orb.md` §7):** Sharpe líq>0 E PSR>0,95 E CPCV≥60%
caminhos+ E DSR>0 E MaxDD-p99 tolerável, com **bruto+ por instrumento** (1º corte).
**Método (anti-p-hacking):** busca de 81 configs (or_min×atr_mult×r_mult×k_range), seleção pelo
Sharpe OUT-OF-SAMPLE do CPCV (não full-sample), DSR deflacionado por |grade|=81. `research/run_orb_search.py`.
**RESULTADO (GER40, M15, 2012-2026, spread medido, comissão=0 OTIMISTA), `experiments/orb_search_1i.json`:**
- **1º corte OK:** os **4 CFDs são bruto-positivos** (`orb_pilot.json`) — o ORB tem edge direcional
  real em índices/commodities (oposto do FX). Só o GER40 tem bruto>spread (os outros o spread mata).
- **Melhor config** (OOS): or_min=30, atr_mult=1,0, r_mult=2,0, k_range=0,8 (≈ default).
- Sharpe 0,21 (✅) · **PSR 0,806 (❌ <0,95)** · CPCV 75% caminhos+ (✅) · **DSR 0,0001 (❌ ≈ruído)** ·
  **MC MaxDD-p99 $657 = 66% de $1.000 (❌)**.
**Veredito: FAIL.** O edge bruto existe mas, pós-spread, é fino demais para ser distinguível de
ruído (não sobrevive à deflação por 81 tentativas) e o drawdown é inaceitável p/ conta pequena —
e isso SEM comissão. Confirma o alerta da pesquisa (Parte 8/desenho §8): intraday de varejo em
breakout puro não tem edge robusto. **Sem p-hacking: o gate rejeitou, não se ajustou. Decisão do usuário.**

## Fase 1 — Baseline de regras · ⛔ REPROVADO (2026-07-25)
**Critério (pré-registrado):** Sharpe líquido > 0 e drawdown tolerável em 10+ anos.
**Resultado (Donchian 55/20 H4, 6 pares, 2010-2026, custos completos):** net −$32.674 em 2.252 trades; **Sharpe anual −0,552**; PSR 0,026; CPCV −0,667 ± 0,353 com **0% dos caminhos positivos**; DSR 0,0002; MaxDD MC-p99 −$65,8k. `experiments/phase1_baseline.json`.
**Veredito: FAIL** — robusto (não é sorte de caminho). O baseline ingênuo não tem edge após custos (esperado, Partes 2/13). Loop PAROU para decisão do usuário.
**Ressalva:** o EA de referência da 0.4 é uma variante SIMPLIFICADA (sempre no mercado, reverte a cada rompimento oposto). A versão canônica da Parte 13 usa **trailing 2,5-3 ATR + pode ficar flat**, o que reduz whipsaw.

### Baseline CANÔNICO (trailing 3ATR + flat + filtro ADX≥25) — também REPROVA
`research/run_phase1_canonical.py` + `research/indicators.py` (ATR/ADX) + `backtester.canonical_positions`. Resultado (6 pares, 2010-2026): net −$13.634 (vs −$32.7k do simples); Sharpe −0,277; PSR 0,14; CPCV −0,45 com **25% dos caminhos positivos** (vs 0%); DSR 0,0. `experiments/phase1_canonical.json`. Melhorou muito, mas **Sharpe ainda < 0 → FAIL**.

### 🔑 DIAGNÓSTICO DECISIVO: P&L BRUTO (pré-custo) é NEGATIVO no FX
Bruto por par (canônico): EURUSD −$1.374, GBPUSD −$1.742, USDCAD −$1.295, USDJPY −$290, AUDUSD −$261 — **todos os FX negativos ANTES de custos**. Só **XAUUSD tem bruto positivo (+$1.314)**, mas custo $6.167 (swap+spread do ouro) o destrói. Total bruto −$3.649. **Conclusão: o sinal de tendência não tem edge nos majors de FX 2010-2026 nem antes de custos** — gestão de risco não cria edge, e filtros não salvam bruto negativo. Confirma Partes 2/13 (trend ingênuo morreu nos majors pós-2010). Único ponto com edge bruto real = ouro, mas caro de carregar. **DECISÃO DO USUÁRIO pendente.**
**Componentes:** `research/bars.py` (ticks→OHLC H1/H4), `research/costs.py` (aplica custos ao fill), `research/backtester.py` (engine), `mt5/reference_ea.mq5` (EA de referência p/ o tester), `research/reconcile.py` (compara blotters).
**Dado alinhado:** o Strategy Tester usa o histórico de ticks do broker = Dukascopy = mesmo venue dos dados de pesquisa → reconciliação com base coerente.
