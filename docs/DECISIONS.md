# Registro de Decisões: Robô Forex/Multi-ativo MT5

> Log durável de decisões (sobrevive à compactação de contexto e reinício de sessão).
> Atualizado pelo comando `/checkpoint`. Foco em DECISÕES e no PORQUÊ, não em implementação.
> Detalhe técnico vivo fica na memória do projeto e em `docs/GATES.md`.

## Metodologia & prioridades (fixas)
- Processo por feature em 10 passos (Arquitetura→Discussão→Implementação→Revisão→Testes
  unit→Integração→Backtests→Validação→Aprovação→próxima). Nada novo antes do anterior validado.
- **Gates pré-registrados** (critério escrito ANTES do teste). Proibido ajuste ad hoc / p-hacking.
- Prioridades: **Robustez > Reprodutibilidade > Evidência > Manutenibilidade > Performance > Simplicidade**.
- Nunca supor requisito importante: perguntar, propor alternativas, aguardar decisão.
- Responder em português.

## Decisões estratégicas (cronológico)
1. **Broker: ActivTrades → Dukascopy** (demo MT5, USD). Motivo: **paridade dado↔execução**
   (os ticks históricos são Dukascopy → o backtest usa o mesmo venue da execução). Dissolveu o R-02.
2. **Produção 100% MQL5 + ONNX** (não Python-vivo), robustez, roda sozinho por anos.
3. **Fase 0 (FX/ouro) concluída:** dados (233M ticks 2010-2026, 6 pares), custos medidos
   (spread par×hora, swap, comissão ECN), backtester + **reconciliação R-01 PASS (75/75 trades
   idênticos, Δ0%)**, toolkit de validação (PSR/DSR, Purged K-Fold, CPCV, Monte Carlo).
4. **Fase 1 REPROVADA + diagnóstico decisivo:** o Donchian (simples e canônico com ATR/ADX/flat)
   dá Sharpe negativo. **O FX não tem edge nem no BRUTO, pré-custo**, só o ouro tem edge bruto,
   mas o **swap** (custo de carregar overnight) o mata. Confirma Partes 2/13 da pesquisa.
5. **★ PIVÔ ESTRATÉGICO (2026-07-25): abandonar FX swing → sistema INTRADAY MULTI-ATIVO.**
   Motivos: (a) FX sem edge; (b) conta pequena (~$1.000) segura ~1 posição; (c) daytrading
   **fecha no dia → swap = 0** (remove o custo que matava o ouro). Melhor fundamentado que FX
   (TSMOM de Moskowitz-Ooi-Pedersen é cross-asset em futuros).
6. **Universo intraday:** XAUUSD + US100 + US500 + GER40 + USOIL (metais/índices/commodity,
   baixa correlação, cobre sessões). **FX fica de fora** (spread come o movimento intraday).
7. **Capital/posições:** **1 posição por vez**, micro lote 0,01; diversificação vem do TEMPO
   (melhor setup do momento em dias/ativos diferentes), não de holdings simultâneas.
8. **Dados: ticks reais profundos.** Ponte MT5 só tem CFDs ~2024+ (raso); o **datafeed Dukascopy
   tem os CFDs fundo (2012+)**, códigos/escala confirmados (US500=USA500IDXUSD, US100=USATECHIDXUSD,
   GER40=DEUIDXEUR, USOIL=LIGHTCMDUSD, todos escala /1000). Ouro já baixado.
9. **★ DOWNLOAD DISPARADO (2026-07-25):** 4 CFDs 2012→hoje via datafeed, em background com
   monitor ao vivo. **Fix de raiz:** o proxy de inspeção SSL desta rede custa ~9s/handshake e
   engasgava com 32 conexões → downloader passou a **reusar 1 conexão TLS por dia (keep-alive,
   24 handshakes/dia → 1)** e concorrência 32→10. Smoke OK nos 4 (preços batem níveis reais).
10. **★ BASELINE ORB fixado (2026-07-25):** spec em `docs/baseline_orb.md`. ORB (range 30min) +
    filtro VWAP + anti-overtrade; **saída alvo 2R fixo** (sem trailing); **TF M15**; flat no fim
    da sessão (swap=0). **Piloto US100 primeiro**, depois os 4. Gate 1i: Sharpe líq>0 c/ PSR>0,95,
    CPCV≥60% caminhos+, DSR>0, MaxDD-p99 no circuit breaker, e **bruto+ por instrumento** (1º corte).

