# Arquitetura do Sistema de Trading Forex MT5

> Documento de projeto (Fase de arquitetura). **Nenhuma implementação até aprovação.**
> Fonte de requisitos: `robo_forex_mt5_evidencias.md` (a "pesquisa"). Onde houver conflito, prevalece a solução de maior nível de evidência.
> Status: **RASCUNHO PARA APROVAÇÃO** · Data: 2026-07-20

---

## 0. Escopo e princípios

- Uso **local**, máquina única. Produção deve rodar sozinha por anos.
- Ordem de prioridade (herdada da instrução): **Robustez > Reprodutibilidade > Evidência > Manutenibilidade > Performance > Complexidade mínima**.
- Metodologia por feature (10 passos): Arquitetura → Discussão → Implementação → Revisão → Testes unitários → Testes de integração → Backtests → Validação estatística → Aprovação → próxima.
- Nenhuma feature nova começa antes da anterior validada. Falhou uma etapa, corrige antes de seguir.
- **Anti-overfitting é requisito de primeira classe**, não um passo final (ver §7).

---

## 1. Requisitos Funcionais (RF)

Rastreabilidade: cada RF cita a Parte da pesquisa que o origina.

### Dados e custos
- **RF-01** Ingestão de ticks: broker (produção); Dukascopy/TrueFX 2010+ (pesquisa) importados como símbolo custom. *(P8, P11, P12-0)*
- **RF-02** Sanidade de dados: detecção de gaps, spikes de tick isolados, mudança de horário do servidor e DST; **normalizar tudo para UTC**. *(P11)*
- **RF-03** Modelo de custos de 3 camadas: **spread** (variável por sessão/evento), **slippage** (assimétrico, pior em stops sob notícia), **swap** (triplo na quarta). Custos **medidos, não assumidos**. *(P1, P12-0)*

### Sinal e features
- **RF-04** Conjunto de indicadores enxuto: **ATR, Donchian, inclinação/distância de EMA, ADX**. *(P5)*
- **RF-05** Pipeline de features: **< 20 features**, estacionárias (retornos/razões, nunca preço bruto), normalizadas por vol, com correlação auditada. Retornos log multi-horizonte; vol realizada curta/média/longa + razões (HAR); sazonalidade intradiária/sessão; dummies de calendário econômico; ATR normalizado; compressão de vol; tick volume como proxy; regime. *(P6)*
- **RF-06** Detecção de regime: regra vol/ADX (HMM como refinamento posterior), calculada **antes** do sinal. *(P6, P11)*
- **RF-07** Sinal primário: **TSMOM com rompimento de canal Donchian em H4** (entrada em rompimento ~55 barras ou reversão de momentum multi-horizonte; saída por canal oposto curto ou trailing 2,5–3 ATR). *(P13)*
- **RF-08** Meta-label opcional: LightGBM estima probabilidade de sucesso do sinal primário; rotulagem por **barreira tripla**; validação purged. **Só vai a produção se vencer o baseline líquido sob CPCV com DSR positivo.** *(P7, P13)*

### Filtros e risco
- **RF-09** Cadeia de filtros, nesta ordem: spread corrente ≤ teto por par (ex.: p75 do histórico daquela hora) → vol dentro da banda validada → fora da janela de notícias → sessão permitida. *(P11)*
- **RF-10** Camada de risco (pode vetar/reduzir qualquer ordem): 0,25–0,5%/trade (default 0,35%), sizing por ATR `lote = (equity × risco%)/(k × ATR$)`, k∈[2,3]. *(P9, P13)*
- **RF-11** Limites em cascata: dia −2% (bloqueia novas entradas), semana −4% (pausa + revisão), mês −8% (desliga + auditoria). Redução de lote à metade ao atingir 70% do limite mensal. *(P9)*
- **RF-12** Circuit breaker automático: desliga se perda acumulada/sequência exceder **p99 da distribuição de Monte Carlo** validada. *(P9)*
- **RF-13** Volatility targeting de portfólio: alvo 8–12% a.a., escalando pela vol realizada de 20 dias. *(P9)*
- **RF-14** Kelly fracionado como **teto**, ≤ ¼ Kelly estimado. *(P9)*
- **RF-15** Exposição agregada **por moeda** (não por par); limite por moeda (ex.: 2 unidades de risco); correlação rolante 60d, acima de 0,7 tratar dois pares como um. *(P9)*
- **RF-16** VaR (95/99) e Expected Shortfall diários como **monitoramento/alarme**, não sizing primário. *(P9)*

