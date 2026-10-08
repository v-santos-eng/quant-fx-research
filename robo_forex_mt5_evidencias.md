# Robô de Forex no MT5: projeto baseado em evidências

*Síntese técnica da literatura para uso pessoal. Não é recomendação de investimento.*

Legenda de evidência usada em todo o documento: **\[F\]** forte (revisada por pares, replicada) · **\[M\]** moderada (publicada, replicação parcial ou com ressalvas) · **\[E\]** empírica da indústria (prática documentada de bancos/fundos, sem literatura conclusiva) · **\[X\]** experimental ou hipótese · **\[∅\]** sem evidência verificável.

---

## Parte 1: O que realmente gera consistência

O edge é o componente mais fraco e mais incerto de qualquer sistema. Tudo o mais existe para que um edge pequeno e intermitente sobreviva ao mundo real. A ordem de importância, do mais para o menos decisivo:

**1º. Custos de transação e qualidade de execução \[F\].** A maior parte das anomalias publicadas morre depois de custos realistas. Novy-Marx e Velikov (2016) mostram isso sistematicamente em ações; Neely e Weller (2013) documentam o mesmo em FX: regras técnicas que lucravam nos anos 1970-80 convergiram para retorno líquido próximo de zero nos majors a partir dos anos 1990\. Em Forex os custos têm três camadas: spread (variável por sessão e por evento), slippage (assimétrico, pior em stops durante notícias) e swap (domina o P\&L quando a posição atravessa dias, especialmente em pares de carry negativo). Um sistema que não modela as três camadas antes de qualquer otimização está medindo ruído.

**2º. Dimensionamento e limites de perda \[F\].** Sizing não cria edge, mas determina se você sobrevive à variância dele. A probabilidade de ruína e o drawdown esperado são funções diretas do risco por operação; Kelly com edge superestimado leva à quebra mesmo com expectativa positiva (Thorp, 2006). Sistemas idênticos em sinal, com sizing diferente, têm destinos opostos.

**3º. Metodologia de validação \[F\].** Harvey, Liu e Zhu (2016) argumentam que, dado o volume de testes feitos em finanças, descobertas exigem t-stat acima de 3, não 2\. Bailey, Borwein, López de Prado e Zhu (2014) mostram que com tentativas suficientes qualquer série de ruído produz um backtest "vencedor". A taxa-base de falsas descobertas em backtests é alta; o protocolo da Parte 8 é o antídoto.

**4º. Estabilidade do edge e adaptação a regimes \[M\].** Edges decaem. McLean e Pontiff (2016) medem queda de \~26% fora da amostra e \~58% após publicação em anomalias de ações; Neely e Weller (2013) mostram o padrão análogo em FX. Regimes de mercado alternam entre tendência, reversão e caos (Ang e Timmermann, 2012), e um sistema calibrado num regime sangra no outro. Detecção de regime reduz esse sangramento, mas não o elimina.

**5º. Expectativa matemática \[necessária, porém pequena\].** Precisa existir, mas nos pares líquidos ela será fina: frações de pip por operação depois de custos. Projete assumindo edge pequeno e intermitente, nunca edge grande e constante.

Liquidez, volatilidade e rollover funcionam como condições de contorno, não como fontes de consistência. Liquidez define capacidade e custo (BIS Triennial Survey 2022: giro diário de US$ 7,5 trilhões, leitura preliminar de 2025 próxima de US$ 9,6 trilhões). Volatilidade tem clustering forte e previsível (Corsi, 2009), o que o sistema deve explorar via sizing, não via previsão de direção. Swap tripla na quarta-feira e vira custo estrutural em qualquer holding acima de intradiário.

---

## Parte 2: Estratégias com evidência real

Veredito antes da análise: das 18 abordagens listadas, apenas a família tendência/momentum combina evidência acadêmica forte com implementabilidade no varejo via MT5. Order flow tem a evidência mais forte de todas, mas os dados são inacessíveis fora do interbancário. SMC e ICT não têm um único artigo revisado por pares.