11. **★ ACHADO DE CUSTO decisivo (2026-07-26):** specs medidos do MT5 (`experiments/broker_specs_intraday.json`)
    revelaram que **o config marcava point_value errado** (dizia 1.0; o MT5 mede tick_value 0.001 →
    índices $1/ponto/lote, WTI $100/$1/lote). E o **LOTE MÍNIMO quebra a premissa de $1.000**:
    US100/US500/USOIL exigem mín. 1,0 lote (risco 1,8-6%/trade); **só GER40 (mín. 0,1) cabe** em 0,5-1%.
    → **Piloto trocado de US100 para GER40.** US100/USOIL/US500 ficam no **research, fora do live**
    (backtesta os 5; opera ao vivo só o que cabe no capital, GER40 agora, outros quando a conta crescer).
12. **★ BASELINE ORB, 1º resultado (2026-07-26), `experiments/orb_pilot.json`:** os **4 CFDs são
    BRUTO-POSITIVOS** (o ORB tem edge direcional real em índices/commodities, oposto do FX). Mas o
    **spread decide**: só o **GER40** tem bruto>custo (bruto +$744, spread $515, net +$215 em 14,5a;
    US500/US100/USOIL viram net negativo pelo spread). **GER40 default ainda NÃO passa o gate**
    (Sharpe 0,18 / PSR 0,77 < 0,95, mesmo SEM comissão). Tese confirmada na direção; edge fino.

13. **★ FASE 1i REPROVADA (2026-07-26), `experiments/orb_search_1i.json`:** busca honesta de 81
    configs (seleção OOS via CPCV, DSR deflacionado por |grade|). Melhor config ≈ default. Gate FAIL:
    Sharpe 0,21 mas **PSR 0,81 (<0,95)**, **DSR 0,0001 (≈ruído)**, **MC MaxDD-p99 66% de $1.000**,
    e SEM comissão. O breakout puro intraday não tem edge robusto pós-custo. Gate rejeitou sem p-hacking.

14. **★ FASE 2i REPROVADA (2026-07-26), `experiments/metalabel_2i.json`:** meta-labeling sobre o ORB
    (HistGBM + logística, Purged K-Fold OOS, DSR deflacionado). Filtrou 3606→351 trades mas Sharpe
    0,159 < baseline 0,179, NÃO agrega. **GBM ≈ logística** → não há sinal a extrair, as features não
    predizem o vencedor. **3ª reprovação honesta.** Conclusão convergente: FX (sem edge bruto), ORB puro
    (edge fino, não sobrevive à deflação) e ORB+ML (nada a filtrar), varejo intraday $1.000 nesses
    veículos NÃO tem edge robusto extraível, exatamente como a pesquisa (Parte 8) alertou.

15. **★ DECISÃO ESTRATÉGICA (2026-07-26): Caminho 3 (plataforma de pesquisa) como BASE** + rodar
    2a (reversão intraday) como última hipótese barata. **2a REPROVADA** (`mr_search_2a.json`):
    reversão é **bruto-NEGATIVA nos 4 CFDs** (espelho do ORB, que era bruto-positivo) → os movimentos
    têm leve CONTINUAÇÃO, não reversão. 4ª reprovação honesta; **hipóteses baratas esgotadas**.
    Conclusão firme: varejo intraday $1.000 nesses veículos não tem edge robusto, nem momentum
    (fino) nem reversão (negativo). O projeto adota seu maior valor: **bancada de validação rigorosa**
    que vet ideias antes de arriscar dinheiro. Expansões possíveis (não urgentes, decisão do usuário):
    mais capital + futuros (nova fonte de dados/cost model) ou outra classe de edge com racional a priori.

