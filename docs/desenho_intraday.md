# Desenho intraday para conta pequena (~$1.000) — documento de discussão

> Reformulação do projeto para a realidade real do usuário: **daytrading, conta pequena,
> uma posição por vez, sem overnight**. Nada implementado — é desenho para decisão.
> O que muda é o ALVO (instrumentos, timeframe, custo). A infraestrutura (dados tick →
> barras → backtester → validação CPCV/DSR/MC) é reaproveitada inteira.

## 1. As restrições que definem tudo
| Restrição | Consequência de projeto |
| :-- | :-- |
| Capital ~$1.000 | **1 posição por vez**, micro lote (0,01). Sem portfólio simultâneo. |
| Não pode perder | Risco por trade baixo ($5–10), limite de perda diário duro, stop sempre. |
| Segura ~1 posição por poucos dias | **Sem overnight** → elimina swap (o custo que matou o edge do ouro). |
| Varejo, não institucional | Custo por trade é o rei; frequência × custo é o teto do sistema. |

**Decisão estrutural nº 1: FECHAR TODA POSIÇÃO NO MESMO DIA (antes do rollover ~21:00 UTC).**
Isso zera swap e o risco de gap noturno. É o que torna daytrading viável para $1.000.

## 2. Instrumentos — o critério muda (e não é só ouro)
Sem swap, o que decide é **movimento intraday ÷ custo por trade** (spread + comissão).
Quanto do range de um dia você precisa capturar só para empatar. Candidatos:

| Instrumento | Range intraday típico | Custo round-trip (0,01) | Breakeven | Veredito intraday |
| :-- | :-- | :-- | :-- | :-- |
| **XAUUSD (ouro)** | $25–45 | ~$0,70 | ~7 pts ($0,07/oz) | **Forte**: melhor mov/custo, tendência intraday real |
| **US100 (Nasdaq CFD)** | 150–400 pts | ~1–2 pts | baixo | **Forte candidato**: tendência de sessão limpa (abertura NY) |
| **US500 (S&P CFD)** | 30–70 pts | ~0,5–1 pt | baixo | Bom, menos volátil que US100 |
| **GER40 (DAX CFD)** | 150–350 pts | ~1–2 pts | baixo | Bom: tendência na abertura de Frankfurt/Londres |
| EURUSD / majors | 60–110 pips/dia, ~13/h | ~1,5 pip | ~12% do mov/h | **Marginal**: spread come o movimento intraday (a pesquisa alerta) |
| GBPJPY / crosses vol. | grande | spread largo + caudas | alto | Evitar: caudas e slippage |
| BTC / crypto CFD | enorme, 24/7 | spread largo | alto | Fora: risco e custo extremos |

**Leitura:** os melhores veículos de daytrading para varejo **não são o FX** — são **ouro e índices** (US100, US500, GER40). Eles têm tendências de **sessão** limpas (a abertura de NY/Londres gera momentum direcional real) e movimento grande contra spread pequeno. O FX majors, que era a estrela do desenho swing, vira **marginal** no intraday (a Parte 4 já dizia: o spread come o movimento pequeno).

**Portfólio intraday proposto:** ouro + 2–3 índices (US100, US500, GER40). Uma posição por vez entre eles (o que der sinal primeiro na sessão), respeitando o capital.

**Lacuna de dados:** temos ticks Dukascopy de 6 FX+ouro. **Índices exigem baixar dados novos** (Dukascopy tem os CFDs; a demo MT5 lista 418 símbolos). Fase 0 dos índices a refazer.

## 3. Timeframe
- **Sinal em H1** (a pesquisa: menor TF viável; no ouro/índices a relação custo/mov é boa).
- **Refino de entrada em M15**, gestão de stop intraday.
- **Janela de operação = sessões líquidas** (Londres + NY, ~07:00–20:00 UTC). Fora disso o spread abre e o movimento seca.
- **Corte duro antes do rollover** (fecha tudo ~20:45 UTC).

## 4. Custos — redesenhados para intraday
- **Sem swap.** Some a camada que dominava o P&L no swing.
- **Spread por hora vira o custo decisivo** — e varia muito por sessão. Regra: operar só nas horas de spread baixo (percentil baixo do histórico daquela hora). Já temos `spread_model.json` por par×hora para FX/ouro; refazer para índices.
- **Comissão × frequência é o novo teto.** Intraday = mais trades = paga spread+comissão muitas vezes. **Este é o risco nº 1**: mesmo um edge real morre se a frequência for alta demais. O modelo de custo tem que exigir edge por trade **com folga** sobre o custo.
- Slippage: medido nas Fases 5–6 (demo/live), estressado antes.