| Estratégia | Evidência | Referência central | Situação no varejo MT5 |
| :---- | :---- | :---- | :---- |
| Trend following (TSMOM) | **F** (decaimento \[M\] em majors pós-2010) | Moskowitz, Ooi, Pedersen (2012) | Viável, H4/D1 |
| Momentum cross-sectional FX | **F** academicamente | Menkhoff et al. (2012) | Difícil: retorno concentrado em moedas de spread alto |
| Mean reversion intradiária | **E** | literatura de market making | Custos matam em M1-M15 no varejo |
| Mean reversion por bandas (H1+) | **X** | resultados mistos | Testável, sem expectativa alta |
| Breakout (canal) | **M** | regras Donchian; Osler (2003) | Viável, subconjunto de tendência |
| Pullback | **E** | sem literatura própria | Variante de entrada em tendência |
| VWAP como sinal | **∅** em FX spot | volume real inexistente no spot | Não aplicável |
| Order flow | **F** | Evans, Lyons (2002) | Inviável: dados interbancários |
| Volume profile | **X** em FX spot | proxy de tick volume | Frágil |
| Smart Money Concepts | **∅** | nenhuma | Narrativa não testável |
| ICT | **∅** | nenhuma | Idem |
| Price action / candles | **∅/E** | Marshall et al. (2006); Park, Irwin (2007) | Testes publicados majoritariamente negativos |
| Liquidity sweep | fenômeno **M**, framework **∅** | Osler (2005) | Já capturado por regras de breakout |
| Pairs trading | **F** em ações, **X** em FX | Gatev et al. (2006) | Relações cambiais instáveis |
| Statistical arbitrage | **X** em FX varejo | idem | Latência e custos proibitivos |
| Cointegração entre pares | **X** | Baillie, Bollerslev (1989) vs. Diebold et al. (1994) | Não estacionária na prática |
| Market making | **F** institucional | Avellaneda, Stoikov (2008) | Inviável: você paga o spread, não o recebe |
| ML supervisionado | **M** como ferramenta | López de Prado (2018); Gu, Kelly, Xiu (2020) | Viável como filtro/meta-label |
| Reinforcement learning | **X** | Moody, Saffell (2001) | Overfitting de simulador |

O que sustenta cada veredito relevante:

**Tendência e momentum.** Moskowitz, Ooi e Pedersen (2012) documentam time-series momentum em 58 futuros, incluindo moedas, com persistência de 1 a 12 meses. Lempérière et al. (2014) e Hurst, Ooi e Pedersen (2017) estendem a evidência por até dois séculos e múltiplas classes de ativos. É a anomalia mais replicada das finanças empíricas. A ressalva honesta: nos majors de FX o retorno da versão pura enfraqueceu depois de 2010, e o momentum cross-sectional de Menkhoff, Sarno, Schmeling e Schrimpf (2012), embora estatisticamente forte (\~10% a.a. bruto), concentra o retorno em moedas de spread alto e liquidez baixa, exatamente onde o varejo paga mais caro. Conclusão prática: tendência em H4/D1 sobre um portfólio de pares é o único núcleo defensável; espere Sharpe modesto, não os números dos papers.

**Order flow.** Evans e Lyons (2002) mostram que o fluxo de ordens interbancário explica 40 a 60% da variação diária do câmbio, a relação mais forte já documentada em FX. O problema é de acesso, não de ciência: esse dado existe em plataformas como EBS/Reuters e nos livros dos dealers. Tick volume de um broker de varejo não substitui. Descarte como estratégia, aproveite a lição: preço se move por desequilíbrio de fluxo, e notícias importam na medida em que geram fluxo.

**SMC, ICT, liquidity sweeps e price action.** Não existe artigo revisado por pares testando esses frameworks. O que existe de real por trás deles vem da microestrutura: Osler (2003, Journal of Finance) documenta que ordens take-profit se agrupam em números redondos e stops logo além deles, o que dá base mecânica a suporte/resistência e a rompimentos; Osler (2005) descreve cascatas de stop-loss. Ou seja, o fenômeno que o vocabulário de "sweep de liquidez" descreve tem suporte, mas ele já é capturado por uma regra de breakout de canal com filtro, sem a camada de narrativa discricionária e não falsificável. Sobre candles e padrões gráficos: Marshall, Young e Rose (2006) não encontram valor em estratégias de candlestick após custos, e o survey de Park e Irwin (2007) mostra resultados mistos contaminados por data snooping. Lo, Mamaysky e Wang (2000) encontram algum conteúdo informacional em padrões, mas em ações e sem demonstrar lucratividade líquida.

**Pares, stat-arb e cointegração.** Gatev, Goetzmann e Rouwenhorst (2006) validam pairs trading em ações. Em FX a transposição falha: taxas de câmbio já são preços relativos, e as relações de longo prazo entre elas dependem de política monetária, que muda de regime. Baillie e Bollerslev (1989) encontraram tendências estocásticas comuns entre câmbios; Diebold, Gardeazabal e Yilmaz (1994) mostraram que o resultado não se sustenta com métodos mais rigorosos. Qualquer par "cointegrado" que você achar em 5 anos de dados tem probabilidade alta de ser artefato.

**Market making e mean reversion intradiária.** O edge existe e é grande, para quem recebe o spread. Avellaneda e Stoikov (2008) formalizam o problema. No varejo MT5 você está do lado errado do livro por construção. A reversão intradiária que os dados mostram é, em grande parte, a remuneração dos provedores de liquidez; tentar capturá-la pagando spread em M5 é matematicamente adverso.

**ML e RL.** Tratados nas Partes 6 e 7\. Resumo: ML supervisionado tem evidência moderada como ferramenta de previsão de retornos quando a metodologia é correta (Gu, Kelly e Xiu, 2020, em ações; López de Prado, 2018, para o protocolo), e nenhuma evidência pública de que "resolve" FX. RL aplicado a trading segue experimental: a referência clássica é Moody e Saffell (2001), e vinte e cinco anos depois não há demonstração reprodutível de vantagem fora de simulador.

