import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import requests
import pandas as pd
import ta
import yfinance as yf

# --- [ Telegram Configurations ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"

# စောင့်ကြည့်မည့် Asset များ
ASSETS = {
    "GOLD (ရွှေ)": "GC=F",
    "CRUDE OIL (ရေနံ)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ETH/USD": "ETH-USD"
}

INTERVAL = "5m"       
RSI_PERIOD = 14       

# Logging သေချာတက်လာစေရန် Setup လုပ်ခြင်း
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

last_signals = {asset: None for asset in ASSETS.keys()}

def send_telegram_message(text):
    url = f"https://api.telegram.com/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        logging.info(f"Telegram API Sent Status: {response.status_code}")
        return response.status_code
    except Exception as e:
        logging.error(f"Telegram Error: {e}")
        return None

async def check_markets_and_alert():
    global last_signals
    logging.info("🚀 [ENGINE START] Multi-Asset Polling Engine စတင်ပါပြီ...")
    
    # စက်စမောင်းတာနဲ့ Telegram ထဲကို စမ်းသပ်စာသား အတင်းပို့ခိုင်းခြင်း
    test_msg = "📢 **BOT STATUS ACTIVE**\n\nTrading Engine ကို FastAPI Lifespan စနစ်ဖြင့် အောင်မြင်စွာ တည်ဆောက်ပြီးပါပြီ။\n\n🎯 *ယခုအချိန်မှစ၍ Signal များကို စတင်ဖတ်နေပါပြီ။*"
    send_telegram_message(test_msg)
    
    while True:
        for asset_name, ticker in ASSETS.items():
            try:
                logging.info(f"🔍 Fetching data for {asset_name}...")
                data = yf.download(tickers=ticker, period="1d", interval=INTERVAL, progress=False)
                
                if data.empty or len(data) < (RSI_PERIOD + 2):
                    logging.info(f"⚠️ [{asset_name}] ဒေတာမလုံလောက်ပါ သို့မဟုတ် စျေးကွက်ပိတ်ထားသည်။")
                    continue
                
                df = pd.DataFrame(data)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                
                df['Close'] = df['Close'].astype(float)
                df['RSI'] = ta.momentum.rsi(df['Close'], window=RSI_PERIOD)
                
                df_clean = df.dropna(subset=['RSI', 'Close'])
                if df_clean.empty:
                    continue
                
                current_rsi = float(df_clean['RSI'].iloc[-1])
                current_price = float(df_clean['Close'].iloc[-1])
                
                # Render Log ပေါ်တွင် အမြဲတမ်းမြင်ရအောင် print ထုတ်ခြင်း
                print(f"📊 [{asset_name}] Price: {current_price:.4f} | RSI: {current_rsi:.2f}", flush=True)
                
                # Signal Logic
                if current_rsi < 42 and last_signals[asset_name] != "BUY":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🟢 Action: **BUY**\n💰 Price: {current_price:.4f}\n📉 RSI (14): {current_rsi:.2f}"
                    send_telegram_message(message)
                    last_signals[asset_name] = "BUY"
                    
                elif current_rsi > 58 and last_signals[asset_name] != "SELL":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🔴 Action: **SELL**\n💰 Price: {current_price:.4f}\n📈 RSI (14): {current_rsi:.2f}"
                    send_telegram_message(message)
                    last_signals[asset_name] = "SELL"
                    
                elif 45 < current_rsi < 55:
                    last_signals[asset_name] = None
                    
            except Exception as e:
                logging.error(f"Error processing {asset_name}: {e}")
                
            await asyncio.sleep(2)
            
        await asyncio.sleep(60)

# Uvicorn မောင်းတာနဲ့ နောက်ကွယ်က Loop ကို Background မှာ ဇွတ်မောင်းခိုင်းမည့် ခေတ်မီစနစ်
@asynccontextmanager
async def lifespan(app: FastAPI):
    # စက်စမောင်းချိန်တွင် လုပ်ရမည့်အလုပ်
    task = asyncio.create_task(check_markets_and_alert())
    yield
    # စက်ပိတ်ချိန်တွင် လုပ်ရမည့်အလုပ်
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "Online", "engine": "Lifespan Active"}
