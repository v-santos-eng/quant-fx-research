# Consistência em trading algorítmico de varejo com US$ 1.000: o que a evidência sustenta

Classificação usada em todo o texto: **[C]** Científica (peer-reviewed, replicada), **[M]** Moderada (fonte institucional séria, não replicada de forma independente), **[E]** Empírica (consenso profissional sem estudo formal), **[X]** Experimental (plausível, não testado), **[?]** Inconclusivo. Datas e veículos aparecem na primeira citação; a lista completa está no fim.

---

## 1. Viabilidade do capital

US$ 1.000 tem dois problemas distintos e conviria não misturá-los: custo proporcional (spread, comissão, slippage, swap), que escala com o tamanho da posição, e custo fixo (VPS, dados, ferramentas), que não escala. O primeiro é o mesmo problema de sempre em escala menor. O segundo muda de natureza com capital pequeno e é ele que decide a viabilidade.

**Custo proporcional.** Em conta raw spread num par major, o custo típico atual de ida e volta é ~0,2 pip de spread + ~US$ 7/lote de comissão, o equivalente a ~0,9 pip por round turn; em conta standard sem comissão, ~1,0 a 1,5 pip. Isso dá ~1 ponto-base do nocional, um custo proporcionalmente baixo. Tamanho de varejo tem até uma vantagem documentada na literatura de custos: anomalias acadêmicas perdem rentabilidade com custo e impacto de mercado conforme o capital cresce (Novy-Marx e Velikov, 2016, Review of Financial Studies, "A Taxonomy of Anomalies and Their Trading Costs") [C]; medições com US$ 1,7 trilhão de execuções reais confirmam o impacto como função do tamanho (Frazzini, Israel e Moskowitz, 2018, "Trading Costs", working paper AQR/SSRN) [M]. Um micro lote não move preço nenhum. O custo proporcional, portanto, não inviabiliza US$ 1.000 por si só. O que ele faz é excluir frequências altas: contra um alvo de 5 pips, 0,9 pip de custo consome 20-30% do movimento bruto; contra um movimento diário de 30-80 pips, consome poucos por cento. A aritmética empurra conta pequena para timeframe diário ou superior, e isso converge com onde a evidência de edge é melhor (seção 4).

Números concretos, com risco de 1% por trade e stop de 30 pips em EURUSD: posição de 0,033 lote, pip valendo US$ 0,33, custo de US$ 0,30-0,43 por trade. Um sistema com Sharpe por trade de 0,05 (definição na seção 2; corresponde a Sharpe anual ~0,8 com 250 trades/ano, nível de um bom sistema real) tem expectância líquida de ~1,25 pip por trade. Para entregar isso líquido, a expectância bruta precisa ser ~2,15 pips: **o custo consome ~42% do edge bruto** mesmo no timeframe diário. Esse sistema gera ~US$ 104/ano sobre US$ 1.000. Os parâmetros de custo vêm de tabelas de corretoras (única fonte existente para esse dado; usados aqui como insumo aritmético, não como evidência de prática) [E].

**Custo fixo.** US$ 30/mês são US$ 360/ano, 36% do capital ao ano. Nenhuma família de estratégia documentada sustenta 36% líquidos com risco aceitável (seção 4); a referência de um século de trend following multi-ativo é Sharpe ~0,4 líquido de custos e taxas (Hurst, Ooi e Pedersen, 2017) [C]. A conta de breakeven:

| Retorno líquido de trading | Opex US$ 60/ano | Opex US$ 360/ano |
|---|---|---|
| 5% a.a. | breakeven US$ 1.200 | breakeven US$ 7.200 |
| 10% a.a. | US$ 600 | US$ 3.600 |
| 20% a.a. | US$ 300 | US$ 1.800 |
| p/ opex ≤ 10% do lucro (r = 10%) | US$ 6.000 | US$ 36.000 |

Com US$ 30/mês e um edge bom (10% a.a. líquido de custos de trade), o valor esperado da operação em US$ 1.000 é ~-US$ 256/ano. **Existe, sim, um piso abaixo do qual o problema deixa de ser estatístico e vira aritmético: é opex anual dividido pelo retorno líquido realista.** Com US$ 360/ano de opex, o piso fica entre US$ 3.600 e US$ 7.200. US$ 1.000 está abaixo dele. A única forma de US$ 1.000 ser operável é opex ≈ 0: máquina local (que você já tem), feed de dados do próprio broker via MT5 (gratuito), sem VPS. Em timeframe diário, VPS não é requisito técnico; latência é irrelevante nessa escala (seção 5).

A saída aparente, aumentar alavancagem para diluir o custo fixo, tem contraevidência causal direta: Heimer e Simsek (2019, Journal of Financial Economics, "Should Retail Investors' Leverage Be Limited?") estudaram o teto regulatório de alavancagem imposto nos EUA em 2010 como quase-experimento; a restrição melhorou o retorno dos traders de alta alavancagem em 18 pontos percentuais ao mês e reduziu suas perdas em ~40% [C]. Alavancagem alta em conta pequena não dilui o problema, acelera a ruína. Complemento: swap de varejo carrega markup do broker sobre o diferencial de juros, o que degrada ou inverte o carry teórico de posições multi-dia [E].

