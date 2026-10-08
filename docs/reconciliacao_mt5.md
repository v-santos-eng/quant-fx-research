# Reconciliação Python ↔ MT5 (gate do R-01): passo a passo

Objetivo: rodar a estratégia de referência (Donchian 55/20 H4) no **Strategy Tester**
do MT5 e comparar com o backtester Python. Gate pré-registrado: **nº de trades ±1** e
**P&L dentro de ±2%** na mesma janela/símbolo.

O EA já está em: `...\MQL5\Experts\reference_ea.mq5` (cópia em `mt5/reference_ea.mq5`).

## 1. Compilar o EA
1. No MT5, tecle **F4** (abre o MetaEditor).
2. No navegador à esquerda: **Experts → reference_ea.mq5** (duplo-clique).
3. Tecle **F7** (Compilar). Confirme **0 erros** → gera `reference_ea.ex5`.

## 2. Abrir e configurar o Strategy Tester
1. No MT5, tecle **Ctrl+R** (abre a aba *Testador de Estratégia*).
2. Configure:
   - **Expert Advisor:** `reference_ea`
   - **Símbolo:** `EURUSD`
   - **Período (timeframe):** **H4**
   - **Modelagem:** **"Every tick based on real ticks"** (cada tick por ticks reais)
   - **Intervalo de datas:** use **2023.01.01 → 2025.12.31** (ver nota A)
   - **Depósito:** 10000 USD · **Alavancagem:** 1:100
   - **Otimização:** desligada (execução única)
3. Aba **Inputs/Parâmetros:** `EntryN=55`, `ExitN=20`, `Lots=0.10`.

## 3. Rodar
- Clique **Start**. Aguarde terminar (barra de progresso).
- Na aba **Resultados/Gráfico** você vê os trades; **guarde o "Total net profit" e o "Total trades"**.

## 4. Localizar a saída do EA
O EA grava um CSV com todos os trades em:
```
%APPDATA%\MetaQuotes\Terminal\Common\Files\reference_ea_trades.csv
```
Colunas: `idx, dir, entry_time, entry_price, exit_time, exit_price, volume`.

## 5. Me envie
- O arquivo **`reference_ea_trades.csv`**, e
- Os números do relatório do tester (**total trades** e **total net profit**).

Com isso eu rodo o `research/reconcile.py`: alinho as barras Python ao horário do
servidor (ver nota B), comparo trade a trade e P&L, e **verifico o gate (±1 / ±2%)**.

---

## Notas que evitam dor de cabeça
**A. Profundidade de ticks reais.** O "ticks reais" do broker costuma ter histórico
limitado (poucos anos). Por isso a janela recomendada é recente (2023–2025). Se quiser
cobrir 2010+, o tester cai para modelagem "1 minuto OHLC" (menos exata), aí a
reconciliação vira aproximada. Para o gate do R-01, uma janela recente com ticks reais
é o teste limpo.

**B. Alinhamento de barras (a razão de existir esta etapa).** O MT5 monta barras H4 no
**horário do servidor** (Dukascopy ≠ UTC, com horário de verão), enquanto as barras
Python são UTC. Então os trades **não** casam barra-a-barra sem correção. O `reconcile.py`
detecta o offset do servidor a partir dos horários do CSV e reconstrói as barras Python
com `build_bars(..., origin_offset=...)` antes de comparar. É exatamente o risco R-01
que este gate mede.

**C. Preços.** O EA registra o preço na **abertura da barra** (igual ao Python), para
isolar a mecânica do sinal; diferenças de spread/fill entram na camada de custos, que é
comparada à parte.
