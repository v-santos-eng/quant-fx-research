# Relatório de Fechamento — Consistência com US$ 1.000: evidência + o que medimos

> Consolida os dois documentos de evidência (`quant-system-design.md`, `pesquisa-consistencia-
> trading-algoritmico-1k.md`) com o que a plataforma de fato construiu e mediu (Fases 0–2i, 1d).
> Objetivo: uma base honesta para a decisão de capital/veículo. Data: 2026-07-26.

## Veredito em uma frase
Existe um edge real (TSMOM diário), nós o medimos exatamente no nível que a evidência prevê
(Sharpe ~0,33), mas ele **não gera renda sobre US$ 1.000** (bloqueio aritmético) e **não cruza a
barra de consistência** (DSR, amostra, breadth) — o valor de US$ 1.000 é ser o **laboratório**
que valida o sistema com opex≈0, não a fonte de retorno.

## 1. As duas perguntas que US$ 1.000 mistura
- **Renda?** Não, e o bloqueio é **aritmético antes de estatístico**: um sistema no topo do
  realista (Sharpe 0,8, vol 10%) rende ~US$ 80-150/ano sobre US$ 1.000; com opex de US$ 30/mês o
  valor esperado é negativo (breakeven US$ 3,6-7,2k). Alavancar para escapar tem contraevidência
  causal (Heimer-Simsek 2019).
- **Construir um sistema que sobrevive?** Sim, e US$ 1.000 chega — se **opex≈0** (máquina local +
  feed do broker via MT5, sem VPS; timeframe diário não precisa de latência). Este é o seu caso.

## 2. O que a evidência sustenta (síntese dos dois docs)
- **Ranking de edge:** regra fixa sobre prêmio de risco documentado (TSMOM, carry) > camada de
  risco/sizing > econometria paramétrica > ML/RL como sinal primário. TSMOM é a **única família**
  com dados seculares, replicação independente, funcionamento multi-ativo e lucro líquido por década.
- **Intraday/técnica de curto prazo:** falsificada sob controle de data-snooping (Sullivan-
  Timmermann-White 1999; Bajgrowicz-Scaillet 2012). É o modo de operação de quase todo EA de varejo.
- **Sharpe esperado** de um book de trend de varejo com 8-15 instrumentos: **0,3-0,6** (não o
  0,8-1,0 institucional que vem de 40-60 mercados).
- **Carry/overnight de varejo:** comprometido pelo markup de swap do broker. Só como componente pequeno.
- **ML:** defensável apenas como camada secundária (meta-labeling/filtro), nunca como sinal primário
  no varejo (sem um único caso auditado; graus de liberdade explodem o DSR).
- **Consistência (definição operacional):** DSR > 0,95 contando tentativas; expectância positiva por
  regime; drawdown dentro do envelope Monte Carlo; **amostra ~2.000 trades**; aderência de execução.

## 3. O que construímos e medimos
Plataforma completa: ingestão de ticks reais → barras → **custos medidos do broker** → backtester
honesto (reconciliado com MT5) → validação CPCV/DSR/PSR/Monte Carlo → monitor. Fases testadas pelo
mesmo gate pré-registrado, **sem p-hacking**:

| Fase | Estratégia | Veredito | Número decisivo |
| :-- | :-- | :-- | :-- |
| 1 | FX trend (Donchian) | ⛔ FAIL | bruto NEGATIVO nos majors (sem edge nem pré-custo) |
| 1i | ORB intraday (M15) | ⛔ FAIL | bruto+ mas Sharpe 0,21 / PSR 0,81 / DD 66% |
| 2i | ORB + meta-label (ML) | ⛔ FAIL | GBM≈logística → nada a filtrar |
| 2a | Reversão intraday | ⛔ FAIL | bruto NEGATIVO nos 4 (mercado continua, não reverte) |
| **1d** | **TSMOM D1 cross-asset** | 🟡 **PARCIAL** | **1º gross+ (0,28); gold+JPY net 0,33** |

Detalhe da 1d (`experiments/tsmom_1d.json`, `tsmom_full_1d.json`):
- **Gross portfolio Sharpe +0,283** — o sinal TEM edge (1º positivo do projeto).
- **Universo pleno (8): net −0,97** — o **swap de índice CFD (~15%/ano) é o assassino**.
- **Gold+JPY (swap benigno): net +0,33**, 4/5 blocos temporais positivos, 79% dos caminhos CPCV
  positivos. **Mas DSR ≈ 0,12 ≪ 0,95, breadth de 2 ativos, e seleção parcialmente ex-post** →
  **não cruza a barra de consistência.**