Granularidade fecha a análise: com lote mínimo de 0,01 e stop de 30 pips, o risco mínimo por trade é US$ 3, ou 0,3% de US$ 1.000, o que ainda permite dimensionamento fino. Abaixo de ~US$ 300-500 de capital, o degrau mínimo de risco passa de 1% e o dimensionamento contínuo quebra. US$ 1.000 está acima desse limite técnico, abaixo do limite econômico com opex de US$ 30/mês, e dentro do viável com opex zero.

---

## 2. O que "consistente" significa em números

Proposta de definição operacional, em cinco condições cumulativas:

1. **Deflated Sharpe Ratio > 0,95** contando honestamente o número de configurações testadas. O DSR corrige o Sharpe observado por viés de seleção, não-normalidade e tamanho de amostra (Bailey e López de Prado, 2014, Journal of Portfolio Management, "The Deflated Sharpe Ratio") [C].
2. **Expectância positiva em cada regime**, com regimes definidos ex ante (por exemplo, tercis de volatilidade realizada e sub-períodos de 2-3 anos), e intervalos de confiança sobrepostos entre regimes. Um sistema que lucra só num regime é uma aposta nesse regime, não um sistema.
3. **Drawdown realizado dentro do envelope de Monte Carlo** (abaixo do p95 da distribuição simulada por re-sequenciamento de trades).
4. **Amostra mínima na casa de 2.000 trades** ou o Minimum Track Record Length correspondente (Bailey e López de Prado, 2012, Journal of Risk, "The Sharpe Ratio Efficient Frontier"), que cresce com assimetria e curtose negativas [C].
5. **Aderência de execução**: slippage e fills reais dentro do modelado no backtest. Isso é testável com poucas dezenas de trades, ao contrário do edge.

O motivo da condição 4 é poder estatístico, e os números são desconfortáveis. Com Sharpe por trade SR_t (expectância dividida pelo desvio-padrão do resultado por trade), o t-stat é SR_t·√N. Poder de detecção com significância de 5% unilateral:

| SR por trade (Sharpe anual a 250 tr/ano) | N=200 | N=500 | N=2.000 | N p/ poder 80% | N p/ t=3 |
|---|---|---|---|---|---|
| 0,03 (~0,5) | 11% | 16% | 38% | 6.870 | 10.000 |
| 0,05 (~0,8) | 17% | 30% | 72% | 2.473 | 3.600 |
| 0,10 (~1,6) | 41% | 72% | ~100% | 618 | 900 |

Leitura direta: **200 trades não decidem nada** (poder de 11-41% até para edges bons; a maioria dos edges reais passaria despercebida e a maioria dos "edges" detectados seria ruído). 500 trades só resolvem edges do tamanho que quase nenhum sistema sustenta (Sharpe anual ~1,6). 2.000 trades dão 72% de poder para um sistema de Sharpe ~0,8, ainda aquém do ideal. A coluna t=3 usa o limiar de Harvey, Liu e Zhu (2016, Review of Financial Studies, "...and the Cross-Section of Expected Returns"), que argumentam que t=2 é baixo demais dado o volume de testes já feitos em finanças [C].

A razão do limiar mais alto: seleção infla o Sharpe esperado sob ruído puro. O melhor resultado entre K configurações independentes testadas sobre N trades sem edge nenhum tem Sharpe por trade esperado ≈ √(2·ln K)/√N:

| Configurações testadas | N=500 | N=2.000 |
|---|---|---|
| K=10 | Sharpe anual falso ~0,96 | ~0,48 |
| K=20 | ~1,21 | ~0,60 |
| K=100 | ~1,67 | ~0,84 |

Vinte variações de parâmetro sobre 500 trades fabricam um Sharpe ~1,2 do nada. Esse é o resultado central de Bailey, Borwein, López de Prado e Zhu (2014, Notices of the American Mathematical Society, "Pseudo-Mathematics and Financial Charlatanism"): com tentativas suficientes, qualquer Sharpe alvo é atingível in-sample [C]. A métrica Probability of Backtest Overfitting formaliza a medição (Bailey, Borwein, López de Prado e Zhu, 2017, Journal of Computational Finance) [C].

Consistência também não é ausência de períodos ruins. Monte Carlo de um sistema legítimo (Sharpe anual 0,8, vol 10%, 4 anos, retornos diários):

- Max drawdown: mediana 13%, p95 24%
- Maior período abaixo da máxima anterior: mediana ~14 meses, p95 ~40 meses
- Probabilidade de terminar 4 anos no negativo: ~7%

Um sistema genuinamente bom passa mais de um ano abaixo do pico com frequência. Definição prática que decorre disso: consistência é estacionariedade da expectância confirmada com amostra suficiente, não suavidade da curva de capital. Quem exige suavidade seleciona overfitting.

---

## 3. Onde está o edge: sinal, estatística ou risco

Ranking por qualidade de evidência fora da amostra: **(a) > (d) > (b) > (c)**. Detalhe e justificativa:

### (a) Regra fixa sobre prêmio de risco documentado: a melhor evidência disponível