### Notícias
- **RF-17** Bloquear novas entradas de −15min a +30min de eventos tier 1 nas moedas envolvidas. Posições abertas: testar "manter stop original" vs "achatar antes" e adotar a vencedora por par. *(P10)*
- **RF-18** Calendário: `CalendarValueHistory`/`CalendarEventById` em produção; **exportar calendário para arquivo** para backtest (funções não operam no Strategy Tester). *(P10)*

### Execução (produção MT5)
- **RF-19** Ordens a mercado com `deviation` máximo definido; tratamento explícito de retcodes (requote, off quotes, no money). *(P11)*
- **RF-20** Retries idempotentes com verificação de posição antes de reenviar; reconciliação periódica estado interno do EA ↔ posições reais do terminal. *(P11)*

### Observabilidade
- **RF-21** Logging estruturado por decisão: timestamp UTC, par, snapshot das features, sinal, prob. do meta-label, lote, preço pedido/executado, slippage, spread, retcode, equity. CSV ou SQLite local. *(P11)*
- **RF-22** Monitoramento online com limiares **definidos ex ante**: tracking error P&L real vs backtest (>2σ), PSI features live vs treino (>0,25), slippage/spread semanais vs histórico (>1,5×), rolling Sharpe 60 trades vs banda MC. Alertas via push MT5/Telegram. *(P11)*

### Validação (pipeline de pesquisa)
- **RF-23** **Lockbox**: últimos 2 anos isolados, leitura **única** no fim. *(P8)*
- **RF-24** **Registro de tentativas**: toda config/feature/backtest logada com data e resultado (insumo do DSR). *(P8)*
- **RF-25** **Purged K-Fold com embargo** para seleção de features/hiperparâmetros. *(P8)*
- **RF-26** **CPCV** para obter distribuição de Sharpe. *(P8)*
- **RF-27** **Walk-Forward** rolante como ensaio do processo de produção. *(P8)*
- **RF-28** Correções de múltiplos testes: White Reality Check / Hansen SPA; **PSR > 0,95**; limiar **t > 3**; DSR usando o nº real de tentativas. *(P8)*
- **RF-29** **Monte Carlo** em 3 eixos: reamostragem em blocos (DD e tempo submerso), perturbação de parâmetros ±20%, stress de custos (spread ×2, slippage 1–2 spreads, swap ×2). *(P8)*
- **RF-30** Amostra mínima: **≥ 200 trades** no histórico de teste. *(P8)*

### Portfólio e timeframe
- **RF-31** Portfólio: EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD; XAUUSD a meio peso (opcional). *(P3, P13)*
- **RF-32** Timeframe: **H4** decisão, **H1** refinamento de entrada/stop. *(P4)*

---

## 2. Requisitos Não-Funcionais (RNF)

- **RNF-01 Reprodutibilidade**: seeds fixos, versões pinadas, dados versionados, experimentos versionados; qualquer resultado reexecutável bit-a-bit (dentro de tolerância numérica declarada).
- **RNF-02 Separação de responsabilidades**: pesquisa / treino / validação / execução em módulos distintos e testáveis isoladamente.
- **RNF-03 SOLID, baixo acoplamento, alta coesão**; sem abstração especulativa (interface com 1 implementação só se houver 2º runtime real — caso do split Python/MQL5).
- **RNF-04 Configuração por arquivos** (YAML), sem constantes mágicas espalhadas.
- **RNF-05 Logging estruturado** em todas as camadas.
- **RNF-06 Testes automatizados** (unitários + integração) como gate de cada fase.
- **RNF-07 Auditabilidade**: attempt log + logs de decisão permitem distinguir "edge morreu" de "execução piorou".
- **RNF-08 Robustez operacional**: uptime, reconexão automática, tolerância a falhas de rede/broker.
- **RNF-09 Manutenibilidade de longo prazo** (anos): documentação completa, código limpo, contratos entre módulos explícitos.
- **RNF-10 Complexidade mínima necessária**: cada tecnologia nova exige justificativa técnica registrada.
- **RNF-11 Segurança local**: credenciais fora do repositório; nada de segredos em código/logs.

