import os
import requests
import time
import yfinance as yf
import pandas_ta as ta

# --- Configuration ---
TOKEN = "8140108107:AAH1AEOF1pZzYRNkDDm1v4ylvBHC-IcQlhM"
CHAT_ID = "8344079627"

def send_signal(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except:
        pass

def monitor_market():
    # ရွှေ၊ ငွေ နဲ့ Bitcoin ကို စောင့်ကြည့်မယ်
    assets = {"GOLD 🟡": "GC=F", "SILVER ⚪": "SI=F", "BITCOIN 🧡": "BTC-USD"}
    
    for name, ticker in assets.items():
        try:
            df = yf.download(ticker, period="2d", interval="5m", progress=False)
            
            # Institutional Logic (EMA 200 & RSI)
            df['EMA_200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            price = df['Close'].iloc[-1]
            ema_200 = df['EMA_200'].iloc[-1]
            rsi = df['RSI'].iloc[-1]

            # Signal Logic
            if price > ema_200 and 45 < rsi < 65:
                msg = f"🏆 *GLOBAL PRO BUY: {name}*\n🎯 Price: `${price:.2f}`\n📈 Trend: Strong Bullish"
                send_signal(msg)
            elif price < ema_200 and 35 < rsi < 55:
                msg = f"🏆 *GLOBAL PRO SELL: {name}*\n🎯 Price: `${price:.2f}`\n📉 Trend: Strong Bearish"
                send_signal(msg)
        except:
            continue

if __name__ == "__main__":
    print("🚀 AI Agent is starting on Cloud...")
    while True:
        monitor_market()
        time.sleep(300) # ၅ မိနစ်တစ်ခါ စစ်ဆေးမယ်