Time-series momentum: retorno positivo em 58 mercados de futuros e forwards, 1965-2009 (Moskowitz, Ooi e Pedersen, 2012, Journal of Financial Economics, "Time Series Momentum") [C]; estendido a 1880-2016 com Sharpe líquido ~0,4 em cada década (Hurst, Ooi e Pedersen, 2017, Journal of Portfolio Management, "A Century of Evidence on Trend-Following Investing") [C]; replicação independente por grupo distinto com dois séculos de dados e t-stat ~5 desde 1960, ~10 desde 1800 (Lempérière, Deremble, Seager, Potters e Bouchaud, 2014, Journal of Investment Strategies, "Two Centuries of Trend Following") [C]. Carry multi-ativo: Koijen, Moskowitz, Pedersen e Vrugt (2018, Journal of Financial Economics, "Carry") [C], com risco de crash documentado em FX (Brunnermeier, Nagel e Pedersen, 2008, NBER Macroeconomics Annual, "Carry Trades and Currency Crashes") [C]. Momentum cross-section em moedas: spread de até ~10% a.a. entre vencedoras e perdedoras, 1976-2010 (Menkhoff, Sarno, Schmeling e Schrimpf, 2012, Journal of Financial Economics, "Currency Momentum Strategies") [C], com a ressalva relevante para varejo de que os lucros se concentram em moedas de spread alto e caem bastante líquidos de custo.

Essas famílias têm o que nenhuma outra tem: replicação entre grupos independentes (AQR, CFM, academia), amostras seculares, estabilidade multi-ativo e explicação econômica de por que o retorno não é arbitrado (seção 4). Poucos graus de liberdade: um lookback, uma regra de sinal, um esquema de dimensionamento, tipicamente 2-4 parâmetros.

### (d) Camada de risco e dimensionamento: segunda melhor, com controvérsia ativa

A afirmação forte ("volatility targeting aumenta Sharpe em geral") não sobrevive à melhor metodologia. Moreira e Muir (2017, Journal of Finance, "Volatility-Managed Portfolios") documentaram alfas positivos ao escalar fatores por inverso da variância [C na existência do alfa em regressão de spanning]. Cederburg, O'Doherty, Wang e Yan (2020, Journal of Financial Economics) testaram 103 estratégias em versões implementáveis em tempo real e encontraram que as versões out-of-sample geralmente entregam Sharpe e retorno-certeza-equivalente menores que os portfólios sem gestão de vol, por instabilidade estrutural das regressões [C]. Entre os dois, a metodologia de Cederburg et al. é superior para a pergunta que interessa aqui (implementável, sem look-ahead).

A afirmação condicional sobrevive: em ativos de risco com efeito alavancagem (equities, crédito), vol targeting melhora Sharpe; **em bonds, moedas e commodities o efeito sobre o Sharpe é ~zero**; em todas as classes, reduz caudas e drawdowns extremos porque perdas extremas ocorrem em vol alta, quando a posição já está reduzida (Harvey, Hoyle, Korgaonkar, Rattray, Sargaison e Van Hemert, 2018, Journal of Portfolio Management, "The Impact of Volatility Targeting", 60+ ativos, 1926-2017) [C]. Caso específico bem estabelecido: gestão de risco de momentum corta os crashes característicos da estratégia e quase dobra o Sharpe (Barroso e Santa-Clara, 2015, Journal of Financial Economics, "Momentum Has Its Moments"; Daniel e Moskowitz, 2016, Journal of Financial Economics, "Momentum Crashes") [C].

Quanto do Sharpe mensurável vem de (d) e não de (a)-(c)? Não existe decomposição limpa publicada [?]. O que a evidência permite dizer: para o portfólio relevante a este projeto (FX e futuros via CFD), o ganho de média esperado de (d) é aproximadamente nulo (Harvey et al., 2018); o ganho real é de sobrevivência, na forma de caudas menores, drawdowns mais rasos e menor probabilidade de ruína. E um limite lógico que convém explicitar: **dimensionamento não cria retorno onde não há sinal; escalar um fluxo de média zero produz média zero menos custos.** (d) é multiplicador de (a)-(b), não fonte independente.

### (b) Econometria paramétrica sem ML: funcionou, degradou, e a degradação está documentada

Pairs trading por distância: ~11% a.a. em 1962-2002 (Gatev, Goetzmann e Rouwenhorst, 2006, Review of Financial Studies, "Pairs Trading: Performance of a Relative-Value Arbitrage Rule") [C]. A sequência importa mais que o resultado original: lucros declinantes e, líquidos de custos com estimativa de custo variável no tempo, em média não-positivos após 2002, com exceção dos bear markets 2000-02 e 2007-09 (Do e Faff, 2010, Financial Analysts Journal, "Does Simple Pairs Trading Still Work?"; Do e Faff, 2012, Journal of Financial Research) [C]. Stat arb institucional mostra o mesmo decaimento após 2002-2007 (Avellaneda e Lee, 2010, Quantitative Finance, "Statistical Arbitrage in the US Equities Market") [M]. Frameworks de Ornstein-Uhlenbeck e Kalman para hedge dinâmico são métodos sólidos (Elliott, van der Hoek e Malcolm, 2005, Quantitative Finance) cuja lucratividade persistente pós-2010 carece de demonstração independente [M no método, ? na lucratividade atual].

GARCH merece separação: a previsibilidade de volatilidade é um dos fatos mais replicados de toda a econometria financeira (Engle, 1982, Econometrica; Bollerslev, 1986, Journal of Econometrics; para FX, nada supera sistematicamente um GARCH(1,1): Hansen e Lunde, 2005, Journal of Applied Econometrics) [C]. Converter essa previsibilidade em filtro de regime lucrativo é um passo adicional com suporte apenas parcial, e é exatamente onde Cederburg et al. mostram a fragilidade [M].

### (c) ML/RL como gerador primário de sinal: a pior evidência das quatro, e não por preconceito

