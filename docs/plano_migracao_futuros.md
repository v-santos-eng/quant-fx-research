# Plano de migração para micro futuros (Caminho 1)

> Rota da plataforma atual (Dukascopy CFD/FX + MT5) para **trend-following cross-asset em micro
> futuros CME**, timeframe diário, o veículo que a evidência sustenta e que o nosso proxy swap=0
> indicou viável. Reaproveita a engine de sinal (`tsmom.py`), a validação (CPCV/DSR/MC) e a
> metodologia de gates. Troca o que futuros exigem: fonte de dados, roll de contrato, cost model,
> sizing discreto e a camada de execução. Contexto: `docs/relatorio_final.md`.
>
> **Não é aconselhamento de investimento, é um plano de engenharia/pesquisa.** Envolve custos
> (dados, corretora) e capital; a decisão e o risco são do usuário.

## Por que futuros (recap de 1 linha)
CFD retail cobra **markup de swap** (~15%/ano nos índices) que matou o edge; futuros embutem o
carry justo no roll (**sem markup**), têm volume real e **breadth cross-asset**, a diversificação
que eleva o Sharpe de 0,3-0,6 (universo pequeno) para 0,6-1,0 (40-60 mercados).

## Acoplamento honesto: o que EXIGE capital em futuros (correção)
**Não é o dado.** Preço histórico bruto é obtível de graça (API do IB com conta; Barchart tier
grátis; yfinance front-month). O que se paga (Norgate ~US$ 35/mo) é a ENGENHARIA, contínuo com
roll correto, back-adjustment, contratos vencidos (sem survivorship bias). Como **construímos o
builder de roll de qualquer forma (F1)**, dá para alimentá-lo com dado grátis e rodar a
**pesquisa (F0-F3) com opex ≈ zero** (troca assinatura por trabalho + validação de qualidade).
Real-time do CME tem taxa pequena e muitas vezes dispensável a diário (delayed/EOD grátis).

**O que de fato exige capital é a GRANULARIDADE DISCRETA:** não se compra fração de micro contrato.
Um book de ~20 mercados a 1 contrato cada, com vol-targeting não destruído pelo arredondamento,
+ margem + sobreviver a drawdown de 20-30%, aterrissa em **~US$ 10-25k**, independente do custo
de dados. **A pesquisa roda antes, sem risco de capital; o capital só é necessário para operar.**

## Decisões a fechar antes de começar (com recomendação)
| Decisão | Recomendação | Alternativas / nota |
| :-- | :-- | :-- |
| **Fonte de dados** | **Pesquisa: DIY grátis** (API do IB / Barchart tier grátis) + nosso builder de roll (F1) → opex≈0. **Conveniência: Norgate** (~US$ 35/mo) se quiser pular a engenharia | Databento (tick, pay-per-use); yfinance p/ 1ª exploração |
| **Corretora/venue** | **Interactive Brokers** (acesso global inclusive do Brasil, API madura, micros CME) | Tradovate (foco micros, API REST/WS); AMP/Rithmic |
| **Universo inicial** | ~20-25 micros/minis em 5-6 setores (abaixo) | começar menor (10-12) e expandir |
| **Acesso local** | CME via IB | B3 tem minis (WIN índice, WDO dólar) mas só 2 mercados → breadth insuficiente p/ o núcleo |

**Universo-alvo (breadth cross-asset):** índices MES/MNQ/MYM/M2K; metais MGC/SIL/MHG; energia
MCL (+ gás); FX M6E/M6A/M6B/MJY; juros ZF/ZN/ZB (ou micro-yield 2/5/10/30Y); grãos ZC/ZS/ZW.
→ ~20-30 mercados em índices, juros, metais, energia, FX e agrícolas.

## Fases e gates (mesma disciplina do projeto)

### F0: Fundação de dados (o gargalo real). ~2-3 semanas
- **Deliverable:** conta de dados; contínuos back-adjusted dos ~20-25 alvos baixados; tabela de
  **specs de contrato** (tick size/value, multiplicador, horário, calendário de vencimento, margem).
- **Gate:** ≥20 mercados carregados; specs conferidos contra o site do CME; preços batem níveis
  históricos reais (mesmo smoke test que fizemos nos CFDs).

### F1: Contínuos e roll (infra NOVA crítica). ~2 semanas
- Validar o builder de série contínua: **regra de roll** (por volume/open interest) e
  **back-adjustment** (ratio p/ retornos). Norgate entrega, mas **auditar**.
- Modelar o **custo do roll** (cada roll = 1 spread + comissão em 2 pernas).
- **Gate:** os retornos da série contínua reproduzem os retornos reais intra-contrato (reconciliação
  da emenda); **zero look-ahead** no roll (a decisão de rolar usa só dados até o dia).