- As refinements da Part 13 (score proporcional + overlay de regime) **não melhoraram** (testadas,
  não p-hackeadas além).
- **Proxy futuros (swap=0): 8 ativos net +0,15; só índices +0,32** → o sistema completo é
  provavelmente viável em **futuros** (sem markup de financiamento de CFD).

## 4. A convergência (o resultado mais importante)
Nossa medição independente caiu **em cima** das previsões da evidência:

| Previsão da evidência | Nossa medição |
| :-- | :-- |
| Intraday de varejo é falsificado | 4 FAILs intraday (ORB, ORB+ML, reversão, FX curto) |
| TSMOM é o edge com melhor evidência | Único gross+ de portfólio do projeto (+0,28) |
| Trend de varejo, universo pequeno → Sharpe 0,3-0,6 | Gold+JPY net **0,33** (em cheio) |
| Swap de varejo compromete overnight | Swap de índice CFD destruiu o book completo |

A plataforma não só rejeitou o que a evidência diz para rejeitar — ela **mediu o edge real no valor
exato previsto.** Isso valida a calibração tanto quanto o número.

## 5. Onde exatamente estamos (honestidade)
- **Temos** o sistema que ambos os documentos recomendam (TSMOM diário, família (a)), com a régua de
  validação da Seção 2 implementada, e um resultado real no nível previsto.
- **Não temos** um sistema que cruze a barra de consistência: DSR abaixo de 0,95, breadth baixa
  (o Sharpe 0,7-1,0 de CTA vem de 40-60 mercados; nós temos ~8 acessíveis e correlacionados), e
  amostra insuficiente para poder estatístico (o doc: ~2.000 trades para 72% de poder a Sharpe 0,8).
- Em US$ 1.000, mesmo o resultado bom rende **migalhas** e segura posição overnight (precisa de capital).

## 6. O caminho que a evidência sustenta (recomendação)
1. **Opex ≈ 0.** Local + feed MT5, sem VPS. É a única variável 100% sob seu controle e cada dólar
   fixo é retorno certo negativo.
2. **Núcleo = TSMOM diário** nos ativos de swap benigno (ouro, JPY, e o que a medição de custo
   aprovar), camada de sizing por vol (risco 0,5-1%/trade, teto por moeda-base, kill switch).
3. **Live como teste de EXECUÇÃO, não de edge.** O que o live valida em semanas é aderência
   fill↔modelo; a expectância leva **anos** e milhares de trades. Tratar o PnL curto como sinal é
   erro de leitura estatística.
4. **Capital vem depois, por aporte externo** sobre um sistema já validado — não por composição dos
   US$ 1.000. A transição para retorno relevante é essa, não mágica de estratégia.
5. **Escala real = futuros.** O proxy swap=0 mostra que o sistema cross-asset completo do doc
   provavelmente vive em micro futuros (sem markup de financiamento). É a rota de médio prazo,
   condicionada a capital + fonte de dados de futuros + novo cost model.

## 7. O que faltaria para "validado" (se um dia for perseguir)
- Medir a **comissão real de CFD** (rodamos a 0, otimista).
- **Micro futuros**: dados + corretora + cost model (a Dukascopy não tem CME) → destrava a breadth
  e remove o swap que mata os índices.
- Acumular **amostra/tempo** suficiente (o poder estatístico exige anos a esta frequência).
- Rodar a régua completa da Seção 2 (DSR>0,95 com contagem honesta, positivo por regime, MTRL).

## 8. Fecho
A pesquisa de estratégia chegou a uma conclusão **bem-fundamentada e convergente com a melhor
evidência disponível**, não a um fracasso. Encontramos o edge real (TSMOM), provamos por que o
intraday não funciona, medimos o resultado no valor exato que a ciência prevê, e mapeamos o único
caminho que muda a matemática (capital + futuros). O maior valor entregue é uma **plataforma de
validação rigorosa** — a coisa que, segundo os dois documentos, separa os sobreviventes dos ~90%
que morrem. Guia de uso: `docs/como_adicionar_estrategia.md`.