---

## Parte 3: Escolha dos pares

O critério que decide é custo relativo à volatilidade (spread all-in dividido pelo ATR diário), seguido de eficiência e de redundância de correlação. Números de ordem de grandeza para conta ECN típica em 2024-2026; meça no seu broker antes de qualquer backtest:

| Par | Spread all-in típico | ATR(14) diário típico | Custo/ATR | Observação |
| :---- | :---- | :---- | :---- | :---- |
| EURUSD | 0,7-1,0 pip | 60-80 pips | \~1,2% | Mais líquido e mais eficiente; custo mínimo, edge mais difícil |
| USDJPY | 0,8-1,2 | 80-110 | \~1,0% | Vol alta nos últimos anos; sensível a intervenção do MoF |
| GBPUSD | 1,0-1,5 | 90-110 | \~1,2% | Bom equilíbrio |
| AUDUSD | 0,8-1,2 | 50-65 | \~1,7% | Proxy de commodities e China |
| USDCAD | 1,2-1,8 | 60-75 | \~2,2% | Correlacionado a petróleo |
| NZDUSD | 1,2-2,0 | 45-55 | \~3,0% | Redundante com AUDUSD (corr \~0,85) |
| USDCHF | 1,2-1,8 | 55-65 | \~2,5% | Redundante com EURUSD (corr \~ \-0,9) |
| EURJPY | 1,2-1,8 | 90-110 | \~1,4% | Cross líquido, soma exposição EUR e JPY |
| GBPJPY | 1,8-3,0 | 130-160 | \~1,6% | Vol alta não compensa: caudas pesadas, slippage pior |
| XAUUSD | 15-35 cents | US$ 25-45 | \~0,8% | Custo/vol competitivo; problemas são gaps de abertura e caudas |

Leituras que saem da tabela. Primeiro: EURUSD é o par mais barato e o mais eficiente ao mesmo tempo, então serve de âncora do portfólio, com expectativa de edge menor por unidade. Segundo: USDCHF e NZDUSD não adicionam quase nada por correlação; incluir os dois é dobrar exposição fingindo diversificar. Terceiro: GBPJPY é popular pela volatilidade, mas o que importa é custo por unidade de volatilidade e formato das caudas, e nos dois quesitos ele perde para USDJPY. Quarto: XAUUSD tecnicamente não é FX e tem risco de gap de fim de semana e sensibilidade geopolítica, mas o custo relativo à volatilidade é dos melhores da lista e o comportamento tendencial é forte; cabe no portfólio em H4 com sizing reduzido.

Portfólio recomendado: EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, com XAUUSD opcional a meio peso. Cinco a seis instrumentos de correlação moderada é o ponto em que a diversificação de um sistema de tendência rende mais do que a complexidade custa.

---

## Parte 4: Timeframes

A aritmética decide antes de qualquer teste. Com custo all-in de \~0,9 pip no EURUSD e o movimento médio por barra medido em 2020-2025:

| TF | Movimento médio/barra | Custo como % do movimento | Trades/ano (sistema de tendência) | Veredito |
| :---- | :---- | :---- | :---- | :---- |
| M1 | \~1,5 pip | \~60% | milhares | Inviável no varejo |
| M5 | \~3,5 | \~26% | milhares | Inviável |
| M15 | \~6 | \~15% | centenas | Marginal, exige execução excelente |
| M30 | \~9 | \~10% | centenas | Marginal |
| H1 | \~13 | \~7% | 150-400 | Viável |
| H4 | \~30 | \~3% | 50-150 | Melhor relação custo/oportunidade |

Três efeitos se somam contra os timeframes baixos. O custo consome fração proibitiva do movimento esperado, como mostra a tabela. O ruído microestrutural cresce: em M1-M5 o que você modela é, em boa parte, o comportamento do feed do seu broker, não do mercado, o que significa overfitting a um artefato que muda quando o broker muda de provedor de liquidez. E a execução vira variável dominante: um sistema de M5 vive de slippage e latência, terreno em que o varejo compete em desvantagem estrutural.

Contra os timeframes altos pesa a estatística: um sistema D1 gera 20-60 trades por ano, e com isso os intervalos de confiança de qualquer métrica ficam largos demais para validação em prazo razoável (ver Parte 8 sobre o erro padrão do Sharpe). H1 e H4 são o compromisso: custo baixo o suficiente, amostra grande o suficiente, padrões menos dependentes de broker. Recomendação: H4 como timeframe de decisão, H1 para refinamento de entrada e gestão de stop.

---

## Parte 5: Indicadores

Todos os indicadores da lista são transformações do preço (e, no caso do VWAP, de um volume que não existe no spot). A pergunta certa não é "qual indicador funciona", e sim quanta informação não redundante cada família carrega. São três famílias:

Família de tendência: SMA, EMA, Ichimoku, SuperTrend. Tudo aqui é suavização de preço com pesos diferentes. Ichimoku é um conjunto de médias deslocadas; SuperTrend é ATR sobre média. Nenhum dos dois tem evidência independente da família. Fique com uma medida: inclinação e distância normalizada de uma EMA \[M como feature de estado de tendência\].

