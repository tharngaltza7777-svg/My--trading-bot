import yfinance as yf
import requests
import time
import os
from flask import Flask
from threading import Thread

# Web Server for Render
app = Flask('')
@app.route('/')
def home(): return "Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# RSI တွက်ချက်ရန် Function (Library မပါဘဲ ကိုယ်တိုင်တွက်နည်း)
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Signal စစ်ဆေးပြီး Telegram သို့ ပို့ရန် Function
def check_signals():
    symbol = "XAUUSD=X" # Gold (ရွှေစျေး)
    try:
        df = yf.download(symbol, interval="5m", period="1d", progress=False)
        if len(df) < 20: return
        
        df['RSI'] = calculate_rsi(df)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        last_price = df['Close'].iloc[-1]
        last_rsi = df['RSI'].iloc[-1]
        last_ema = df['EMA_20'].iloc[-1]
        
        msg = ""
        if last_rsi < 30 and last_price > last_ema:
            msg = f"🚀 BUY SIGNAL: Gold at {last_price:.2f} (RSI: {last_rsi:.2f})"
        elif last_rsi > 70 and last_price < last_ema:
            msg = f"📉 SELL SIGNAL: Gold at {last_price:.2f} (RSI: {last_rsi:.2f})"
        
        if msg:
            # Token နဲ့ Chat ID ကို Environment Variables ကနေ ခေါ်သုံးပါမယ်
            token = os.environ.get("TELEGRAM_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
                requests.get(url)
                print(f"Signal Sent: {msg}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    Thread(target=run_web).start()
    print("🚀 Bot is starting...")
    while True:
        check_signals()
        time.sleep(900)
            
        