---

## 3. Inconsistências, lacunas e riscos identificados

Numerados para virarem itens de decisão/tarefa. **[R]** risco · **[L]** lacuna · **[D]** decisão pendente.

- **R-01 (crítico) Paridade Python↔MQL5.** Pesquisa/backtest em Python, produção em MQL5+ONNX. Se o cálculo de features, o modelo de custos e a lógica de execução divergirem entre os dois runtimes, **backtest ≠ live** e toda a validação vira ficção. → Mitigação arquitetural em §5.4 (spec única + cross-check "golden set" + reconciliação backtester Python vs Strategy Tester).
- **R-02 (crítico) Feed de dados divergente.** Edge medido em ticks Dukascopy/TrueFX pode não existir no feed do broker (spread/slippage diferentes). A pesquisa já alerta: "confirme no feed do broker". → Gate em Fase 0.3/0.4.
- **R-03 (alto) Custos medidos exigem conta demo antes de qualquer backtest.** Swap e slippage só se medem operando/observando. Sem broker definido, a Fase 0 não fecha. → **D-01**.
- **R-04 (alto) Suficiência amostral para o meta-label.** H4 gera 50–150 trades/ano no portfólio; barreira tripla + purged CV + ≥200 trades por teste podem deixar o ML sem amostra estatisticamente honesta. → Verificar contagem real de trades do baseline **antes** de investir na Fase 3; ML é condicional.
- **R-05 (médio) Calendário não roda no Strategy Tester.** Filtro de notícias no backtest depende de export para arquivo; fidelidade backtest↔live do filtro precisa ser testada. *(RF-18)*
- **R-06 (médio) Horário do servidor MT5 ≠ UTC + DST.** Erro silencioso clássico. Normalização UTC é pré-condição de features de sessão/sazonalidade. *(RF-02)*
- **R-07 (médio) Testabilidade do MQL5.** Não há framework de teste unitário maduro para MQL5 como em Python. → Estratégia: manter o máximo de lógica em Python (validado), portar para MQL5 o mínimo, e cobrir MQL5 por testes de reconciliação/golden-set, não unitários finos.
- **R-08 (médio) XAUUSD não é FX.** Gaps de fim de semana e caudas exigem tratamento à parte; entra a meio peso e opcional. *(RF-31)*
- **R-09 (médio) Reprodutibilidade de dados de mercado.** Tick histórico de broker tem profundidade limitada; Dukascopy pode ser revisado. → Congelar snapshots versionados dos datasets de pesquisa (hash).
- **L-01 Ambiente não especificado:** MT5 instalado? Python disponível? Conta (demo/real), corretora, moeda da conta, capital. → **D-01, D-02**.
- **L-02 Ferramenta de versionamento de experimentos** não definida (attempt log em SQLite/CSV vs MLflow). → **D-03** (recomendo mínimo).
- **L-03 Política de "posição aberta durante notícia"** é definida por par via backtest (RF-17) — não decidível a priori; vira sub-tarefa da Fase 2.
- **L-04 Fonte de tick de pesquisa** (Dukascopy vs TrueFX vs histórico do broker) não fixada. → **D-04**.
- **D-05 Escopo de ML agora vs depois:** comprometer Fase 3 ou tratá-la como estritamente condicional ao gate da Fase 1/2 (recomendo condicional, alinhado à pesquisa).

**Refinamento justificado vs Parte 12:** a pesquisa coloca a validação completa na Fase 4. Porém os *primitivos* estatísticos (attempt log, purged CV, CPCV, Monte Carlo, DSR) são necessários para tornar o **gate da Fase 1 significativo** — "Sharpe líquido > 0 em 10+ anos" sem distribuição de Sharpe e stress de custos é exatamente o backtest bonito que a Parte 8 condena. Por isso proponho **construir o toolkit de validação na Fase 0** e aplicá-lo em cada gate; a **leitura do lockbox permanece única, no fim (Fase 4)**. Justificativa: maior evidência (Parte 8) sobre conveniência de cronograma.

---

## 4. Visão de módulos (responsabilidades, SOLID)

Cada bloco é uma unidade coesa, testável isoladamente, acoplada por contratos de dados explícitos.

