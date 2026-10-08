# Meta-labeling sobre o ORB (Fase 2i) — desenho para decisão

> Passo "Arquitetura". Nada implementado. Baseado em López de Prado cap. 3 (meta-labeling)
> e cap. 7/12 (Purged CV / CPCV). Objetivo: transformar o edge BRUTO real do ORB (que existe,
> mas é fino pós-custo) num edge LÍQUIDO robusto — negociando MENOS e MELHOR.
> Contexto do FAIL do ORB puro: `docs/GATES.md` Fase 1i. Baseline: `docs/baseline_orb.md`.

## 1. A ideia (por que meta-labeling e não "outro sinal")
O ORB **acerta a direção** (bruto +$744 no GER40) — o problema é que muitos sinais são de
baixa qualidade e o spread os torna perdedores líquidos. Meta-labeling **separa os papéis**:
- **Modelo primário = ORB** (já pronto): decide o LADO (long/short) e os níveis (entry/stop/alvo).
- **Meta-modelo (ML) = decide se PEGA ou NÃO** cada sinal (aposta 0 ou 1). Não inventa direção;
  só filtra para o subconjunto de alta precisão. É o uso disciplinado de ML do projeto:
  **ML só entra se bater o baseline** — aqui, literalmente filtrando o baseline.

## 2. O rótulo (meta-label binário) — sem look-ahead
Para cada sinal ORB, simula-se o bracket (já temos o engine): **y = 1 se o trade bateu o alvo
2R antes do stop (vencedor líquido), senão y = 0**. É o rótulo triple-barrier do ORB. Determinístico.

## 3. Features (só informação disponível NO fechamento da barra-gatilho)
| Feature | Intuição |
| :-- | :-- |
| OR_width / ATR | qualidade do range de abertura (nem estreito nem explosivo) |
| dist(close, VWAP) / ATR | força do momentum de sessão no rompimento |
| ATR percentil (janela longa) | regime de volatilidade |
| minuto-da-sessão do gatilho | rompimento cedo vs tarde (cedo costuma seguir) |
| retorno do dia anterior / gap de abertura | contexto direcional |
| preço vs média H1 (inclinação H1) | tendência de fundo (contexto multi-TF) |
| volume das barras do OR / média da sessão | participação na abertura |
| dia da semana | sazonalidade intrassemana |

Todas puras e auditáveis. **Zero look-ahead** (o rótulo é futuro; as features, passado).

## 4. Modelo
- **Recomendado: HistGradientBoostingClassifier (sklearn)** — captura não-linearidades e
  interações, robusto, rápido, sem tuning pesado. Raso e pequeno (poucas árvores) p/ evitar overfit.
- Alternativa: **regressão logística** (mais interpretável, menos capacidade). Bom como sanity/baseline do ML.
- Saída = P(vitória). **Regra: pega o trade se P ≥ τ.** τ escolhido para maximizar o Sharpe
  líquido, **dentro do CV** (nunca no full sample).

## 5. Validação (o mesmo rigor que reprovou o ORB puro — o guarda-costas)
- **Treino/seleção de τ:** Purged K-Fold + embargo (cap. 7) — sem vazamento por sobreposição.
- **Avaliação final:** CPCV sobre a série de trades FILTRADA → Sharpe OOS, PSR, % caminhos+.
- **DSR deflaciona** pelo nº de ensaios (grade de hiperparâmetros + escolha de τ + escolha de modelo).
  Um filtro que só "funciona" por ter testado muito NÃO sobrevive à deflação.
- **Monte Carlo** de drawdown na série filtrada (p99 tem de caber em $1.000).

## 6. Gate 2i (pré-registrado — critério ANTES do teste)
O ORB+meta-label só é APROVADO se, na série líquida filtrada:
1. Sharpe líq>0 **E** PSR>0,95 **E** CPCV≥60% caminhos+ **E** DSR>0 **E** MaxDD-p99 tolerável p/ $1.000.
2. **E bate o baseline com folga:** Sharpe líquido do filtrado **≥ baseline + margem** (senão o ML
   não agrega e cai a Navalha de Occam — fica-se sem ML). Margem proposta: **Sharpe ≥ 0,5** absoluto
   (o ORB puro deu 0,21) **e** menos trades (o filtro tem de reduzir frequência, não aumentar).
3. Testado ainda **sem comissão (otimista)**; se passar, medir comissão real e re-testar (corte final).

**Falha em qualquer critério → FAIL honesto.** Se o meta-label também não passar, a conclusão
metodológica é que esses veículos não dão edge robusto p/ varejo $1.000 — e paramos de insistir.

## 7. Risco desta aposta (honestidade)
- **Overfit do filtro** é o perigo nº 1: ML tem capacidade de memorizar ruído. Mitigação = modelo
  pequeno + Purged CV + DSR deflacionado + exigir folga sobre o baseline.
- **Amostra de eventos pequena:** ~3,3k sinais ORB no GER40 em 14 anos; ML com poucos positivos
  líquidos é frágil. Features parcimoniosas (8) e modelo raso reduzem o risco.
- **Só resgata um edge fino** — se o bruto pós-spread é marginal, o teto do que o filtro pode
  entregar também é. Não esperar milagre; esperar um veredito honesto.

## 8. Decisões para você (antes de implementar)
1. **Modelo:** HistGBM (recomendado) ou logística? Ou os dois (logística como sanity)?
2. **Features:** a lista §3 serve, ou quer tirar/adicionar algo?
3. **Margem sobre o baseline:** Sharpe ≥ 0,5 e menos trades — concorda com o "bater com folga"?
