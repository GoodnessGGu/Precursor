//+------------------------------------------------------------------+
//|                                              Gushtec_Bridge.mq5 |
//|                                  Copyright 2026, Gushtec Pro    |
//|                                             https://gushtec.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Gushtec Pro"
#property link      "https://gushtec.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input string SignalFolder = "signals\\"; // Folder relative to MQL5/Files or Common/Files
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("Gushtec MT5 Bridge Started. Monitoring for signals...");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   string filename;
   // Searching in the local MQL5/Files folder (no FILE_COMMON flag)
   long search_handle = FileFindFirst(SignalFolder + "*.json", filename);

   if(search_handle != INVALID_HANDLE)
   {
      do
      {
         Print("Local signal detected: ", filename);
         ProcessSignal(filename);
      }
      while(FileFindNext(search_handle, filename));
      
      FileFindClose(search_handle);
   }
}

//+------------------------------------------------------------------+
//| Process the JSON Signal File                                     |
//+------------------------------------------------------------------+
void ProcessSignal(string filename)
{
   int file_handle = FileOpen(SignalFolder + filename, FILE_READ|FILE_TXT);
   if(file_handle != INVALID_HANDLE)
   {
      string json_str = FileReadString(file_handle);
      FileClose(file_handle);
      
      // Basic manual parsing of the JSON (MQL5 doesn't have a built-in JSON parser)
      string symbol = GetJsonValue(json_str, "symbol");
      string side = GetJsonValue(json_str, "side");
      double qty = StringToDouble(GetJsonValue(json_str, "qty"));
      double sl = StringToDouble(GetJsonValue(json_str, "sl"));
      double tp = StringToDouble(GetJsonValue(json_str, "tp"));
      
      if(symbol != "" && qty > 0)
      {
         bool result = false;
         if(side == "LONG")
            result = trade.Buy(qty, symbol, 0, sl, tp, "Gushtec AI Signal");
         else if(side == "SHORT")
            result = trade.Sell(qty, symbol, 0, sl, tp, "Gushtec AI Signal");
            
         if(result)
         {
            Print("✅ TRADE EXECUTED: ", side, " ", symbol, " ", qty, " lots");
            FileDelete(SignalFolder + filename); // Remove file after success
         }
         else
         {
            Print("❌ TRADE FAILED: ", trade.ResultRetcodeDescription());
            FileDelete(SignalFolder + filename); // Remove anyway to avoid loops
         }
      }
   }
}

// Simple helper to extract value from JSON string
string GetJsonValue(string json, string key)
{
   string search_key = "\"" + key + "\":";
   int pos = StringFind(json, search_key);
   if(pos == -1) return "";
   
   int start = pos + StringLen(search_key);
   // Find start of value (skip quotes or whitespace)
   while(start < StringLen(json) && (StringSubstr(json, start, 1) == " " || StringSubstr(json, start, 1) == "\"" || StringSubstr(json, start, 1) == ":"))
      start++;
      
   int end = start;
   // Find end of value (until comma or closing brace)
   while(end < StringLen(json) && StringSubstr(json, end, 1) != "," && StringSubstr(json, end, 1) != "}" && StringSubstr(json, end, 1) != "\"")
      end++;
      
   return StringSubstr(json, start, end - start);
}