| Módulo | Responsabilidade única | Runtime |
| :-- | :-- | :-- |
| `DataSource` | Fornecer ticks/barras brutos (broker, Dukascopy, TrueFX) | Py (pesquisa) / MQL5 (prod) |
| `Sanitizer` | Gaps, spikes, DST, normalização UTC, qualidade | Py + MQL5 (espelhado) |
| `BarBuilder` | Ticks → barras H1/H4 consistentes | Py + MQL5 |
| `FeaturePipeline` | Features estacionárias/normalizadas (< 20), correlação auditada | Py (treino) + MQL5 (infer) |
| `RegimeDetector` | Estado de regime (vol/ADX; HMM opcional) antes do sinal | Py + MQL5 |
| `SignalGenerator` | Sinal primário TSMOM/Donchian (regra transparente) | Py + MQL5 |
| `MetaLabeler` | Prob. de sucesso (LightGBM→ONNX); **opcional/condicional** | Py treino / MQL5 ONNX infer |
| `FilterChain` | spread→vol→notícia→sessão (ordem fixa) | Py + MQL5 |
| `RiskManager` | Sizing ATR, cascata, circuit breaker, vol target, Kelly, exposição/moeda | Py + MQL5 |
| `ExecutionHandler` | Ordens, retcodes, retries idempotentes, reconciliação | **MQL5 apenas** |
| `Backtester` | Simulação com modelo de custo 3 camadas (coração da pesquisa) | **Py apenas** |
| `ValidationToolkit` | Purged CV, embargo, CPCV, WFO, MC, DSR/PSR, lockbox | **Py apenas** |
| `AttemptRegistry` | Log de toda tentativa (insumo do DSR) | Py |
| `ExperimentTracker` | Versionamento de datasets/params/resultados (seeds, hashes) | Py |
| `Logger` | Linha estruturada por decisão | Py + MQL5 |
| `Monitor` | Tracking error, PSI, slippage/spread, rolling Sharpe, alertas | Py (offline) + MQL5 (online) |

**Spec compartilhada** (fonte única de verdade, consumida pelos dois runtimes): `config/feature_spec.yaml`, `config/cost_model.yaml`, `config/risk_policy.yaml`, `config/filters.yaml`. Python e MQL5 leem a **mesma** spec para minimizar R-01.

---

## 5. Arquitetura de alto nível

### 5.1 Separação por fase do ciclo de vida
```
PESQUISA / TREINO / VALIDAÇÃO  (Python)         PRODUÇÃO (MQL5, no terminal MT5)
------------------------------------            --------------------------------
DataSource(Duka/TrueFX/broker)                  DataSource(broker ticks)
   -> Sanitizer -> BarBuilder                      -> Sanitizer -> BarBuilder
   -> FeaturePipeline -> RegimeDetector            -> FeaturePipeline(ONNX-ready) -> RegimeDetector
   -> SignalGenerator -> [MetaLabeler treino]      -> SignalGenerator -> [MetaLabeler ONNX infer]
   -> FilterChain -> RiskManager                   -> FilterChain -> RiskManager
   -> Backtester (custos 3 camadas)                -> ExecutionHandler (ordens/retcodes/reconc.)
   -> ValidationToolkit (CPCV/MC/DSR/lockbox)      -> Logger + Monitor(online) -> alertas
   -> AttemptRegistry + ExperimentTracker
   ===> exporta: modelo ONNX + specs congeladas ==========>  consumidos pela produção
```

### 5.2 Fluxo em produção (por barra fechada H4/H1)
`dados → sanidade → features → regime → sinal → filtros → risco → execução → logging → monitoramento → auditoria` *(Parte 11)*.

### 5.3 Decisão de runtime — **Produção 100% MQL5 + ONNX** (não Python-vivo)
Justificativa (Parte 11 + prioridade Robustez): a ponte Python↔MT5 adiciona um processo, uma ponte e dois pontos de falha a um sistema que deve rodar sozinho por anos. Python vivo fica **restrito a pesquisa e coleta**. *(RNF-08)*