Família de momentum: RSI, MACD, ADX. RSI e MACD medem a mesma coisa (velocidade do preço) em escalas diferentes; como gatilho isolado, os testes publicados são desfavoráveis (Park e Irwin, 2007). Como feature normalizada num modelo, RSI é aceitável. ADX é o único com papel distinto: mede força de movimento sem direção, útil como filtro de regime \[M\].

Família de volatilidade: ATR, Bollinger, Keltner, Donchian. Bollinger e Keltner são envelopes (desvio padrão e ATR, respectivamente) e carregam a mesma informação do ATR. ATR é o indicador mais importante de toda a lista, não como sinal, mas como régua: dimensiona posição, define stop e normaliza qualquer outra feature \[F como medida de vol; a previsibilidade da volatilidade é dos fatos mais sólidos da área, Corsi 2009\]. Donchian merece lugar próprio porque define rompimento de forma objetiva e conecta o sistema à evidência de tendência \[M\].

Conjunto final que sobrevive ao corte: ATR, Donchian, inclinação/distância de EMA, ADX. O resto adiciona parâmetros e correlação entre features, que é o combustível do overfitting.

---

## Parte 6: Engenharia de features

O fato central da literatura: direção é quase imprevisível, volatilidade é bastante previsível. Um sistema honesto extrai o máximo do que é previsível (vol, sazonalidade, custo) e pede o mínimo do que não é (direção). Ranking das features da sua lista por poder preditivo documentado:

Primeiro escalão \[F\]. Retornos logarítmicos em múltiplos horizontes (1, 5, 20, 60 barras): é a materialização do momentum, a base com melhor evidência. Volatilidade realizada em janelas curta/média/longa e as razões entre elas: o modelo HAR de Corsi (2009) mostra que vol passada em três escalas prevê vol futura com precisão alta. Sazonalidade intradiária e de sessão: Andersen e Bollerslev (1998) documentam o padrão de volatilidade por hora do dia em FX com estabilidade notável; sessão (Ásia/Londres/NY) como dummy é obrigatória. Dummies de calendário econômico: o efeito de anúncios sobre vol e spread é dos resultados mais replicados (Andersen, Bollerslev, Diebold e Vega, 2003).

Segundo escalão \[M\]. ATR normalizado e distância do preço à média em unidades de ATR (estado de tendência). Inclinação de médias. Compressão de volatilidade (largura de banda em percentil histórico) como precursora de expansão. Tick volume: não é volume real, mas verificações contra volume de futuros de câmbio mostram correlação alta; trate como proxy de atividade, nunca como fluxo. Regime de mercado via HMM ou via regra simples de vol/ADX (Ang e Timmermann, 2012). Volatilidade implícita e risk reversals de opções de câmbio têm literatura como preditores, mas o dado é caro e difícil no varejo; deixe documentado como extensão futura.

Terceiro escalão \[E ou fraco\]. Dia da semana: efeitos pequenos e instáveis. Spread corrente: pouca previsão, muito valor operacional (é filtro, não feature preditiva). Breakout strength: útil, mas redundante com distância normalizada e Donchian.

Regra de engenharia: menos de 20 features finais, todas estacionárias (retornos e razões, nunca preço bruto), todas normalizadas por vol, e com correlação entre elas auditada. Fractional differentiation (López de Prado, 2018, cap. 5\) é opcional se você quiser reter memória sem perder estacionariedade.

---

## Parte 7: Machine Learning

| Modelo | Dados exigidos | Risco de overfitting | Interpretabilidade | Veredito para este projeto |
| :---- | :---- | :---- | :---- | :---- |
| Logistic Regression | baixo | baixo | alta | Baseline obrigatório |
| Random Forest | médio | médio | média (importâncias) | Baseline forte |
| XGBoost / LightGBM / CatBoost | médio | médio-alto (controlável) | média (SHAP) | Escolha principal |
| SVM | médio | médio | baixa | Sem vantagem atual, escala mal |
| HMM | baixo | baixo | média | Bom uso: regime, não retorno |
| LSTM | alto | alto | baixa | Raramente supera GBM em tabular |
| Transformers / TFT | muito alto | alto | baixa | Dados insuficientes num projeto pessoal |
| DQN / PPO / SAC | muito alto | severo | baixa | Experimental; overfitting de simulador |

A justificativa em três pontos. Grinsztajn, Oyallon e Varoquaux (2022) mostram que em dados tabulares de porte médio, exatamente o caso de features de FX, árvores com gradient boosting continuam superando redes profundas. Gu, Kelly e Xiu (2020), no maior estudo de ML em precificação de ativos, encontram que árvores e redes rasas lideram, e que o R² preditivo é minúsculo mesmo quando economicamente relevante: calibre sua expectativa por isso. E López de Prado (2018) fornece o protocolo que separa ML útil de ML alucinado em finanças: rotulagem por barreira tripla, purged cross-validation com embargo e, principalmente, meta-labeling, em que o modelo não decide direção, apenas estima a probabilidade de um sinal primário transparente dar certo, controlando filtro e tamanho.

