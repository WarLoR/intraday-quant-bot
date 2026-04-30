import yfinance as yf
import pandas as pd
import requests
import time
import os
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_alert(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

stocks = ["SBIN.NS","ITC.NS","AXISBANK.NS","NHPC.NS"]

def calculate_vwap(df):
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

def run_bot():
    print("🚀 Bot loop started")

    while True:
        try:
            messages = []

            for stock in stocks:
                data = yf.download(stock, period="1d", interval="5m", progress=False)

                if data.empty or len(data) < 10:
                    continue

                data['VWAP'] = calculate_vwap(data)

                latest = data.iloc[-1]
                prev = data.iloc[-2]

                price = latest['Close']
                vwap = latest['VWAP']

                vol = latest['Volume']
                avg_vol = data['Volume'].mean()

                if prev['Close'] < prev['VWAP'] and price > vwap and vol > 1.5 * avg_vol:
                    messages.append(f"🟢 BUY {stock} @ {round(price,2)}")

                elif prev['Close'] > prev['VWAP'] and price < vwap:
                    messages.append(f"🔴 SELL {stock} @ {round(price,2)}")

            if messages:
                send_alert("📊 VWAP ALERTS\n\n" + "\n".join(messages))

            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)

threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