## 5. Família de sinal (o que tem evidência intraday)
Ordem de prioridade por evidência/aderência ao intraday de sessão:
1. **Opening-Range Breakout (ORB) / momentum de sessão** — o range da 1ª hora da sessão rompe e o movimento continua. É o fenômeno intraday mais documentado (liquidez e ordens agrupadas na abertura; base microestrutural em Osler). Forte em índices na abertura de NY e no ouro em Londres/NY.
2. **Breakout de canal intraday (Donchian curto em H1/M15)** — mesma família do que já temos, portada para intraday, fechando no dia.
3. **Expansão de volatilidade** — após compressão (ATR baixo em percentil), operar a expansão. Bom filtro combinado com (1).

Todos **determinísticos e testáveis** — nada de discricionário. O núcleo continua sendo uma regra transparente; ML (meta-label) só se vencer o baseline, como antes.

## 6. Risco e sizing para $1.000
- **1 posição por vez** (o capital força concentração — assumir isso explicitamente).
- **Micro lote 0,01** (ou fracionário se o broker permitir).
- **Risco por trade 0,5–1%** ($5–10) via stop intraday em ATR (ATR de H1/M15, não diário).
- **Limite de perda diário duro** (ex.: −3% do dia → para de operar até o dia seguinte).
- **Sem overnight** → sem swap, sem gap noturno (índices fecham; ouro/FX seguem, mas fechamos mesmo assim).
- Vol targeting e cascata (da Fase 0.5/RF-9) aplicados em escala pequena.

## 7. A matemática honesta (o que decide se vive ou morre)
Exemplo ouro, 0,01 lote:
- Custo round-trip ≈ **$0,70** (spread $0,35 + comissão $0,35).
- Um rompimento intraday de $8 = 800 pts = **+$8** bruto; stop de $3 = **−$3**.
- Se o sinal acerta ~40% com payoff 2:1, expectativa bruta ≈ 0,4·$8 − 0,6·$3 = **+$1,40/trade**; menos $0,70 de custo = **+$0,70/trade líquido**.
- A **frequência** decide o resto: 1–2 trades/dia bons → viável; 10 trades/dia → o custo ($7/dia) come tudo.

**Conclusão da conta:** o intraday em ouro/índices **pode** ter expectativa positiva porque o custo é fração pequena do movimento — o oposto do FX scalping que a pesquisa condena. Mas **só se a frequência for baixa** (poucos sinais de alta qualidade por dia). Isso vira um requisito de projeto: **filtro de qualidade forte, poucos trades.**

## 8. Riscos e armadilhas (honestidade)
- **Frequência × custo** é o assassino silencioso. O sistema precisa negociar POUCO e bem.
- **Decay mais rápido**: edges intraday somem mais rápido que os de swing; re-teste frequente.
- **Retorno absoluto pequeno**: $1.000 a micro lote, um bom ano é +$100–300. Isso **prova o processo e compõe no tempo** — não é renda. Ser explícito nisso evita frustração e overtrading.
- **Dados faltantes** para índices (baixar + validar qualidade).
- **Sessão/gap** em índices; execução intraday exige o EA rodando confiável (VPS).
- A pesquisa **alerta contra intraday no varejo** — nossa aposta é que ouro/índices em H1 (não M5-FX) é caso diferente. **Tem que ser provado com o mesmo rigor (CPCV/DSR/MC), não assumido.**

## 9. O que reaproveitamos (nada se perde)
Toda a infra serve: ingestão de tick → sanidade → barras (agora H1/M15) → backtester com custo (agora sem swap, com corte de sessão) → validação (PSR/DSR/CPCV/MC) → reconciliação MT5. Muda o **alvo** (ouro+índices, intraday), não as **ferramentas**.

## 10. Decisões abertas para você
1. **Instrumentos:** ouro + quais índices? (US100, US500, GER40 — 1, 2 ou os 3?)
2. **Sinal primário:** começar por ORB/momentum de sessão (recomendado) ou breakout de canal intraday?
3. **Baixar dados de índices** da Dukascopy (nova Fase 0 para eles) — ok?
4. **Timeframe:** H1 como decisão (recomendado) — confirma?
