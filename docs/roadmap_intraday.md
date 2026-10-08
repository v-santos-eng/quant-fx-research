# Roadmap reformulado — sistema intraday multi-ativo (conta pequena)

> Pivô aprovado: **daytrading intraday** (sem overnight → sem swap) sobre um **universo
> diversificado** de índices, metais e commodities. Conta ~$1.000. A infraestrutura
> (tick→barras→backtester→validação CPCV/DSR/MC→reconciliação MT5) é reaproveitada;
> muda o alvo e o timeframe.

## 1. Tese revisada
Momentum/breakout **intraday** de sessão, cross-asset, fechando toda posição antes do
rollover. Diversificação por classe de ativo (a base do TSMOM de Moskowitz-Ooi-Pedersen
2012) + custo minimizado por não atravessar a noite. Núcleo de regra transparente; ML
como meta-label só se vencer o baseline.

## 2. Universo de instrumentos (candidatos)
Critério: **movimento intraday ÷ custo**, liquidez, **cobertura de sessão** e baixa
correlação mútua. A medir na demo Dukascopy antes de fixar.

| Classe | Candidatos | Sessão-chave | Papel |
| :-- | :-- | :-- | :-- |
| Metais | **XAUUSD** (ouro), XAGUSD (prata) | Londres/NY | tendência forte, âncora |
| Índices US | **US100** (Nasdaq), US500 (S&P), US30 (Dow) | abertura NY (13:30 UTC) | momentum de abertura limpo |
| Índices EU/Ásia | **GER40** (DAX), JP225 (Nikkei) | Frankfurt/Ásia | cobre outras horas |
| Commodities | **USOIL** (WTI), UKOIL (Brent) | NY | baixa correlação com índices |

**Começar com ~5-6** de correlação baixa e boa cobertura de sessão, ex.: XAUUSD, US100,
GER40, USOIL (+ US500). Assim há sempre algo ativo em alguma sessão do dia.

## 3. Capital e posições — a resolução honesta
Com $1.000 você **não** segura 6 posições ao mesmo tempo. A diversificação vem do
**TEMPO**, não de holdings simultâneas:
- **1 posição por vez** (talvez 2 se descorrelacionadas e o capital crescer), micro lote 0,01.
- Você **escaneia o universo** e opera o **melhor setup do momento** — em dias/sessões
  diferentes, instrumentos diferentes. Ao longo de semanas, o resultado é diversificado
  (não fica sempre no mesmo regime), mesmo com 1 posição de cada vez.
- Regra de correlação: nunca 2 índices US simultâneos (são uma aposta só).
- Diversificação simultânea real só quando o capital comportar.

## 4. Custo intraday (sem swap)
- **Swap = 0** (fecha no dia). Some a camada que dominava o swing.
- **Spread por hora é o custo rei** → operar só nas horas líquidas de cada instrumento
  (percentil baixo do spread histórico daquela hora).
- **Comissão × frequência = o teto.** Requisito de projeto: **poucos trades de alta
  qualidade** (1-3/dia no universo todo). Filtro forte é obrigatório.

## 5. Sinal primário
**Opening-Range Breakout / momentum de sessão** por instrumento: define o range da 1ª
hora da sessão daquele ativo; rompimento com filtro (volatilidade/tendência) → entra;
saída por trailing ATR intraday ou fim de sessão. H1 decisão, M15 refino. Determinístico.

## 6. Roadmap por fases (reformulado)
| Fase | Entregável | Gate |
| :-- | :-- | :-- |
| **0i. Dados & custo do universo** | Barras H1/M15 de ~5-6 instrumentos; spread intraday por hora; sem swap | Custos medidos, cobertura de dado auditada |
| **1i. Baseline intraday** | ORB/momentum de sessão no universo, custos completos, fecha no dia | **Sharpe líquido > 0** e DD tolerável, validado CPCV/DSR/MC |
| **2i. Risco & filtros** | Sizing 1-posição, limite diário, filtro de sessão/spread/notícia | Caudas/DD melhoram sem destruir retorno |
| **3i. Meta-label ML** | LightGBM sobre o sinal, condicional | Vence o baseline em CPCV com DSR>0; senão fica o baseline |
| **4i. Validação completa** | WFO, MC, stress, DSR/PSR, leitura do lockbox | Critérios pré-registrados atendidos |
| **5i. Incubação demo** | Sistema em demo, gravando spread/slippage reais | Distribuição live ≈ backtest (KS) |
| **6i. Live mínimo** | Micro lote real | Tracking error na banda |

A infra das Fases 0.1-0.5 (config, reprodutibilidade, sanidade, backtester, toolkit de
validação, reconciliação MT5) **serve toda** — só troca o alvo.

## 7. Abordagem de dados (decisão)
Os CFDs de índice/commodity têm códigos de símbolo diferentes do datafeed FX da Dukascopy.
Opções:
- **A) Ponte MT5 (`copy_rates_range` H1/M15)** — rápido, usa o terminal; profundidade de
  histórico limitada (vimos ~2015+ em barras). Bom para pesquisa inicial.
- **B) Datafeed/ticks reais** — mais fundo e exato, mas exige descobrir os códigos e o
  formato por instrumento; ticks reais do tester só vão a ~2023 (como no EURUSD).
Recomendo **começar por A** (barras via ponte) para a pesquisa, e confirmar com ticks
reais na validação final (Fase 4i/5i).

## 8. Riscos e honestidade
- **Frequência × custo** continua sendo o assassino nº 1 — o sistema tem que negociar pouco.
- Edges intraday **decaem rápido** → re-teste frequente.
- **Retorno absoluto pequeno** em $1.000 (bom ano ~ +$100-300) — prova o processo, compõe
  no tempo. Não é renda.
- **Dado por instrumento** a auditar (qualidade, gaps de sessão, horários).
- Intraday exige **execução confiável** (EA + VPS).
- Ainda **não provado** — melhor fundamentado que o FX intraday, mas passa pelo mesmo
  crivo (CPCV/DSR/MC). Nada é assumido.

## 9. Decisões para confirmar antes da Fase 0i
1. **Universo inicial:** XAUUSD + US100 + GER40 + USOIL + US500? (ajustar a lista)
2. **Posições simultâneas:** 1 por vez (recomendado p/ $1.000) ou permitir 2 descorrelacionadas?
3. **Dados:** começar por barras via ponte MT5 (opção A) — ok?
4. **Sinal:** ORB/momentum de sessão como primário (recomendado)?