Meta-labeling é a arquitetura recomendada aqui por uma razão de sobrevivência: mantém o núcleo do sistema interpretável e auditável (uma regra de tendência que você entende), e confina o ML ao papel em que ele erra com menos custo. Se o LightGBM degradar, você volta ao baseline de regras sem reescrever o sistema.

Sobre RL: PPO/SAC/DQN precisam de milhões de interações, e a única forma de obtê-las é um simulador do mercado, que herda todos os defeitos do seu backtest e os amplifica, porque o agente aprende a explorar as imperfeições do simulador (fills otimistas, spread constante, ausência de impacto). Moody e Saffell (2001) seguem sendo citados justamente porque quase nada reprodutível veio depois. Classificação: \[X\], fora do projeto.

---

## Parte 8: Validação estatística

O protocolo abaixo é sequencial e cada etapa tem poder de veto. A ordem importa.

1. **Lockbox.** Separe os últimos 2 anos de dados e não os toque até a etapa 8\. Uma única leitura, no fim. Se você "espiar", o teste morreu.  
     
2. **Registro de tentativas.** Todo backtest, toda configuração, toda feature testada entra num log com data e resultado. Sem esse número, o Deflated Sharpe Ratio da etapa 6 é incalculável e o seu processo inteiro vira data snooping inauditável. Este é o item mais barato e mais negligenciado da lista.  
     
3. **Purged K-Fold com embargo** (López de Prado, 2018, cap. 7\) para seleção de features e hiperparâmetros. Cross-validation comum vaza informação em séries temporais porque os rótulos se sobrepõem no tempo; purga e embargo eliminam o vazamento.  
     
4. **CPCV** (Combinatorial Purged Cross-Validation, cap. 12\) para obter uma distribuição de Sharpe em vez de um número único. Um Sharpe médio de 0,6 com desvio de 0,2 entre caminhos é um sistema; 0,6 com desvio de 0,8 é sorte de caminho único.  
     
5. **Walk-Forward** rolante como ensaio geral do processo de produção: re-otimize com a mesma regra e a mesma frequência que você usará ao vivo, nunca "a melhor janela achada depois". O WFO testa o seu procedimento, não só os parâmetros.  
     
6. **Correções de múltiplos testes.** White (2000, Reality Check) ou Hansen (2005, SPA) se você comparar várias estratégias. Deflated Sharpe Ratio e Probabilistic Sharpe Ratio (Bailey e López de Prado, 2014): exija PSR \> 0,95 contra benchmark zero usando o número real de tentativas do seu log. Lembre o limiar de Harvey, Liu e Zhu (2016): t \> 3\.  
     