16. **★ CORREÇÃO + 1º EDGE REAL (2026-07-26):** relendo `quant-system-design.md` vimos que 3 dos 4
    FAILs eram estratégias que o doc EXCLUI (ORB M15 <H1, reversão intraday, FX Donchian). A
    recomendação PRIMÁRIA, **TSMOM D1 cross-asset (Part 13)**, nunca fora testada. Testada agora
    (`tsmom.py`/`run_tsmom.py`/`tsmom_1d.json`): **gross portfolio Sharpe +0,283** (1º bruto+ de
    portfólio!). Universo pleno (8) net −0,97 = FAIL, **swap de índice CFD (~15%/ano) é o assassino**.
    Mas **USDJPY+XAUUSD: net +0,33, 4/5 blocos+, CPCV 79%**, melhor resultado do projeto (borderline:
    PSR 0,93<0,95, **DSR 0,118≪0,95 NÃO cruza a deflação**, net/gross 0,53, breadth 2, seleção ex-post).
    **Proxy futuros (swap=0): 8 ativos net +0,15, índices +0,32** → sistema completo viável em FUTUROS.
17. **★ 2º DOC DE EVIDÊNCIA (`pesquisa-consistencia-trading-algoritmico-1k.md`) CONFIRMA tudo:**
    intraday falsificado; TSMOM é o edge; **trend de varejo universo pequeno → Sharpe 0,3-0,6** (nós
    medimos 0,33 EM CHEIO); swap de varejo compromete overnight; **$1.000 = renda NÃO** (breakeven
    $3,6-7,2k), mas **laboratório SIM com opex≈0** (máquina local+MT5). Consistência exige DSR>0,95 +
    ~2.000 trades. Relatório de fechamento: `docs/relatorio_final.md`.

## Estado atual (2026-07-26)
- **Fase:** 0i ✅; 1i/2i/2a REPROVADAS (intraday); **1d PARCIAL, 1º edge líquido real (TSMOM D1)**.
  **Modo = plataforma (Caminho 3)** + candidato vivo: refinar TSMOM D1 nos ativos de swap benigno
  (ouro/JPY/EUR) rumo a um PASS limpo, e/ou Caminho 1 (futuros) que o proxy swap=0 respalda.
- **Como testar uma ideia nova:** guia completo em **`docs/como_adicionar_estrategia.md`**
  (engine no padrão `orb.py`/`meanrev.py` → runner `run_*_search.py` → gate 1i CPCV/DSR/MC,
  com checklist e as 5 armadilhas). Toda a infra reaproveitada.
- **Entregue:** barras M15/H1 dos 4 CFDs, spread par×hora (`spread_model_intraday.json`), specs MT5,
  engine ORB (`research/orb.py`) + testes, runner (`research/run_orb_pilot.py`). Spec: `docs/baseline_orb.md`.
- **Testes:** 80 verdes. **Custo intraday:** swap=0; spread/hora é o custo rei; comissão do CFD ainda
  NÃO medida (rodado spread-only = otimista).

## Pendências / decisões abertas
- [ ] **Próximo passo do GER40:** validação robusta (CPCV/DSR/MC) + busca de parâmetros DENTRO do
      CPCV (deflacionada por DSR, sem p-hacking) para ver se um config honesto cruza o gate.
- [ ] **Medir comissão real do CFD** na Dukascopy (symbol_info não traz; precisa trade demo com
      mercado aberto OU tabela CFD do broker). Rodado a 0 até lá (otimista).
- [ ] Reconciliar o ORB do GER40 com o MT5 Strategy Tester (R-01) quando o config for aprovado.
- [ ] Validar janelas de sessão com os dados reais (config tem provisório).

## Infra & operacional (decisões de suporte)
- **Monitor operacional** é LOCAL (`research/monitor_server.py`, 8777), Artifact claude.ai não lê
  arquivos locais (CSP). Painel de marcos: `docs/dashboard.html` (Artifact).
- **Docker:** container `linkedinscraper-frontend-1` remapeado 3000→**3001** (a 3000 é do agente
  do Strategy Tester do MT5). UI do scraper agora em localhost:3001.
- **Telegram BLOQUEADO nesta rede** (SSL intercept) → avisos por PushNotification (quando ativo)
  ou no chat. **Segredos** só em `config/secrets.yaml` (gitignored); nunca no template versionável.
- Reinício de sessão mata loop/jobs background → re-armar ao voltar.