O que está estabelecido: métodos de ML melhoram a previsão de retornos cross-section relativa a modelos lineares (Gu, Kelly e Xiu, 2020, Review of Financial Studies, "Empirical Asset Pricing via Machine Learning") [C]. O que também está estabelecido, pela continuação dessa mesma literatura: os lucros se concentram em microcaps, ações em distress e estados de alto limite à arbitragem; excluí-los atenua fortemente o resultado, e custos de transação realistas o deterioram ainda mais, por turnover alto e posições extremas (Avramov, Cheng e Metzker, 2023, Management Science, "Machine Learning vs. Economic Restrictions") [C]. Deep learning em stat arb foi lucrativo bruto até ~2010 e decaiu depois (Krauss, Do e Huck, 2017, European Journal of Operational Research) [C]. RL para trading tem resultados positivos publicados (Zhang, Zohren e Roberts, 2020, Journal of Financial Data Science) sem replicação independente com custos realistas, num campo com problema conhecido de reprodutibilidade [X].

À pergunta direta: **caso documentado e auditável de trader de varejo com edge sustentado via ML puro sobre preço bruto não existe na literatura consultável.** A evidência disponível é anedótica (fóruns, vendedores, threads) e a fonte anedótica típica tem conflito de interesse comercial [?]. Ausência de evidência não é evidência de ausência, mas a assimetria é informativa: para (a) existem séculos de dados públicos replicados; para (c) primário no varejo não existe um caso limpo.

O mecanismo da diferença está nos graus de liberdade. Uma regra de trend tem 2-4 parâmetros; um pipeline de ML tem escolha de features, janelas, arquitetura, hiperparâmetros, seeds e critérios de parada, com K efetivo facilmente na casa das centenas. Pela tabela da seção 2, K=100 sobre 500 trades fabrica Sharpe ~1,7 sob ruído puro. O backtest de um pipeline de ML sem contagem explícita de tentativas e sem DSR/PBO não é evidência de nada; é a máquina de charlatanismo matemático de Bailey et al. (2014) operando em modo automático, sem má-fé necessária [C no mecanismo].

Papel defensável de ML como camada secundária: existe, com evidência moderada. Meta-labeling (um modelo secundário decide tamanho/veto sobre um sinal primário de origem econômica) foi proposto por López de Prado (2018, Advances in Financial Machine Learning, Wiley) e testado em série de artigos no Journal of Financial Data Science (Singh e Joubert, 2022; Meyer, Joubert e Alfeus, 2022-23), com melhora de eficácia de sinal em testes controlados [M, com a nota de que parte do ecossistema em torno do tema vende software, o que pede desconto]. Classificação de regime: a existência de regimes é bem estabelecida (Ang e Bekaert, 2002, Review of Financial Studies) [C]; que filtrar por regime melhore estratégia out-of-sample de forma estável é suporte apenas parcial [M]. A configuração defensável: sinal primário de (a), ML restrito a decidir "operar ou não operar / quanto", com graus de liberdade contados no DSR.

---

## 4. Estratégias com evidência de persistência

**Trend following / time-series momentum** é a única família com evidência simultânea de: mais de um século de dados, replicação por grupos independentes com metodologias distintas, funcionamento em dezenas de mercados não correlacionados e lucro líquido de custos em cada década (referências na seção 3a) [C]. Explicação econômica, que é o que sustenta a expectativa de persistência: sub-reação inicial a informação (ancoragem, disposição a realizar ganhos cedo), realimentação de fluxo depois, e presença estrutural de participantes que transacionam por motivos alheios a lucro especulativo (hedgers comerciais, bancos centrais em FX, rebalanceamento mecânico), que transferem retorno a quem toma a ponta oposta. O prêmio sobrevive à publicação há 30+ anos porque carregá-lo é desconfortável: anos abaixo do pico (seção 2) e perdas em mercados laterais que a maioria dos alocadores não tolera.

A degradação 2010-2019 é real e sua causa foi decomposta: o desempenho fraco da década não se explica por perda de eficácia da conversão sinal-lucro nem por falha de diversificação, e sim pela magnitude atipicamente pequena dos movimentos de mercado no período (Babu, Hoffman, Levine, Ooi, Schroeder e Stamelos, 2020, Journal of Portfolio Management, "You Can't Always Trend When You Want") [M: metodologia boa, autores gestores com interesse na conclusão]. A hipótese concorrente, crowding, tem suporte mais fraco; e o desempenho de 2020 e sobretudo 2022 (ano de crise de bonds em que CTAs entregaram retornos altos) é consistente com a explicação de "faltou movimento, não faltou edge". Custo de implementação em conta pequena: baixo. Poucos trades, timeframe diário, majors com ~1 pip de custo. A limitação real é diversificação: o Sharpe ~0,7-1,0 dos CTAs vem de 40-60 mercados; com 8-15 instrumentos acessíveis em MT5 (majors, cruzados líquidos, ouro, prata, 2-3 índices), o Sharpe esperado da família cai plausivelmente para 0,3-0,6 [X: extrapolação aritmética de correlação, não medida publicada para esse universo].

**Carry FX**: prêmio documentado em décadas e classes de ativos (Koijen et al., 2018; Lustig, Roussanov e Verdelhan, 2011, Review of Financial Studies, "Common Risk Factors in Currency Markets") [C], com explicação econômica genuína: é remuneração por risco de crash; o retorno vem com assimetria negativa severa e perdas concentradas em episódios de aversão a risco (Brunnermeier et al., 2008) [C]. Degradação pós-2008 documentada: compressão de diferenciais de juros no G10 na era de juros zero reduziu o prêmio bruto na década de 2010; o ciclo de alta de 2022+ restaurou diferenciais parcialmente. Implementação em conta pequena: tecnicamente trivial (manter posição), economicamente comprometida no varejo porque o swap cobrado pelo broker embute markup que consome parte relevante do diferencial [E]; e a combinação de assimetria negativa com alavancagem é o caminho clássico de ruína. Viável apenas como componente pequeno, nunca como núcleo, numa conta de US$ 1.000.

