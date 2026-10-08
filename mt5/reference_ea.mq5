//+------------------------------------------------------------------+
//|  reference_ea.mq5 — Donchian breakout de REFERÊNCIA (Fase 0.4)     |
//|  Replica research/backtester.py :: donchian_positions + simulate  |
//|  para reconciliar Python <-> Strategy Tester (ataca o R-01).      |
//|                                                                    |
//|  Não é o sistema final — é instrumento determinístico de teste.   |
//|  Decisão no FECHAMENTO da barra (shift 1); execução na ABERTURA    |
//|  da barra seguinte (shift 0). Preços registrados = abertura da     |
//|  barra (mid) para casar com o Python; custos são comparados à parte.|
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input int    EntryN  = 55;                        // canal de entrada (barras)
input int    ExitN   = 20;                        // canal de saída (barras)
input double Lots    = 0.10;                       // volume fixo
input string CsvName = "reference_ea_trades.csv";  // saída em Common\Files

CTrade   trade;
datetime g_lastBar   = 0;
datetime g_entryTime = 0;
double   g_entryPrice = 0.0;
int      g_dir = 0;     // posição atual: -1 vendido, 0 flat, +1 comprado
int      g_idx = 0;
int      g_fh  = INVALID_HANDLE;

int OnInit()
{
   g_fh = FileOpen(CsvName, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(g_fh != INVALID_HANDLE)
      FileWrite(g_fh, "idx","dir","entry_time","entry_price","exit_time","exit_price","volume");
   PrintFormat("reference_ea iniciado | EntryN=%d ExitN=%d Lots=%.2f | CSV=%s", EntryN, ExitN, Lots, CsvName);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   // fecha posição aberta no fim, como o simulate() do Python (fecha na última barra)
   if(g_dir != 0)
      WriteTrade(iTime(_Symbol,PERIOD_H4,0), iClose(_Symbol,PERIOD_H4,0));
   if(g_fh != INVALID_HANDLE)
      FileClose(g_fh);
}

// Permite rodar também em modo Otimização ("Custom max") sem erro; para a
// reconciliação use execução ÚNICA (Otimização = Desligada).
double OnTester()
{
   return TesterStatistics(STAT_PROFIT);   // lucro líquido como critério custom
}

int CurrentDir()
{
   if(!PositionSelect(_Symbol)) return 0;
   return (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
}

// extremos das `count` barras a partir do shift `start` (exclui a barra de decisão)
double Highest(int start, int count)
{
   double a[]; if(CopyHigh(_Symbol,PERIOD_H4,start,count,a) < count) return 0.0;
   return a[ArrayMaximum(a)];
}
double Lowest(int start, int count)
{
   double a[]; if(CopyLow(_Symbol,PERIOD_H4,start,count,a) < count) return 0.0;
   return a[ArrayMinimum(a)];
}

void WriteTrade(datetime xt, double xp)
{
   if(g_fh != INVALID_HANDLE)
      FileWrite(g_fh, g_idx, g_dir,
                TimeToString(g_entryTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                DoubleToString(g_entryPrice, _Digits),
                TimeToString(xt, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                DoubleToString(xp, _Digits),
                DoubleToString(Lots, 2));
   g_idx++;
}

void OnTick()
{
   datetime t = iTime(_Symbol, PERIOD_H4, 0);
   if(t == g_lastBar) return;          // age só uma vez por barra H4 (na abertura)
   g_lastBar = t;
   if(Bars(_Symbol, PERIOD_H4) < EntryN + 3) return;

   double close1 = iClose(_Symbol, PERIOD_H4, 1);   // barra recém-fechada (decisão)
   double up55 = Highest(2, EntryN), lo55 = Lowest(2, EntryN);
   double up20 = Highest(2, ExitN),  lo20 = Lowest(2, ExitN);
   if(up55 == 0.0 || lo55 == 0.0) return;

   int cur = CurrentDir();
   int target = cur;
   if     (cur <= 0 && close1 > up55) target = 1;   // rompe canal superior -> comprado
   else if(cur >= 0 && close1 < lo55) target = -1;  // rompe canal inferior -> vendido
   else if(cur > 0  && close1 < lo20) target = 0;   // saída do comprado
   else if(cur < 0  && close1 > up20) target = 0;   // saída do vendido

   if(target == cur) return;

   double barOpen = iOpen(_Symbol, PERIOD_H4, 0);   // preço de execução = abertura da barra
   if(cur != 0)                                     // fecha posição atual
   {
      trade.PositionClose(_Symbol);
      WriteTrade(t, barOpen);
   }
   if(target != 0)                                  // abre nova
   {
      if(target > 0) trade.Buy(Lots, _Symbol); else trade.Sell(Lots, _Symbol);
      g_entryTime = t; g_entryPrice = barOpen; g_dir = target;
   }
   else g_dir = 0;
}
//+------------------------------------------------------------------+