### F2: Cost model de futuros. ~1 semana
- **Comissão por contrato** (medir do broker: ~US$ 0,25-0,75/lado nos micros + fees exchange/NFA);
  spread (tipicamente 1 tick); slippage modelado + stress ×2; custo de roll.
- **Swap = 0** (não existe; carry no roll). O cost model **simplifica** vs CFD.
- **Gate:** custo round-trip por mercado documentado com banda; sanity all-in contra tabela do broker.

### F3: Baseline TSMOM cross-asset no gate (O TESTE QUE DECIDE). ~2 semanas
- Rodar a engine `tsmom.py` (**já pronta**) sobre os ~20-25 futuros, custo de futuros, vol-targeting
  de portfólio, no **gate completo**: Sharpe líq, PSR, CPCV, **DSR > 0,95 com contagem honesta**,
  MC de drawdown, expectância positiva por regime, ≥4/5 blocos temporais, net ≥ 60% do gross,
  sobrevive a custo ×2.
- **Se cruzar** (o proxy swap=0 deu +0,15 nos 8 e +0,32 nos índices → plausível com breadth real):
  você tem o **primeiro sistema validado** do projeto. **Se não cruzar: PARA, honestamente.**
- **Gate:** os 6 critérios de consistência do `relatorio_final.md` §7.

### F4: Sizing discreto + construção de portfólio. ~1-2 semanas
- Vol-targeting com **arredondamento para contratos inteiros**; medir a distorção de granularidade
  vs capital; fixar o **capital mínimo** onde a distorção é tolerável (estimativa ~US$ 10-25k).
- Teto de risco por setor, correlação-ajustado, kill switch, limite diário.
- **Gate:** vol realizada no backtest dentro de ±25% do alvo; drawdown não piora por granularidade.

### F5: Execução (substitui o EA MT5). ~3-4 semanas
- **Adapter fino** para o broker (IB API / Tradovate): recebe posições-alvo, reconcilia posição,
  coloca/gerencia ordens, heartbeat, limites locais. Mesmo conceito do EA, nova implementação.
- **Reconciliação nova (R-01 no novo venue):** backtest vs conta paper do broker.
- **Gate:** tracking error sinal-gerado vs backtest < 5%; zero drift de posição não reconciliado;
  handoff atômico de sinais (write-temp-rename).

### F6: Paper trading. 6 meses (inegociável)
- Stack completo contra conta **paper/demo de futuros**. Aderência: fills, slippage, **roll real**,
  fees dentro do modelado. Passa por vencimentos, rollovers, fim de trimestre, DST.
- **Gate:** tracking < 5%; custo realizado por trade na banda da F2; uptime do heartbeat > 99%;
  zero evento de posição não reconciliado nos últimos 60 dias.

### F7: Capital mínimo real → escala. 6+ meses
- Micro contratos, capital onde a granularidade funciona (~US$ 10-25k). Escala por **aporte** após
  meses sem incidente operacional e com vol realizada na banda. **Nunca sem humano no loop.**

## O que REAPROVEITA (nada se perde)
- **Sinal:** `research/tsmom.py` (score multi-horizonte, inverse-vol, banda de drift, overlay de regime).
- **Validação:** `validation.py` (PSR/DSR), `cv.py` (CPCV), `montecarlo.py`, a régua inteira.
- **Metodologia:** gates pré-registrados, attempt log p/ DSR, monitor operacional, `docs/como_adicionar_estrategia.md`.
- **Portfólio:** vol-targeting/inverse-vol, caps de risco.

## O que é NOVO (o trabalho da migração)
- Aquisição de dados de futuros + **builder de contínuo/roll** (F0-F1), a peça nova mais crítica.
- Tabela de specs de contrato + **cost model de futuros** (swap fora, comissão/roll dentro) (F2).
- **Sizing por contratos inteiros** (F4).
- **Adapter de execução** para IB/Tradovate + nova reconciliação (F5), substitui o EA MT5.

## Riscos e armadilhas específicas de futuros
- **Erro de roll/back-adjustment** = backtest lindo e falso (o análogo do look-ahead). Auditar em F1.
- **Granularidade discreta** distorce o portfólio em capital baixo, é o que fixa o piso de capital.
- **Custo de roll acumulado** em muitos mercados pode surpreender, modelar em F2, não assumir.
- **Opex de dados** reintroduz o breakeven, só faz sentido com capital suficiente.
- **Sobrevivência a vencimento/expiry** e mudança de contrato: o adapter tem de rolar posição viva.

## Primeiro passo concreto
Fechar as 3 decisões (dados, corretora, universo). Com isso, **F0-F3 são pura pesquisa, sem risco
de capital**, e a F3 responde, de forma honesta e barata, a única pergunta que importa: **o
trend cross-asset em futuros cruza o gate?** Só depois disso vale investir em execução e capital.
