import asyncio
import logging
from fastapi import FastAPI
import requests
import pandas as pd
import ta

# --- [ ဆက်တင်များ အားလုံး ဖြည့်စွက်ပြီးသားဖြစ်သည် ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"
SYMBOL = "ETHUSDT"                              # စောင့်ကြည့်မယ့် Asset
INTERVAL = "5m"                                 # ၅ မိနစ် Timeframe
RSI_PERIOD = 14                                 # RSI Standard Period
# --------------------------------------------------

app = FastAPI()
logging.basicConfig(level=logging.INFO)

last_signal = None  

async def check_rsi_and_alert():
    global last_signal
    while True:
        try:
            # ၁။ Binance API မှ Live Candlestick Data လှမ်းဆွဲခြင်း
            url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=100"
            response = requests.get(url).json()
            
            # ၂။ Data Frame ပြင်ဆင်ခြင်း
            df = pd.DataFrame(response, columns=[
                'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 
                'Close_time', 'Quote_asset_volume', 'Number_of_trades', 
                'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
            ])
            df['Close'] = df['Close'].astype(float)
            
            # ၃။ pandas_ta သုံးပြီး RSI ကို တွက်ချက်ခြင်း
            df['RSI'] = ta.rsi(df['Close'], length=RSI_PERIOD)
            
            current_rsi = float(df['RSI'].iloc[-1])
            current_price = float(df['Close'].iloc[-1])
            
            logging.info(f"Current RSI for {SYMBOL}: {current_rsi:.2f} | Price: {current_price}")
            
            # ၄။ Logic စစ်ဆေးပြီး Telegram သို့ Signal တိုက်ရိုက်ပို့ခြင်း
            if current_rsi < 42 and last_signal != "BUY":
                message = f"🚀 **REAL-TIME ETH ALERT**\n\n🟢 Action: **BUY**\n💰 Price: {current_price}\n📊 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated via Polling Engine"
                send_telegram_message(message)
                last_signal = "BUY"
                
            elif current_rsi > 58 and last_signal != "SELL":
                message = f"🚀 **REAL-TIME ETH ALERT**\n\n🔴 Action: **SELL**\n💰 Price: {current_price}\n📊 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated via Polling Engine"
                send_telegram_message(message)
                last_signal = "SELL"
                
            elif 45 < current_rsi < 55:
                last_signal = None
                
        except Exception as e:
            logging.error(f"Polling Engine Error: {e}")
            
        await asyncio.sleep(60)

def send_telegram_message(text):
    url = f"https://api.telegram.com/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Sending Error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_rsi_and_alert())

@app.get("/")
def home():
    return {"status": "Polling Engine is Active and Scanning Markets!"}