7. **Monte Carlo em três eixos.** Reamostragem em blocos da sequência de trades (distribuição de drawdown e tempo debaixo d'água); perturbação de parâmetros em ±20% (se o resultado colapsa, você otimizou um pico, não um platô); e stress de custos: spread ×2, slippage de 1 a 2 spreads em toda ordem a mercado, swap dobrado. Sobreviveu com Sharpe \> 0 no stress? Prossiga.  
     
8. **Amostra mínima e leitura do lockbox.** O erro padrão do Sharpe é aproximadamente sqrt((1 \+ SR²/2)/n) (Lo, 2002); com 100 trades e SR verdadeiro 0,5, você mal distingue o sistema de zero. Exija 200+ trades no histórico de teste. Só então rode uma vez no lockbox e aceite o resultado, seja ele qual for.

Especificidades do MT5: use o Strategy Tester em "Every tick based on real ticks" para realismo de execução, sabendo que a profundidade do histórico de ticks do broker é limitada; para pesquisa longa, importe ticks da Dukascopy ou TrueFX num símbolo custom e depois confirme no feed do broker. O otimizador genético do tester é uma máquina de overfitting se usado sem as etapas 2-7; use-o para explorar, nunca para decidir. E o cálculo estatístico (CPCV, DSR, Monte Carlo) faça em Python, exportando os trades do tester; o MT5 não oferece isso nativamente.

---

## Parte 9: Gestão de risco institucional

Números concretos primeiro, justificativa depois. Para um sistema de edge desconhecido em conta pessoal:

Risco por operação de 0,25 a 0,5% do equity, calculado por distância do stop em ATR: lote \= (equity × risco%) / (k × ATR em valor monetário), com k entre 2 e 3\. Limites de perda em cascata: dia a \-2%, novas entradas bloqueadas até a virada do dia; semana a \-4%, sistema pausado e revisão obrigatória; mês a \-8%, sistema desligado e auditoria completa antes de religar. Circuit breaker automático adicional: se a perda acumulada ou a sequência de perdas exceder o percentil 99 da distribuição de Monte Carlo da Parte 8, o sistema se desliga sozinho, porque está se comportando fora do que foi validado. Redução automática de lote: metade do risco após atingir 70% do limite mensal.

Volatility targeting no nível do portfólio: alvo de 8 a 12% de vol anualizada, escalando a exposição pela vol realizada de 20 dias. A evidência aqui pede honestidade: Moreira e Muir (2017) mostram ganho de Sharpe em vários fatores, Cederburg et al. (2020) questionam a solidez fora da amostra, e Harvey et al. (2018) encontram que, em FX especificamente, o ganho de Sharpe é pequeno, mas o corte de caudas e drawdowns é real. Classificação \[M\], adotado pelo benefício de cauda, não de retorno.

Kelly fracionado como teto, nunca como alvo: ≤ ¼ do Kelly estimado (Thorp, 2006). A estimativa de edge tem erro enorme e Kelly cheio com edge superestimado é receita de ruína \[F a favor da fração baixa\].

Exposição agregada por moeda, não por par: EURUSD comprado \+ EURJPY comprado \= exposição dupla em EUR. Some as posições por moeda e limite cada moeda a, por exemplo, 2 unidades de risco. Correlação rolante de 60 dias entre os pares do portfólio; acima de 0,7, trate os dois como um só para fins de limite.

VaR (95/99) e Expected Shortfall diários entram como monitoramento e alarme, não como mecanismo primário de sizing: com 5-6 instrumentos e sizing por ATR, o VaR paramétrico adiciona pouco à decisão, mas serve de verificação independente de que a exposição total está onde deveria \[E institucional, F como conceito\].

---

## Parte 10: Notícias macroeconômicas

A evidência é inequívoca sobre o mecanismo: Andersen, Bollerslev, Diebold e Vega (2003) mostram ajuste de preço em segundos após anúncios, com salto de volatilidade e, nos dados de microestrutura, alargamento de spread de 3 a 10 vezes por alguns minutos, além de slippage praticamente garantido em stops. NFP, CPI americano, decisões e comunicados do FOMC, decisões de BCE/BoE/BoJ e PCE são o tier 1; PMI, PIB e discursos são tier 2, com efeito menor e menos confiável.

A decisão de projeto não é "prever a notícia", é reconhecer que as condições de custo sob as quais o sistema foi validado deixam de existir na janela do evento. Política recomendada: bloquear novas entradas de 15 minutos antes a 30 minutos depois de eventos tier 1 nas moedas envolvidas; para posições abertas, teste as duas políticas no backtest com custos estressados (manter com o stop original vs. achatar antes do evento) e adote a vencedora por par. Operar a notícia em si é outra classe de sistema, dependente de latência, e fica fora deste projeto. Reduzir lote em vez de suspender é meio-termo que herda o pior dos dois mundos: você ainda toma o slippage, só que menor.

Implementação: o MQL5 tem calendário econômico nativo (funções CalendarValueHistory, CalendarEventById etc.), o que dispensa feed externo em produção. Ressalva prática que custa caro descobrir tarde: essas funções não operam dentro do Strategy Tester; para backtest, exporte o calendário para arquivo e leia no EA.

---

## Parte 11: Arquitetura completa

Fluxo: dados → sanidade → features → regime → sinal → filtros → risco → execução → logging → monitoramento → auditoria.

Divisão de responsabilidades recomendada: pesquisa e treino em Python (pandas, LightGBM, scikit-learn, backtester próprio com o modelo de custos da Parte 1); produção 100% dentro do MT5 em MQL5, com o modelo exportado em ONNX, que o MT5 executa nativamente desde 2023\. A alternativa (Python vivo mandando ordens via pacote MetaTrader5) funciona, mas adiciona um processo, uma ponte e dois pontos de falha a um sistema que precisa rodar sozinho por anos; use-a para pesquisa e coleta, não para execução.

Bloco a bloco. Aquisição: ticks do broker em produção; Dukascopy/TrueFX desde 2010+ para pesquisa, importados como símbolo custom. Sanidade: detecção de gaps, spikes de tick isolados, mudanças de horário do servidor e DST (o horário do servidor MT5 raramente é UTC; normalize tudo para UTC na pesquisa). Features e regime: os da Parte 6, com o estado de regime (tendência/neutro por ADX-vol ou HMM) calculado antes do sinal. Sinal: regra primária de tendência; meta-label opcional por cima. Filtros na ordem: spread corrente ≤ teto por par (ex.: percentil 75 do histórico daquela hora), volatilidade dentro da banda validada, fora da janela de notícias, sessão permitida. Risco: tudo da Parte 9, implementado como camada que pode vetar ou reduzir qualquer ordem. Execução: ordens a mercado com deviation máximo definido, tratamento explícito de todos os retcodes relevantes (requote, off quotes, no money), retries idempotentes com verificação de posição antes de reenviar, e reconciliação periódica entre o estado interno do EA e as posições reais do terminal.

Logging: cada decisão gera uma linha estruturada (timestamp UTC, par, snapshot das features, sinal, probabilidade do meta-label, lote, preço pedido, preço executado, slippage, spread no momento, retcode, equity). CSV ou SQLite local. Isso é a matéria-prima da auditoria e do monitoramento; sem isso você não distingue "o edge morreu" de "a execução piorou".

Monitoramento online, com limiares definidos antes de ir ao vivo: tracking error entre o P\&L real e o esperado pelo backtest (alerta acima de 2 desvios); PSI das features live contra a distribuição de treino (revisão acima de 0,25); slippage e spread médios semanais contra o histórico (investigar o broker acima de 1,5×); rolling Sharpe de 60 trades contra a banda do Monte Carlo. Alertas via push do MT5 ou Telegram. Infra: VPS estável perto do servidor do broker; em H1/H4 a latência importa pouco, o uptime e a reconexão automática importam muito.

---

## Parte 12: Roadmap

| Fase | Duração típica | Entregável | Gate para avançar |
| :---- | :---- | :---- | :---- |
| 0\. Dados e custos | 2-4 sem | Ticks 2010+ de 6 pares; modelo de spread por hora/par; medição de swap e slippage do broker | Custos medidos, não assumidos |
| 1\. Baseline de regras | 4 sem | Donchian/TSMOM H4 no portfólio, com custos completos | Sharpe líquido \> 0 e drawdown tolerável em 10+ anos |
| 2\. Risco e filtros | 3-4 sem | Camada da Parte 9 \+ filtros da Parte 11 sobre o baseline | Caudas e DD melhoram sem destruir o retorno |
| 3\. Meta-label ML | 6-8 sem | LightGBM sobre o sinal primário, protocolo purged | Supera o baseline líquido em CPCV com DSR \> 0; senão, fica o baseline |
| 4\. Validação completa | 4 sem | WFO, Monte Carlo, stress, DSR/PSR com o log de tentativas, leitura única do lockbox | Todos os critérios pré-registrados atendidos |
| 5\. Incubação em demo | 3-6 meses | Sistema completo em demo com gravação de spread/slippage reais | Distribuição dos trades live compatível com o backtest (teste KS), slippage dentro do assumido |
| 6\. Live mínimo | 3 meses | 0,01 lote, sistema idêntico | Tracking error dentro da banda |
| 7\. Escala | gradual | Aumento por degraus até o risco alvo | Cada degrau só após N trades dentro da banda |
| Contínuo | mensal/trimestral/anual | Revisão leve mensal; re-treino trimestral com protocolo fixo; revisão profunda anual | Critérios de aposentadoria não atingidos |

Dois princípios atravessam todas as fases. Pré-registro: os critérios de cada gate são escritos antes do teste, senão você vai racionalizar qualquer resultado. E proibição de ajuste ad hoc: mudança no sistema em produção só na janela trimestral, com o mesmo protocolo de validação; mexer no robô depois de uma semana ruim é a forma mais comum de transformar variância em prejuízo estrutural. Prazo total realista até capital relevante: 9 a 15 meses. Menos que isso significa que alguma etapa de validação foi pulada.

---

## Parte 13: O projeto que eu construiria hoje

Objetivo: sobreviver 10 anos com estabilidade estatística. Cada componente com sua classificação de evidência.

**Núcleo de sinal \[F/M\].** Time-series momentum com rompimento de canal Donchian em H4 (entrada em rompimento do canal de \~55 barras ou reversão de momentum multi-horizonte; saída por canal oposto curto ou trailing de 2,5-3 ATR), sobre EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD e XAUUSD a meio peso. Base: Moskowitz, Ooi e Pedersen (2012); Hurst, Ooi e Pedersen (2017); Osler (2003) para a mecânica microestrutural dos rompimentos. É a única fundação com evidência forte que o varejo consegue executar.

**Camada de ML como meta-label \[M na metodologia, X no ganho\].** LightGBM estimando a probabilidade de sucesso de cada sinal primário, com as features da Parte 6, rotulagem por barreira tripla e validação purged (López de Prado, 2018). Só entra em produção se vencer o baseline líquido de custos sob CPCV com DSR positivo. Se não vencer, o sistema vai ao vivo só com regras, e isso não é fracasso: é o resultado esperado na maioria das tentativas honestas.

**Regime e filtros \[M/F operacional\].** Filtro de regime por vol realizada e ADX (HMM como refinamento posterior); filtros de spread, sessão e janela de notícias via calendário nativo do MQL5. Base: Ang e Timmermann (2012); Andersen et al. (2003).

**Risco \[F\].** 0,35% por trade com stop em ATR; vol target de 10% a.a. pelo benefício de cauda (Harvey et al., 2018); limites em cascata dia/semana/mês; circuit breaker no percentil 99 do Monte Carlo; teto de ¼ Kelly; agregação de exposição por moeda. É a parte do sistema com a evidência mais forte e a única inteiramente sob seu controle.

**Validação e operação \[F no método\].** Protocolo completo da Parte 8, com log de tentativas desde o primeiro backtest; roadmap da Parte 12 com gates pré-registrados; produção em MQL5 com ONNX, logging estruturado e monitoramento com limiares definidos ex ante. Critérios de aposentadoria escritos antes do primeiro trade real: drawdown acima do percentil 99 validado, ou tracking error persistente por 2 trimestres, encerram o sistema.

Expectativa honesta de desempenho, se tudo der certo: Sharpe líquido entre 0,3 e 0,7, drawdown máximo em torno de 1,5 a 2,5 vezes a vol alvo (15 a 25% com alvo de 10%), e anos negativos inevitáveis; trend following passou 2011-2013 e boa parte de 2018 no vermelho em portfólios profissionais, e um portfólio só de FX é menos diversificado que isso. A literatura não oferece nada melhor que isto para o seu contexto, e desconfie de quem oferecer: o desenho acima não garante edge, ele garante que, se o edge não existir ou morrer, você vai descobrir cedo, perdendo pouco, com dados para entender o porquê. Em um horizonte de 10 anos, essa propriedade vale mais que qualquer backtest bonito.

---

## Referências

Andersen, Bollerslev (1998). Deutsche Mark-Dollar Volatility. *Journal of Finance*. Andersen, Bollerslev, Diebold, Vega (2003). Micro Effects of Macro Announcements. *American Economic Review*. Ang, Timmermann (2012). Regime Changes and Financial Markets. *Annual Review of Financial Economics*. Avellaneda, Stoikov (2008). High-frequency trading in a limit order book. *Quantitative Finance*. Bailey, Borwein, López de Prado, Zhu (2014). Pseudo-Mathematics and Financial Charlatanism. *Notices of the AMS*. Bailey, López de Prado (2014). The Deflated Sharpe Ratio. *Journal of Portfolio Management*. Baillie, Bollerslev (1989). Common Stochastic Trends in a System of Exchange Rates. *Journal of Finance*. Brunnermeier, Nagel, Pedersen (2008). Carry Trades and Currency Crashes. *NBER Macroeconomics Annual*. Cederburg, O'Doherty, Wang, Yan (2020). On the performance of volatility-managed portfolios. *Journal of Financial Economics*. Corsi (2009). A Simple Approximate Long-Memory Model of Realized Volatility (HAR). *Journal of Financial Econometrics*. Diebold, Gardeazabal, Yilmaz (1994). On Cointegration and Exchange Rate Dynamics. *Journal of Finance*. Evans, Lyons (2002). Order Flow and Exchange Rate Dynamics. *Journal of Political Economy*. Gatev, Goetzmann, Rouwenhorst (2006). Pairs Trading. *Review of Financial Studies*. Grinsztajn, Oyallon, Varoquaux (2022). Why do tree-based models still outperform deep learning on tabular data? *NeurIPS*. Gu, Kelly, Xiu (2020). Empirical Asset Pricing via Machine Learning. *Review of Financial Studies*. Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, van Hemert (2018). The Impact of Volatility Targeting. *Journal of Portfolio Management*. Harvey, Liu, Zhu (2016). ...and the Cross-Section of Expected Returns. *Review of Financial Studies*. Hurst, Ooi, Pedersen (2017). A Century of Evidence on Trend-Following Investing. *Journal of Portfolio Management*. Lempérière, Deremble, Seager, Potters, Bouchaud (2014). Two Centuries of Trend Following. *Journal of Investment Strategies*. Lo (2002). The Statistics of Sharpe Ratios. *Financial Analysts Journal*. Lo, Mamaysky, Wang (2000). Foundations of Technical Analysis. *Journal of Finance*. López de Prado (2018). *Advances in Financial Machine Learning*. Wiley. Marshall, Young, Rose (2006). Candlestick technical trading strategies. *Journal of Banking & Finance*. McLean, Pontiff (2016). Does Academic Research Destroy Stock Return Predictability? *Journal of Finance*. Menkhoff, Sarno, Schmeling, Schrimpf (2012). Currency Momentum Strategies. *Journal of Financial Economics*. Menkhoff, Taylor (2007). The Obstinate Passion of Foreign Exchange Professionals. *Journal of Economic Literature*. Moody, Saffell (2001). Learning to Trade via Direct Reinforcement. *IEEE Transactions on Neural Networks*. Moreira, Muir (2017). Volatility-Managed Portfolios. *Journal of Finance*. Moskowitz, Ooi, Pedersen (2012). Time Series Momentum. *Journal of Financial Economics*. Neely, Weller (2013). Lessons from the evolution of foreign exchange trading strategies. *Journal of Banking & Finance*. Novy-Marx, Velikov (2016). A Taxonomy of Anomalies and Their Trading Costs. *Review of Financial Studies*. Osler (2003). Currency Orders and Exchange Rate Dynamics. *Journal of Finance*. Osler (2005). Stop-loss orders and price cascades in currency markets. *Journal of International Money and Finance*. Park, Irwin (2007). What Do We Know About the Profitability of Technical Analysis? *Journal of Economic Surveys*. Thorp (2006). The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market. *Handbook of Asset and Liability Management*. White (2000). A Reality Check for Data Snooping. *Econometrica*. BIS (2022). Triennial Central Bank Survey of Foreign Exchange Markets.  