### 5.4 Mitigação do R-01 (paridade) — mecanismo explícito
1. **Spec única** (§4) lida pelos dois runtimes.
2. **Golden-set cross-check**: um conjunto fixo de barras é processado em Python e em MQL5; asserção de igualdade numérica de features/sinais dentro de tolerância declarada. Vira teste de regressão.
3. **Reconciliação de backtest**: o `Backtester` Python e o **Strategy Tester ("Every tick based on real ticks")** rodam o mesmo período; divergência de P&L/trades deve ficar dentro de tolerância antes de confiar em qualquer número. É um **gate da Fase 0**.

### 5.5 Layout de repositório (proposto, enxuto)
```
Forex/
  config/          # specs YAML (feature, cost, risk, filters) — fonte única
  data/            # snapshots versionados (hash) — NÃO versionar bruto pesado no git
  research/        # Python: datasource, sanitizer, features, backtester, validation
  mt5/             # MQL5: EA, includes espelhando specs, export ONNX
  experiments/     # attempt log (SQLite) + resultados versionados
  tests/           # unitários + integração + golden-set
  docs/            # este arquivo, gates pré-registrados, decisões
```

### 5.7 Gestão de credenciais (RNF-11)
- **Nenhuma senha em código, config versionado ou logs.** Nunca.
- Login no MT5 é feito pelo usuário na GUI do terminal; o Python conecta ao terminal já logado.
- Se login programático for necessário: `config/secrets.yaml` (gitignored, preenchido pelo usuário) ou variável de ambiente. Arquivo de exemplo `config/secrets.example.yaml` com placeholders, sem valores reais.
- Broker: ActivTrades / `ActivTradesMarkets-Server`. Credenciais reais **fora do repositório**.

### 5.6 Stack (mínimo justificado)
- Python: pandas, numpy, scikit-learn, LightGBM, ONNX/skl2onnx, pyarrow. Sem frameworks pesados de orquestração (YAGNI).
- Persistência: **Parquet** (dados), **SQLite** (attempt log/experimentos). *(evita dependência de servidor; local-first)*
- Config: YAML. Testes: pytest. MQL5 nativo no MT5 (ONNX desde 2023).
- Sem MLflow/Airflow por ora — attempt log em SQLite cobre o requisito com muito menos superfície. Reavaliar só se medida a insuficiência. *(RNF-10)*

---

## 6. Contratos entre módulos (para baixo acoplamento)

- `DataSource → Sanitizer`: série de ticks (UTC, bid/ask, volume) + metadados de fonte.
- `Sanitizer → BarBuilder`: ticks limpos + relatório de qualidade (gaps/spikes tratados).
- `FeaturePipeline`: entrada = barras; saída = DataFrame de features **estacionárias, normalizadas, com dicionário de features versionado** (nome, fórmula, janela).
- `SignalGenerator → FilterChain → RiskManager → Execution`: objeto `TradeIntent` (par, direção, força, stop em ATR, prob. meta-label) que cada camada pode **vetar ou reduzir**, nunca ampliar silenciosamente.
- Todo contrato é imutável (dataclass/struct) e logado.

---

## 7. Estratégia transversal de testes e anti-overfitting

Aplicada em **todas** as fases (não é etapa isolada):
- Unitários: pura lógica (features, sizing, cascata de risco, cadeia de filtros) com casos de borda.
- Integração: pipeline dados→sinal→risco→backtest ponta a ponta em dados sintéticos + reais.
- Golden-set Python↔MQL5 (R-01).
- Validação estatística por gate: purged CV/CPCV para seleção; MC + stress de custos antes de aprovar; **DSR com o attempt log real**; lockbox só na Fase 4.
- Checklist de qualidade por fase (obrigatório antes de "concluído"): riscos técnicos, fontes de overfitting, problemas estatísticos, **data leakage**, escalabilidade, manutenibilidade, segurança, aderência a boas práticas.

---

## 8. Fases e gates (pré-registrados, objetivos)

> Regra atravessadora: **critério de gate escrito ANTES do teste**; **proibido ajuste ad hoc** — mudança em sistema aprovado só em janela de revisão, com o mesmo protocolo. Attempt log ativo desde o **primeiro** backtest.

