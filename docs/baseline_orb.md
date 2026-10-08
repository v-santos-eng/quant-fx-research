# Baseline ORB: spec concreto (Fase 1i) · passo "Arquitetura"

> Definição implementável e determinística do baseline intraday. Nada aqui é
> discricionário. É o alvo a ser codificado APÓS aprovação (passo Discussão→Implementação).
> Custo: spread par×hora medido + comissão; **swap = 0** (fecha no dia). Reusa
> `bars.py`, `costs.py`, `backtester.py`, validação CPCV/DSR/MC.
> Contexto e trade-offs macro em [desenho_intraday.md](desenho_intraday.md).

## 1. Universo e sessões (de `config/instruments_intraday.yaml`)
| Instrumento | Sessão de operação (UTC) | Abertura que gera o range |
| :-- | :-- | :-- |
| XAUUSD | 07:00–20:00 | Londres 07:00 |
| US100 / US500 | 13:30–20:00 | Cash NY 13:30 |
| GER40 | 07:00–15:30 | Frankfurt/Xetra 07:00 |
| USOIL | 13:00–20:00 | Pit NY 13:00 |

**Corte duro:** toda posição fecha ao fim da sessão do instrumento (flat forçado).
Nunca cruza o rollover → swap = 0, sem gap noturno.

## 2. O sinal (Opening-Range Breakout + filtro de momentum)
Por instrumento, a cada dia de sessão:
1. **Opening Range (OR):** high/low dos primeiros **OR_MIN** minutos após a abertura.
2. **Gatilho:** a barra M15 que **fecha** acima do `OR_high` (long) ou abaixo do `OR_low` (short).
   Fechar (não só tocar) evita o whipsaw de pavio.
3. **Filtro de momentum de sessão (direcional):** só entra se o rompimento concorda com
   o viés da sessão, preço vs **VWAP da sessão**: long exige `close > VWAP`; short `close < VWAP`.
   Descarta rompimentos contra o fluxo do dia (fonte nº1 de falso ORB).
4. **Filtro de qualidade do range (anti-overtrade):** só opera se o OR não for degenerado,
   `OR_width ≥ k · ATR_sessão`. Ranges minúsculos = ruído; ranges enormes = risco/custo ruim.
5. **Uma entrada por instrumento por sessão** (sem re-entrada no baseline). Poucos trades e bons.

## 3. Saída (3 caminhos, o que vier primeiro)
- **Stop:** lado oposto do OR, OU `ATR_MULT · ATR(M15)`, o que for mais apertado.
  Risco por trade alvo **$5–10** (0,5–1% de $1.000) define o lote (0,01 fixo no baseline).
- **Alvo:** `R_MULT · risco` (ex.: 2R). Baseline usa alvo fixo em R; trailing fica p/ uma variante.
- **Tempo:** fim da sessão → fecha a mercado (flat obrigatório).

## 4. Uma posição por vez (entre instrumentos)
O capital força concentração. Regra do baseline: **o primeiro gatilho válido da sessão
ocupa a vaga**; enquanto há posição aberta, ignora sinais dos outros. Determinístico
(ordena por horário de sessão; empate → ordem fixa do config). Seleção "melhor setup"
fica para depois do baseline provar edge.

## 5. Custo aplicado (do `costs.py`, adaptado intraday)
- **Spread:** `spread_model.json` por instrumento×hora (refeito para os CFDs na Fase 0i)
  - entra/sai pagando o spread da hora real do fill.
- **Comissão:** round-trip por lote da tabela Dukascopy do instrumento.
- **Swap = 0** (nunca overnight). **Slippage:** modelado + stress ×2 (real nas Fases 5–6).
- **Regra de viabilidade (pré-registrada):** o edge bruto por trade tem de superar o custo
  round-trip **com folga ≥ 2×**, senão a frequência mata (lição da Fase 1 FX).

## 6. Parâmetros (defaults propostos: a fixar antes de codar)
| Símbolo | Papel | Default proposto | Alternativas |
| :-- | :-- | :-- | :-- |
| `OR_MIN` | janela do opening range | **30 min** | 15 / 60 |
| `ATR_MULT` | stop em ATR(M15) | **1,0** | 0,75 / 1,5 |
| `R_MULT` | alvo em múltiplos de risco | **2,0** | 1,5 / 3,0 / trailing |
| `k` (range mín.) | OR_width ≥ k·ATR | **0,5** | 0,3 / 0,8 |
| TF do sinal | barra de gatilho/gestão | **M15** | M5 / M30 |

Estes são **hiperparâmetros de pesquisa** → otimizados SÓ dentro do CPCV (nunca no full
sample), e o nº de combinações testadas alimenta o **DSR** (deflaciona p/ data-mining).

## 7. Gate pré-registrado: Fase 1i (critério ANTES do teste)
Baseline ORB, 5 instrumentos, todo o histórico baixado (2012→hoje), custo completo:
- **Sharpe líquido anual > 0** com **PSR > 0,95** (não é sorte).
- **CPCV:** fração de caminhos com Sharpe > 0 **≥ 60%** (robusto ao path).
- **DSR > 0** após deflação pelo nº de configs testadas.
- **MC block-bootstrap:** MaxDD p99 dentro do circuit breaker (RF-12) para $1.000.
- **Frequência sã:** ≤ ~2 trades/instrumento/dia em média (senão custo domina).
- **Edge bruto (pré-custo) POSITIVO por instrumento**: a lição decisiva da Fase 1:
  sem bruto positivo, nada de gestão/filtro salva. Este é o primeiro corte.

**Falha em qualquer critério → FAIL**, diagnóstico honesto, decisão do usuário. Sem ajuste ad hoc.

## 8. Decisões fixadas (2026-07-25)
1. **Saída = alvo fixo 2R** (stop fixo, sem trailing no baseline). Trailing = variante futura.
2. **TF do sinal/gestão = M15.**
3. **Construção = piloto US100 primeiro** (sessão mais limpa) → valida a mecânica
   ponta-a-ponta + reconciliação MT5, depois estende aos outros 4.

Defaults §6 (`OR_MIN=30`, `ATR_MULT=1,0`, `R_MULT=2,0`, `k=0,5`) valem como **ponto de
partida**; a otimização real ocorre só dentro do CPCV (alimentando o DSR), nunca no full sample.