**Prêmio de risco de variância** (vender volatilidade implícita cara contra realizada): documentado e persistente (Carr e Wu, 2009, Review of Financial Studies, "Variance Risk Premiums") [C], com explicação econômica (seguro). Implementação em US$ 1.000: inviável; requer opções, margem para caudas e sobrevivência a eventos tipo fev/2018. Registrado aqui apenas para completude.

**Value / reversão de longo prazo em ações**: evidência secular [C], mas exige amplitude de cross-section e horizonte de anos; irrelevante para este projeto. Vale pelo aviso embutido: McLean e Pontiff (2016, Journal of Finance, "Does Academic Research Destroy Stock Return Predictability?") mediram o decaimento médio de 97 anomalias publicadas: retornos ~26% menores out-of-sample e ~58% menores pós-publicação [C]. Prêmios comportamentais/de risco com explicação econômica (trend, carry, value) decaem menos que anomalias estatísticas sem explicação. Esse é o critério de triagem que importa: **se não há razão econômica para o retorno existir, a expectativa correta pós-descoberta é decaimento rápido.**

**Análise técnica clássica de curto prazo** (médias, rompimentos intradiários, padrões): falsificada nos termos que o varejo a pratica. Sobre 100 anos de Dow Jones e ~7.800 regras, nada sobrevive ao ajuste de data snooping no período 1987-1996 (Sullivan, Timmermann e White, 1999, Journal of Finance, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", usando o Reality Check de White, 2000, Econometrica) [C]. Com controle por False Discovery Rate e custos: nenhum investidor teria conseguido selecionar ex ante as regras futuras vencedoras, e custos baixos eliminam o desempenho até in-sample nas décadas recentes (Bajgrowicz e Scaillet, 2012, Journal of Financial Economics) [C]. Isso não nega a seção 3a: TSMOM em timeframe diário multi-ativo com dimensionamento por vol é tecnicamente "uma regra sobre preço", mas o que a literatura falsificou foi a mineração de regras curtas num único mercado, que é precisamente o modo de operação do varejo e de quase todo EA vendido para MT5.

---

## 5. Práticas que separam sobreviventes de mortos

**Validação.** A hierarquia por evidência: (i) testes formais de data snooping e seleção, isto é, Reality Check (White, 2000), teste SPA (Hansen, 2005, Journal of Business & Economic Statistics), DSR e PBO (seção 2), são estatística peer-reviewed e replicada [C]; (ii) purged k-fold com embargo e Combinatorial Purged Cross-Validation, desenhados para eliminar vazamento por sobreposição de labels em séries temporais (López de Prado, 2018), com adoção institucional e replicação independente parcial [M]; (iii) walk-forward clássico: prática padrão da indústria há décadas, sem literatura formal forte, e com a limitação estrutural de testar um único caminho histórico [E]; (iv) Monte Carlo por re-sequenciamento de trades para estimar distribuição de drawdown: válido sob hipótese de trocabilidade dos trades, que autocorrelação de resultados viola; útil como envelope, não como verdade [E]. Ordem prática: CPCV ou walk-forward com embargo para estimar expectância, DSR sobre o resultado contando tentativas, MC para o envelope de drawdown que vira contrato operacional (seção 2, condição 3).

**Risco.** O critério de Kelly é matematicamente demonstrado como ótimo de crescimento sob distribuição conhecida (Kelly, 1956, Bell System Technical Journal; tratamento completo em MacLean, Thorp e Ziemba, 2011) [C]; a prática universal de operar fração de Kelly (¼ a ½) por incerteza de parâmetro é consenso profissional sem teorema [E], e a direção é certa: superestimar o edge com Kelly cheio produz drawdowns catastróficos, e a penalidade por apostar acima do Kelly verdadeiro é assimétrica. Vol targeting: evidência na seção 3d; para FX, espere benefício de cauda, não de média [C]. Limite de perda diária e desligamento automático: prática de mesa proprietária sem estudo formal [E], coerente com a evidência comportamental de que perdas induzem aumento de risco (loss chasing) na população de traders [M: literatura comportamental adjacente, não teste da prática em si]. Dimensionamento por risco agregado considerando correlação entre posições (pares de USD são uma posição de USD): princípio de teoria de portfólio elementar [C no princípio, E na receita específica].

**Disciplina operacional.** Revalidação periódica com monitoramento de decaimento: o fenômeno do decaimento é documentado (McLean e Pontiff, 2016) [C]; o protocolo específico de revalidação é prática sem estudo formal [E]. Para a decisão "o drawdown atual é normal ou o edge morreu", existe framework quantitativo publicado por grupo institucional sério: dado o Sharpe assumido, deriva-se o drawdown que deveria disparar desligamento a cada nível de confiança (Rej, Seager e Bouchaud, 2017, arXiv/Wilmott, "You Are in a Drawdown. When Should You Start Worrying?") [M]. Regra derivável da seção 2: um sistema Sharpe 0,8 com maxDD simulado p95 de 24% deve ser desligado ao romper ~25%, e a decisão está escrita antes do primeiro trade, não durante o drawdown. Controle de latência e falha de execução: em timeframe diário, latência é irrelevante (um segundo contra barras de 24h); o que mata é bug silencioso: ordem duplicada, stop não registrado no servidor, reconexão com estado inconsistente, mudança de contrato/margem do broker. Reconciliação diária entre fills esperados e reais, e desligamento automático quando slippage medido excede o modelado, são consenso profissional sem literatura [E]. Intervenção manual: não há estudo controlado sobre override em sistemas de varejo [?]; a evidência adjacente aponta numa direção só: o desempenho discricionário de varejo é sistematicamente negativo (seção 6), e ajustes judgmentais degradam previsões estatísticas na literatura de forecasting em geral [M]. O custo esperado de "só dessa vez" é negativo.

---

## 6. Modos de falha

Não existe censo peer-reviewed de causas de morte de bots de varejo; a ordenação abaixo combina o que tem evidência direta com inferência declarada como tal [a ordenação em si é E].

1. **Overfitting e viés de seleção.** O mecanismo é matematicamente estabelecido (seção 2) [C]. A frequência na população de varejo não é medida diretamente, mas o ambiente é o pior possível: otimizador de parâmetros nativo no MT5, milhares de backtests por hora, nenhuma contagem de tentativas. Tudo que se sabe sobre mineração de regras (Sullivan et al., 1999; Bajgrowicz e Scaillet, 2012) prevê que a maioria dos sistemas de varejo entra no mercado com expectância verdadeira ~zero menos custos [C no mecanismo, E na atribuição de frequência].
2. **Custo subestimado.** Backtests em spread fixo ideal, sem comissão, swap, slippage de stop nem alargamento de spread em notícia. A literatura mostra custos destruindo estratégias inteiras (Bajgrowicz e Scaillet, 2012; Do e Faff, 2012; Avramov et al., 2023) [C].
3. **Subcapitalização e alavancagem.** Evidência causal de que alavancagem alta piora resultado (Heimer e Simsek, 2019) [C]; dados de reguladores: 74-89% das contas CFD de varejo perdem dinheiro, perda média por cliente de €1.600 a €29.000 conforme jurisdição (levantamento das autoridades nacionais compilado pela ESMA, 2018) [M]; na França, 89% dos clientes de FX/CFD perderam ao longo de 4 anos, perda média ~€10.900 (estudo AMF, 2014) [M].
4. **Mudança de regime e decaimento de edge.** Documentado no nível de famílias de estratégia (McLean e Pontiff, 2016; Do e Faff, 2012; discussão de trend na seção 4) [C]. Diferencial prático: quem monitora decaimento com regra ex ante desliga com perda pequena; quem não monitora devolve anos de resultado.
5. **Bug de execução e falha de infraestrutura.** Sem estatística de varejo [?]; o caso institucional documentado (Knight Capital, 2012: US$ 440M em 45 minutos por deploy defeituoso) estabelece o teto de severidade. No varejo MT5, os modos típicos: reconexão com estado órfão, stop no cliente e não no servidor, mudança de especificação de contrato, VPS reiniciando em rollover [E].
6. **Intervenção manual e abandono.** Desligar o sistema no drawdown normal (seção 2 mostra que 14 meses abaixo do pico é mediana, não anomalia) e religar depois do rali; ou override direto. Sem estudo formal no contexto algorítmico [?], direção inferida da evidência discricionária [E].

Sobre taxa de fracasso e tempo de sobrevivência: **para traders algorítmicos de varejo especificamente, o dado não existe publicado** [?]. Os proxies com melhor metodologia, todos de trading ativo de varejo em geral: no Brasil, dos indivíduos que iniciaram day trade em futuros entre 2013-2015 e persistiram mais de 300 pregões, 97% perderam dinheiro, 1,1% ganhou mais que um salário mínimo, e não há evidência de aprendizado com a experiência (Chague, De-Losso e Giovannetti, 2020, working paper FEA-USP/SSRN, "Day Trading for a Living?") [M: muito citado, não publicado em periódico]. Em Taiwan, com dados completos do mercado 1992-2006: agregado de day traders perde de forma confiável em 14 de 15 anos, menos de 1% da população exibe habilidade previsível líquida de custos, e a rotatividade é alta, com a maioria abandonando a atividade em poucos anos apesar das perdas continuadas dos que ficam (Barber, Lee, Liu e Odean, 2014, Journal of Financial Markets, "The Cross-Section of Speculator Skill"; sobre a persistência apesar de perdas, dos mesmos autores, "Do Day Traders Rationally Learn About Their Ability?", working paper) [C]. Nos EUA, os relatórios trimestrais obrigatórios dos brokers de FX à CFTC mostram ~25-35% de contas lucrativas por trimestre, com baixa persistência entre trimestres [M: dado regulatório, sem controle de composição]. Transportar isso para bots exige cautela declarada: automação elimina o erro de execução emocional e preserva integralmente o erro estatístico de pesquisa; a fração do fracasso discricionário atribuível a cada componente não está medida [X].

---

## 7. Veredito

Separando as duas perguntas que US$ 1.000 mistura:

**Como operação de retorno financeiro, a resposta honesta é não, e o bloqueio é aritmético antes de ser estatístico.** Um sistema no topo do realista (Sharpe ~0,8-1,0, vol 10%) gera US$ 80-150/ano esperados sobre US$ 1.000, com ruído mensal de ±US$ 25-60, mediana de max drawdown ~13% e cauda p95 ~24%, e períodos de mais de um ano abaixo do pico como comportamento normal. Com US$ 30/mês de opex, o valor esperado líquido é negativo (breakeven US$ 3.600-7.200 de capital). Alavancar para escapar disso tem contraevidência causal (Heimer e Simsek, 2019). Se o objetivo fosse renda: acumular capital primeiro é a resposta, e a pesquisa roda em paralelo sem prejuízo.

**Como programa de construção de um sistema consistente, com sobrevivência como métrica, existe caminho viável, e US$ 1.000 chega para ele.** O papel do capital nessa fase é expor o pipeline a execução real (fills, slippage, swap, falhas de infra, e a própria disciplina) com mensalidade limitada, não gerar retorno. O caminho mínimo que a evidência sustenta:

1. **Opex ≈ 0.** Máquina local, feed do broker via MT5, sem VPS (timeframe diário não precisa; latência é irrelevante nessa escala). Cada dólar de custo fixo é retorno certo negativo; é a única variável do problema sob controle total.
2. **Núcleo na família (a), timeframe diário ou superior**: time-series momentum / breakout de volatilidade sobre os 8-15 instrumentos líquidos acessíveis (majors, ouro, índices), o único edge com evidência secular replicada e custo de implementação compatível com ~1 pip de custo por trade. Expectativa calibrada pela diversificação limitada: Sharpe 0,3-0,6, não o 0,8-1,0 institucional [X].
3. **Camada (d) por cima**: dimensionamento por vol com risco 0,5-1% por trade, teto de risco agregado por moeda-base, limite diário de perda, kill switch. Em FX espere disso cauda menor e sobrevivência, não Sharpe extra (Harvey et al., 2018).
4. **Validação com a régua da seção 2**: contagem explícita de toda configuração testada, DSR/PBO sobre o resultado final, CPCV ou walk-forward com embargo, MC de re-sequenciamento gerando o envelope de drawdown, e a regra de desligamento escrita antes do primeiro trade real.
5. **Live como teste de execução, não de edge.** Com 100-300 trades/ano, anos passarão antes de o track record ter poder para confirmar expectância (tabela da seção 2). O que o live valida rápido (semanas) é a aderência execução-modelo. Tratar o PnL de curto prazo como sinal é erro de leitura estatística.
6. **ML, se entrar, só como camada secundária** (meta-labeling, filtro de regime) sobre sinal primário econômico, com graus de liberdade contados no DSR. Como gerador primário, o estado da evidência é: funciona em papel bruto em universos não-negociáveis, atenua com custos e restrições realistas, e não tem um único caso de varejo auditado [C/?].

Expectativa realista consolidada: 12-24 meses para um sistema validado a ponto de merecer capital; retorno esperado nesse período próximo de zero (é o custo do laboratório, limitado e conhecido); e a transição para retorno relevante acontece por aporte de capital externo sobre um sistema já validado, não por composição dos US$ 1.000. A evidência não mostra um caminho comprovado de US$ 1.000 a renda via trading; mostra, com bastante clareza, um caminho de US$ 1.000 a um sistema que sobrevive, e mostra que quase todo mundo que pula essa etapa morre pelos modos da seção 6.

---

## Referências

- AMF (Autorité des Marchés Financiers), 2014. *Study of Investment Performance of Individuals Trading in CFDs and Forex in France*.
- Ang, A.; Bekaert, G., 2002. "International Asset Allocation with Regime Shifts". *Review of Financial Studies* 15(4).
- Avellaneda, M.; Lee, J.-H., 2010. "Statistical Arbitrage in the US Equities Market". *Quantitative Finance* 10(7).
- Avramov, D.; Cheng, S.; Metzker, L., 2023. "Machine Learning vs. Economic Restrictions: Evidence from Stock Return Predictability". *Management Science* 69(5).
- Babu, A.; Hoffman, B.; Levine, A.; Ooi, Y.H.; Schroeder, S.; Stamelos, E., 2020. "You Can't Always Trend When You Want". *Journal of Portfolio Management* 46.
- Bailey, D.; Borwein, J.; López de Prado, M.; Zhu, Q.J., 2014. "Pseudo-Mathematics and Financial Charlatanism". *Notices of the AMS* 61(5).
- Bailey, D.; Borwein, J.; López de Prado, M.; Zhu, Q.J., 2017. "The Probability of Backtest Overfitting". *Journal of Computational Finance* 20(4).
- Bailey, D.; López de Prado, M., 2012. "The Sharpe Ratio Efficient Frontier". *Journal of Risk* 15(2).
- Bailey, D.; López de Prado, M., 2014. "The Deflated Sharpe Ratio". *Journal of Portfolio Management* 40(5).
- Bajgrowicz, P.; Scaillet, O., 2012. "Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs". *Journal of Financial Economics* 106(3).
- Barber, B.; Lee, Y.-T.; Liu, Y.-J.; Odean, T., 2014. "The Cross-Section of Speculator Skill: Evidence from Day Trading". *Journal of Financial Markets* 18.
- Barroso, P.; Santa-Clara, P., 2015. "Momentum Has Its Moments". *Journal of Financial Economics* 116(1).
- Bollerslev, T., 1986. "Generalized Autoregressive Conditional Heteroskedasticity". *Journal of Econometrics* 31(3).
- Brunnermeier, M.; Nagel, S.; Pedersen, L.H., 2008. "Carry Trades and Currency Crashes". *NBER Macroeconomics Annual* 23.
- Carr, P.; Wu, L., 2009. "Variance Risk Premiums". *Review of Financial Studies* 22(3).
- Cederburg, S.; O'Doherty, M.; Wang, F.; Yan, X., 2020. "On the Performance of Volatility-Managed Portfolios". *Journal of Financial Economics* 138(1).
- Chague, F.; De-Losso, R.; Giovannetti, B., 2020. "Day Trading for a Living?". Working paper, SSRN 3423101.
- Daniel, K.; Moskowitz, T., 2016. "Momentum Crashes". *Journal of Financial Economics* 122(2).
- Do, B.; Faff, R., 2010. "Does Simple Pairs Trading Still Work?". *Financial Analysts Journal* 66(4).
- Do, B.; Faff, R., 2012. "Are Pairs Trading Profits Robust to Trading Costs?". *Journal of Financial Research* 35.
- Elliott, R.; van der Hoek, J.; Malcolm, W., 2005. "Pairs Trading". *Quantitative Finance* 5(3).
- Engle, R., 1982. "Autoregressive Conditional Heteroscedasticity...". *Econometrica* 50(4).
- ESMA, 2018. *Product Intervention Measures on CFDs and Binary Options* (compilação de dados das autoridades nacionais).
- Frazzini, A.; Israel, R.; Moskowitz, T., 2018. "Trading Costs". Working paper, AQR / SSRN 3229719.
- Gatev, E.; Goetzmann, W.; Rouwenhorst, K.G., 2006. "Pairs Trading: Performance of a Relative-Value Arbitrage Rule". *Review of Financial Studies* 19(3).
- Gu, S.; Kelly, B.; Xiu, D., 2020. "Empirical Asset Pricing via Machine Learning". *Review of Financial Studies* 33(5).
- Hansen, P.R., 2005. "A Test for Superior Predictive Ability". *Journal of Business & Economic Statistics* 23(4).
- Hansen, P.R.; Lunde, A., 2005. "A Forecast Comparison of Volatility Models: Does Anything Beat a GARCH(1,1)?". *Journal of Applied Econometrics* 20(7).
- Harvey, C.; Hoyle, E.; Korgaonkar, R.; Rattray, S.; Sargaison, M.; Van Hemert, O., 2018. "The Impact of Volatility Targeting". *Journal of Portfolio Management* 45(1).
- Harvey, C.; Liu, Y.; Zhu, H., 2016. "...and the Cross-Section of Expected Returns". *Review of Financial Studies* 29(1).
- Heimer, R.; Simsek, A., 2019. "Should Retail Investors' Leverage Be Limited?". *Journal of Financial Economics* 132.
- Hurst, B.; Ooi, Y.H.; Pedersen, L.H., 2017. "A Century of Evidence on Trend-Following Investing". *Journal of Portfolio Management* 44(1).
- Kelly, J.L., 1956. "A New Interpretation of Information Rate". *Bell System Technical Journal* 35(4).
- Koijen, R.; Moskowitz, T.; Pedersen, L.H.; Vrugt, E., 2018. "Carry". *Journal of Financial Economics* 127(2).
- Krauss, C.; Do, X.A.; Huck, N., 2017. "Deep Neural Networks, Gradient-Boosted Trees, Random Forests: Statistical Arbitrage on the S&P 500". *European Journal of Operational Research* 259(2).
- Lempérière, Y.; Deremble, C.; Seager, P.; Potters, M.; Bouchaud, J.-P., 2014. "Two Centuries of Trend Following". *Journal of Investment Strategies* 3.
- López de Prado, M., 2018. *Advances in Financial Machine Learning*. Wiley.
- Lustig, H.; Roussanov, N.; Verdelhan, A., 2011. "Common Risk Factors in Currency Markets". *Review of Financial Studies* 24(11).
- MacLean, L.; Thorp, E.; Ziemba, W., 2011. *The Kelly Capital Growth Investment Criterion*. World Scientific.
- McLean, R.D.; Pontiff, J., 2016. "Does Academic Research Destroy Stock Return Predictability?". *Journal of Finance* 71(1).
- Menkhoff, L.; Sarno, L.; Schmeling, M.; Schrimpf, A., 2012. "Currency Momentum Strategies". *Journal of Financial Economics* 106(3).
- Meyer, M.; Joubert, J.; Alfeus, M., 2022-23. Artigos sobre meta-labeling. *Journal of Financial Data Science*.
- Novy-Marx, R.; Velikov, M., 2016. "A Taxonomy of Anomalies and Their Trading Costs". *Review of Financial Studies* 29(1).
- Moreira, A.; Muir, T., 2017. "Volatility-Managed Portfolios". *Journal of Finance* 72(4).
- Moskowitz, T.; Ooi, Y.H.; Pedersen, L.H., 2012. "Time Series Momentum". *Journal of Financial Economics* 104(2).
- Rej, A.; Seager, P.; Bouchaud, J.-P., 2017. "You Are in a Drawdown. When Should You Start Worrying?". arXiv:1707.01457 / *Wilmott*.
- Sullivan, R.; Timmermann, A.; White, H., 1999. "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap". *Journal of Finance* 54(5).
- White, H., 2000. "A Reality Check for Data Snooping". *Econometrica* 68(5).
- Zhang, Z.; Zohren, S.; Roberts, S., 2020. "Deep Reinforcement Learning for Trading". *Journal of Financial Data Science* 2(2).