| Fase | Entregável | Gate objetivo (pré-registrado) |
| :-- | :-- | :-- |
| **0.1 Fundação** | Esqueleto repo + config YAML + reprodutibilidade (seeds/versões) + AttemptRegistry (SQLite) | Run reproduzível bit-a-bit; attempt log grava e lê; specs carregam nos dois runtimes (stub) |
| **0.2 Dados** | Ingestão + sanidade de ticks 2010+, 6 pares; normalização UTC/DST | Relatório de qualidade: cobertura ≥X%, gaps/spikes tratados e auditáveis; snapshots com hash |
| **0.3 Custos** | Medição real do broker: spread por hora/par, swap, slippage | **Custos medidos, não assumidos**; modelo de spread por hora/par calibrado com dados do broker |
| **0.4 Backtester** | Backtester Python (custos 3 camadas) + reconciliação com Strategy Tester | Divergência Py↔MT5 em caso de referência ≤ tolerância declarada |
| **0.5 Validação** | ValidationToolkit: purged CV+embargo, CPCV, WFO, MC 3-eixos, DSR/PSR | Toolkit testado em série sintética de propriedades conhecidas (recupera o resultado esperado) |
| **1. Baseline** | Donchian/TSMOM H4 no portfólio, custos completos | **Sharpe líquido > 0** e **DD tolerável** em **10+ anos**; **≥200 trades**; sobrevive stress de custos com Sharpe>0; distribuição CPCV consistente |
| **2. Risco+Filtros** | Camada da P9 + filtros da P11 sobre o baseline | Caudas/DD melhoram **sem destruir** o retorno; circuit breakers e exposição/moeda testados; política de notícia por par escolhida por backtest |
| **3. Meta-label ML** *(condicional)* | LightGBM→ONNX sobre o sinal primário, protocolo purged | **Vence o baseline líquido em CPCV com DSR > 0**; senão, **fica o baseline** (resultado esperado e aceitável) |
| **4. Validação completa** | WFO, MC, stress, DSR/PSR com attempt log, **leitura única do lockbox** | Todos os critérios pré-registrados atendidos; PSR>0,95; **leitura única** aceita como for |
| **5. Incubação demo** | Sistema completo em demo, gravando spread/slippage reais (3–6 meses) | Distribuição de trades live compatível com backtest (**teste KS**); slippage dentro do assumido |
| **6. Live mínimo** | 0,01 lote, sistema idêntico (3 meses) | Tracking error dentro da banda |
| **7. Escala** | Aumento por degraus até risco alvo | Cada degrau só após N trades dentro da banda |
| **Contínuo** | Revisão leve mensal; re-treino trimestral (protocolo fixo); revisão anual | Critérios de aposentadoria (DD>p99 validado; tracking error persistente 2 trimestres) não atingidos |

Cada fase percorre os 10 passos da metodologia antes de "aprovada".

---

## 9. Decisões (resolvidas em 2026-07-20)

- **D-01 Corretora + conta:** ✅ ActivTrades, servidor `ActivTradesMarkets-Server`. **Pendente confirmar: demo ou live? Moeda da conta? Tipo de conta (Standard vs Raw/spread)?** — o tipo de conta afeta o spread e será, de qualquer forma, medido na Fase 0.3.
- **D-02 Ambiente local:** ✅ MT5 e Python instalados.
- **D-03 Versionamento de experimentos:** ✅ Mínimo — **AttemptRegistry em SQLite** + pasta `experiments/` com resultados versionados por hash. Sem MLflow (RNF-10).
- **D-04 Fonte de tick de pesquisa:** ✅ **Dukascopy** (gratuita, profundidade desde ~2003, boa qualidade). Confirmar sempre contra o feed do broker (R-02).
- **D-05 ML:** ✅ Fase 3 **estritamente condicional** ao gate da Fase 1/2.
- **D-06 Portfólio:** ✅ EURUSD/USDJPY/GBPUSD/AUDUSD/USDCAD + XAUUSD meio peso.

### Pendências antes da Fase 0
- Confirmar **demo vs live** e **moeda da conta**.
- **Rotacionar a senha da conta** (foi exposta em chat) — ação do usuário.

---

## 10. O que já está decidido pela pesquisa (não reabrir sem evidência melhor)
- Timeframe H4 (decisão) / H1 (refino); produção MQL5+ONNX; sinal núcleo TSMOM/Donchian; risco por ATR com cascata; validação por CPCV/DSR/lockbox; ML só como meta-label condicional; complexidade mínima.
```
