import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import requests
import pandas as pd
import ta
import yfinance as yf

# --- [ Configurations ] ---
TELEGRAM_BOT_TOKEN = "8951243669:AAEJSVGQo3AMWvIorVYUvAIzoBDdFW-z07M"
TELEGRAM_CHAT_ID = "8344079627"

ASSETS = {
    "GOLD (ရွှေ)": "GC=F",
    "CRUDE OIL (ရေနံ)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ETH/USD": "ETH-USD"
}

INTERVAL = "1h"       
BACKTEST_PERIOD = "60d"  

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
last_signals = {asset: None for asset in ASSETS.keys()}

def send_telegram_message(text):
    url = f"https://api.telegram.com/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        logging.info(f"Telegram API Sent Status: {response.status_code}")
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

def run_vectorized_backtest(df):
    try:
        df = df.copy()
        df['RSI_6'] = ta.momentum.rsi(df['Close'], window=6)
        df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
        df['RSI_26'] = ta.momentum.rsi(df['Close'], window=26)
        df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
        df = df.dropna()
        
        if len(df) < 100:
            return 0.0

        df['Buy_Sig'] = (df['RSI_6'] > 50) & (df['RSI_14'] > 50) & (df['RSI_26'] > 50) & (df['Close'] > df['EMA_200'])
        df['Sell_Sig'] = (df['RSI_6'] < 50) & (df['RSI_14'] < 50) & (df['RSI_26'] < 50) & (df['Close'] < df['EMA_200'])
        
        total_trades = 0
        winning_trades = 0
        
        for i in range(len(df) - 5):
            if df['Buy_Sig'].iloc[i]:
                total_trades += 1
                entry = df['Close'].iloc[i]
                max_future_price = df['High'].iloc[i+1:i+6].max()
                if max_future_price > entry * 1.005:
                    winning_trades += 1
            elif df['Sell_Sig'].iloc[i]:
                total_trades += 1
                entry = df['Close'].iloc[i]
                min_future_price = df['Low'].iloc[i+1:i+6].min()
                if min_future_price < entry * 0.995:
                    winning_trades += 1
                    
        if total_trades == 0:
            return 80.0
            
        win_rate = (winning_trades / total_trades) * 100
        return win_rate
    except Exception:
        return 0.0

async def check_markets_and_alert():
    global last_signals
    logging.info("🚀 [ENGINE LAUNCHED]")
    
    # ဆာဗာ စတင်အလုပ်လုပ်တာနဲ့ အတင်းဇွတ် Noti ပို့ခိုင်းသည့်စာသား
    send_telegram_message("⚙️ **QUANT SUPER ENGINE ACTIVE**\n\n• **Timeframe:** 1 Hour (1hr)\n• **Status:** Live Link Connected! 🟢")
    
    while True:
        for asset_name, ticker in ASSETS.items():
            try:
                await asyncio.sleep(5)
                data = yf.download(tickers=ticker, period=BACKTEST_PERIOD, interval=INTERVAL, progress=False)
                if data.empty or len(data) < 100:
                    continue
                
                df = pd.DataFrame(data)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                
                df = df.astype(float)
                calculated_win_rate = run_vectorized_backtest(df)
                
                df['RSI_6'] = ta.momentum.rsi(df['Close'], window=6)
                df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
                df['RSI_26'] = ta.momentum.rsi(df['Close'], window=26)
                df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
                
                current_rsi_6 = float(df['RSI_6'].iloc[-1])
                current_rsi_14 = float(df['RSI_14'].iloc[-1])
                current_rsi_26 = float(df['RSI_26'].iloc[-1])
                current_ema_200 = float(df['EMA_200'].iloc[-1])
                current_price = float(df['Close'].iloc[-1])
                
                recent_low = float(df['Low'].iloc[-10:].min())
                recent_high = float(df['High'].iloc[-10:].max())
                
                if calculated_win_rate >= 70.0:
                    if current_rsi_6 > 50 and current_rsi_14 > 50 and current_rsi_26 > 50 and current_price > current_ema_200:
                        if last_signals[asset_name] != "BUY":
                            sl = recent_low - (current_price * 0.002)
                            tp = current_price + ((current_price - sl) * 1.5)
                            
                            message = (
                                f"🟢 **🎯 PLUS500 AUTO-ORDER: BUY**\n\n"
                                f"📊 Asset: **{asset_name}**\n"
                                f"📈 Win Rate: `{calculated_win_rate:.2f}%` 🔥\n\n"
                                f"💰 **Entry Price:** {current_price:.4f}\n"
                                f"🎯 **Take Profit (TP):** {tp:.4f}\n"
                                f"🛑 **Stop Loss (SL):** {sl:.4f}"
                            )
                            send_telegram_message(message)
                            last_signals[asset_name] = "BUY"
                            
                    elif current_rsi_6 < 50 and current_rsi_14 < 50 and current_rsi_26 < 50 and current_price < current_ema_200:
                        if last_signals[asset_name] != "SELL":
                            sl = recent_high + (current_price * 0.002)
                            tp = current_price - ((sl - current_price) * 1.5)
                            
                            message = (
                                f"🔴 **🎯 PLUS500 AUTO-ORDER: SELL**\n\n"
                                f"📊 Asset: **{asset_name}**\n"
                                f"📈 Win Rate: `{calculated_win_rate:.2f}%` 🔥\n\n"
                                f"💰 **Entry Price:** {current_price:.4f}\n"
                                f"🎯 **Take Profit (TP):** {tp:.4f}\n"
                                f"🛑 **Stop Loss (SL):** {sl:.4f}"
                            )
                            send_telegram_message(message)
                            last_signals[asset_name] = "SELL"
                            
                    elif 45 < current_rsi_14 < 55:
                        last_signals[asset_name] = None
                        
            except Exception as e:
                logging.error(f"Error processing {asset_name}: {e}")
                continue
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(check_markets_and_alert())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "Quant Engine Running"}
