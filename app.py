import asyncio
import logging
from fastapi import FastAPI
import requests
import pandas as pd
import ta
import yfinance as yf

# --- [ Telegram Configurations ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"

# စောင့်ကြည့်မည့် Asset များနှင့် ၎င်းတို့၏ Yahoo Finance သင်္ကေတများ
ASSETS = {
    "GOLD (ရွှေ)": "GC=F",
    "CRUDE OIL (ရေနံ)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ETH/USD": "ETH-USD"
}

INTERVAL = "5m"       # ၅ မိနစ် Timeframe
RSI_PERIOD = 14       # RSI Period

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
                
                if data.empty or len(data) < (RSI_PERIOD + 2):
                    logging.info(f"[{asset_name}] စျေးကွက်ပိတ်ထားခြင်း (သို့) ဒေတာမလုံလောက်ပါ။ Skipping...")
                    continue
                
                # Multi-index DataFrame Column ပြဿနာကို ဖြေရှင်းခြင်း
                df = pd.DataFrame(data)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                
                df['Close'] = df['Close'].astype(float)
                
                # ၂။ RSI တွက်ချက်ခြင်း
                df['RSI'] = ta.momentum.rsi(df['Close'], window=RSI_PERIOD)
                
                # ဒေတာ သန့်စင်ခြင်း
                df_clean = df.dropna(subset=['RSI', 'Close'])
                if df_clean.empty:
                    continue
                
                current_rsi = float(df_clean['RSI'].iloc[-1])
                current_price = float(df_clean['Close'].iloc[-1])
                
                logging.info(f"[{asset_name}] RSI: {current_rsi:.2f} | Price: {current_price:.4f}")
                
                # ၃။ Trading Signal Logic (RSI < 42 Buy | RSI > 58 Sell)
                if current_rsi < 42 and last_signals[asset_name] != "BUY":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🟢 Action: **BUY**\n💰 Price: {current_price:.4f}\n📉 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Multi-Asset Engine Active"
                    send_telegram_message(message)
                    last_signals[asset_name] = "BUY"
                    
                elif current_rsi > 58 and last_signals[asset_name] != "SELL":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🔴 Action: **SELL**\n💰 Price: {current_price:.4f}\n📈 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Multi-Asset Engine Active"
                    send_telegram_message(message)
                    last_signals[asset_name] = "SELL"
                    
                # RSI ပုံမှန်ဇုန်ထဲ ပြန်ရောက်သွားပါက Signal အခြေအနေကို Reset ချပေးခြင်း
                elif 45 < current_rsi < 55:
                    last_signals[asset_name] = None
                    
            except Exception as e:
                logging.error(f"Error processing {asset_name}: {e}")
                
            # API Rate Limit မမိအောင် Asset တစ်ခုချင်းစီကြား ၂ စက္ကန့် ခေတ္တနားခြင်း
            await asyncio.sleep(2)
            
        # စျေးကွက်တစ်ခုလုံးကို ၁ မိနစ်လျှင် တစ်ကြိမ်စီ ပတ်ပတ်လည် Scan ဖတ်ခြင်း
        await asyncio.sleep(60)

def send_telegram_message(text):
    url = f"https://api.telegram.com/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        logging.info(f"Telegram API Response: {response.status_code}")
    except Exception as e:
        logging.error(f"Telegram Sending Error: {e}")

@app.on_event("startup")
async def startup_event():
    # --- [ စမ်းသပ်ချက် အချက်ပြစာတို ] ---
    # စနစ်စတင်မောင်းနှင်တာနဲ့ Telegram ထဲကို စမ်းသပ်စာသား ချက်ချင်း ပို့ခိုင်းခြင်း
    test_msg = "📢 **BOT STATUS ACTIVE**\n\nMulti-Asset Trading Engine ကို အောင်မြင်စွာ တည်ဆောက်ပြီးပါပြီ။\n\n📊 **စောင့်ကြည့်နေသည့် စျေးကွက်များ-**\n• ရွှေ (Gold)\n• ရေနံ (Crude Oil)\n• Forex (EURUSD, GBPUSD)\n• Crypto (ETHUSD)\n\n🎯 *ယခုအချိန်မှစ၍ Signal များကို စတင်ဖတ်နေပါပြီ။*"
    send_telegram_message(test_msg)
    
    # ပုံမှန် စောင့်ကြည့်ရေးလုပ်ငန်းစဉ်ကို နောက်ကွယ်ကနေ စတင်မောင်းနှင်ခြင်း
    asyncio.create_task(check_markets_and_alert())

@app.get("/")
def home():
    return {"status": "Forex, Commodities & Crypto Engine is Fully Functional!"}
