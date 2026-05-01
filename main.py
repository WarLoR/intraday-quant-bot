import yfinance as yf
import pandas as pd
import requests
import time
import os
from flask import Flask
import threading

# ======================
# WEB SERVER (RENDER REQUIREMENT)
# ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

# ======================
# TELEGRAM CONFIG
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_alert(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Missing BOT_TOKEN or CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ======================
# STOCK LIST (EDITABLE)
# ======================
stocks = ["SBIN.NS","ITC.NS","AXISBANK.NS","NHPC.NS"]

# ======================
# VWAP CALCULATION
# ======================
def calculate_vwap(df):
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

# ======================
# TRACK OPEN TRADES
# ======================
open_positions = {}

# ======================
# MAIN BOT LOGIC
# ======================
def run_bot():
    print("🚀 Bot loop started")

    while True:
        try:
            messages = []

            for stock in stocks:
                data = yf.download(stock, period="1d", interval="5m", progress=False)

                if data.empty or len(data) < 20:
                    continue

                data['VWAP'] = calculate_vwap(data)

                # ======================
                # OPENING RANGE (FIRST 15 MIN)
                # ======================
                opening_range = data.iloc[:3]
                orb_high = opening_range['High'].max()
                orb_low = opening_range['Low'].min()

                latest = data.iloc[-1]
                prev = data.iloc[-2]

                price = latest['Close']
                vwap = latest['VWAP']

                vol = latest['Volume']
                avg_vol = data['Volume'].mean()

                body_size = abs(latest['Close'] - latest['Open'])
                candle_range = latest['High'] - latest['Low']

                # ======================
                # ENTRY LOGIC (ANTI FAKE BREAKOUT)
                # ======================
                if stock not in open_positions:

                    if (
                        price > orb_high and
                        price > vwap and
                        vol > 1.5 * avg_vol and
                        latest['Close'] > latest['Open'] and
                        body_size > 0.5 * candle_range   # strong candle
                    ):
                        open_positions[stock] = price
                        messages.append(f"🟢 BUY {stock} @ {round(price,2)}")

                # ======================
                # EXIT LOGIC (SMARTER)
                # ======================
                else:
                    entry_price = open_positions[stock]

                    change = (price - entry_price) / entry_price

                    # Target Hit
                    if change >= 0.015:
                        messages.append(f"🎯 TARGET HIT {stock} @ {round(price,2)}")
                        del open_positions[stock]

                    # Stop Loss
                    elif change <= -0.007:
                        messages.append(f"🔴 STOP LOSS {stock} @ {round(price,2)}")
                        del open_positions[stock]

                    # VWAP Breakdown Exit
                    elif prev['Close'] > prev['VWAP'] and price < vwap:
                        messages.append(f"⚠️ EXIT VWAP {stock} @ {round(price,2)}")
                        del open_positions[stock]

            if messages:
                send_alert("📊 ORB + VWAP SYSTEM\n\n" + "\n".join(messages))

            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)

# ======================
# START BOT THREAD
# ======================
threading.Thread(target=run_bot).start()

# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
