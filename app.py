import asyncio
import logging
from fastapi import FastAPI
import requests
import pandas as pd
import ta
import yfinance as yf

# --- [ ဆက်တင်များ ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"

# စောင့်ကြည့်မည့် Asset များနှင့် ၎င်းတို့၏ Yahoo Finance သင်္ကေတများ
ASSETS = {
    "GOLD (ရွှေ)": "GC=F",
    "CRUDE OIL (ရေနံ)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X"
}

INTERVAL = "5m"       # ၅ မိနစ် Timeframe
RSI_PERIOD = 14       # RSI Standard Period

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Asset တစ်ခုချင်းစီအတွက် ပြီးခဲ့သော Signal အခြေအနေကို မှတ်ထားရန်
last_signals = {asset: None for asset in ASSETS.keys()}

async def check_markets_and_alert():
    global last_signals
    while True:
        for asset_name, ticker in ASSETS.items():
            try:
                # ၁။ Yahoo Finance မှ Real-time ဒေတာ ဆွဲယူခြင်း
                data = yf.download(tickers=ticker, period="1d", interval=INTERVAL, progress=False)
                
                if data.empty or len(data) < RSI_PERIOD + 5:
                    logging.warning(f"Insufficient data for {asset_name}. Skipping...")
                    continue
                
                # ဒေတာဇယားကို ပုံစံချခြင်း
                df = pd.DataFrame(data)
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
                df['Close'] = df['Close'].astype(float)
                
                # ၂။ RSI တွက်ချက်ခြင်း
                df['RSI'] = ta.momentum.rsi(df['Close'], window=RSI_PERIOD)
                
                if df['RSI'].isnull().all():
                    continue
                    
                current_rsi = float(df['RSI'].dropna().iloc[-1])
                current_price = float(df['Close'].iloc[-1])
                
                logging.info(f"[{asset_name}] RSI: {current_rsi:.2f} | Price: {current_price:.4f}")
                
                # ၃။ Trading Signal Logic (RSI < 42 Buy | RSI > 58 Sell)
                if current_rsi < 42 and last_signals[asset_name] != "BUY":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🟢 Action: **BUY**\n💰 Price: {current_price:.4f}\n📉 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated Multi-Asset Engine"
                    send_telegram_message(message)
                    last_signals[asset_name] = "BUY"
                    
                elif current_rsi > 58 and last_signals[asset_name] != "SELL":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🔴 Action: **SELL**\n💰 Price: {current_price:.4f}\n📈 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated Multi-Asset Engine"
                    send_telegram_message(message)
                    last_signals[asset_name] = "SELL"
                    
                elif 45 < current_rsi < 55:
                    last_signals[asset_name] = None
                    
            except Exception as e:
                logging.error(f"Error processing {asset_name}: {e}")
                
            # API Rate Limit မမိအောင် Asset တစ်ခုနှင့်တစ်ခုကြား ၂ စက္ကန့် ခေတ္တနားခြင်း
            await asyncio.sleep(2)
            
        # စျေးကွက်တစ်ခုလုံးကို ၁ မိနစ်လျှင် တစ်ကြိမ်စီ ပတ်ပတ်လည် Scan ဖတ်ခြင်း
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
    asyncio.create_task(check_markets_and_alert())

@app.get("/")
def home():
    return {"status": "Forex & Commodities Polling Engine is Active!"}
