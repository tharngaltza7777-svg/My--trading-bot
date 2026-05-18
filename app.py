import asyncio
import logging
from fastapi import FastAPI
import requests
import pandas as pd
import ta
import yfinance as yf

# --- [ Telegram API configurations ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"

# စောင့်ကြည့်မည့် စျေးကွက်များနှင့် ၎င်းတို့၏ Yahoo Finance သင်္ကေတများ
ASSETS = {
    "GOLD (ရွှေ)": "GC=F",
    "CRUDE OIL (ရေနံ)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ETH/USD (Crypto)": "ETH-USD"  # Crypto ပါ တွဲသုံးလိုလျှင်
}

# တည်ငြိမ်မှုအရှိဆုံး Timeframe (5m ဒေတာ မပြည့်စုံပါက 15m သို့ ပြောင်းသုံးနိုင်သည်)
INTERVAL = "5m"       
RSI_PERIOD = 14       

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# အချက်ပြမှု ထပ်မတက်စေရန် အခြေအနေ မှတ်သားခြင်း
last_signals = {asset: None for asset in ASSETS.keys()}

async def check_markets_and_alert():
    global last_signals
    while True:
        for asset_name, ticker in ASSETS.items():
            try:
                # ၁။ Yahoo Finance မှ ဒေတာကောက်ယူခြင်း (Progress Bar ပိတ်ထားသည်)
                data = yf.download(tickers=ticker, period="1d", interval=INTERVAL, progress=False)
                
                # ဒေတာ လုံးဝမရှိခြင်း သို့မဟုတ် RSI တွက်ရန် မလုံလောက်ခြင်းကို စစ်ဆေးရန်
                if data.empty or len(data) < (RSI_PERIOD + 2):
                    logging.warning(f"[{asset_name}] စျေးကွက်ပိတ်ထားခြင်း (သို့) ဒေတာမလုံလောက်ပါ။ Skipping...")
                    continue
                
                # ၂။ Multi-index DataFrame Column ပြဿနာကို ဖြေရှင်းခြင်း
                df = pd.DataFrame(data)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                
                df['Close'] = df['Close'].astype(float)
                
                # ၃။ RSI တွက်ချက်ခြင်း
                df['RSI'] = ta.momentum.rsi(df['Close'], window=RSI_PERIOD)
                
                # လတ်တလော ထွက်လာသော ဒေတာများကို သန့်စင်ခြင်း
                df_clean = df.dropna(subset=['RSI', 'Close'])
                if df_clean.empty:
                    logging.warning(f"[{asset_name}] RSI တန်ဖိုး မထွက်သေးပါ။ Skipping...")
                    continue
                
                # ဒေတာဇယား၏ နောက်ဆုံးစာကြောင်းကို ဘေးကင်းစွာ ဆွဲယူခြင်း (Index out of bounds မဖြစ်စေရန်)
                current_rsi = float(df_clean['RSI'].iloc[-1])
                current_price = float(df_clean['Close'].iloc[-1])
                
                logging.info(f"[{asset_name}] RSI: {current_rsi:.2f} | Price: {current_price:.4f}")
                
                # ၄။ Trading Signal Logic (RSI < 42 Buy | RSI > 58 Sell)
                if current_rsi < 42 and last_signals[asset_name] != "BUY":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🟢 Action: **BUY**\n💰 Price: {current_price:.4f}\n📉 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated Multi-Asset Engine"
                    send_telegram_message(message)
                    last_signals[asset_name] = "BUY"
                    
                elif current_rsi > 58 and last_signals[asset_name] != "SELL":
                    message = f"🚀 **REAL-TIME TRADING ALERT**\n\n📊 Asset: **{asset_name}**\n🔴 Action: **SELL**\n💰 Price: {current_price:.4f}\n📈 RSI (14): {current_rsi:.2f}\n\n🔒 Status: Automated Multi-Asset Engine"
                    send_telegram_message(message)
                    last_signals[asset_name] = "SELL"
                    
                # RSI ပုံမှန်ဇုန်ထဲ ပြန်ရောက်သွားပါက Signal အခြေအနေကို Reset ချပေးခြင်း
                elif 45 < current_rsi < 55:
                    last_signals[asset_name] = None
                    
            except Exception as e:
                logging.error(f"Error processing {asset_name}: {e}")
                
            # API Rate Limit အညှပ်မခံရစေရန် ပစ္စည်းတစ်ခုချင်းစီကြား ၃ စက္ကန့် စောင့်ခြင်း
            await asyncio.sleep(3)
            
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
    return {"status": "Forex, Commodities & Crypto Polling Engine is Active and Safe!"}
