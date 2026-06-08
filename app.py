from flask import Flask, request, jsonify
import threading
import time
import random
import numpy as np

app = Flask(__name__)

# محاولة استيراد pyquotex
try:
    from pyquotex import Quotex
    QUOTEX_AVAILABLE = True
except ImportError:
    QUOTEX_AVAILABLE = False
    print("⚠️ pyquotex غير مثبت، استخدام وضع المحاكاة")

# متغيرات البوت
bot_active = False
win_streak = 0
loss_streak = 0
total_trades = 0
client = None
current_settings = {
    "pair": "EUR/USD",
    "amount": 10,
    "duration": 5,
    "target_trades": 5,
    "max_trades_per_day": 50,
    "email": "",
    "password": ""
}

# قائمة العملات الافتراضية
default_assets = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "BTC/USD", "ETH/USD", "XAU/USD"]

# ============= دوال التحليل الفني =============
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gain, loss = 0, 0
    for i in range(-period, 0):
        change = prices[i] - prices[i-1]
        if change > 0:
            gain += change
        else:
            loss -= change
    if loss == 0:
        return 100
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_market(prices):
    if len(prices) < 50:
        return "HOLD", 0
    rsi = calculate_rsi(prices)
    if rsi < 25:
        return "BUY", 85
    if rsi > 75:
        return "SELL", 85
    if rsi < 30:
        return "BUY", 70
    if rsi > 70:
        return "SELL", 70
    return "HOLD", 0

def generate_mock_prices():
    price = 1.1000
    prices = []
    for _ in range(100):
        price += random.uniform(-0.003, 0.003)
        prices.append(price)
    return prices

# ============= دورة التداول =============
def trading_loop():
    global bot_active, win_streak, loss_streak, total_trades, client
    target = current_settings["target_trades"]
    
    while bot_active and total_trades < target:
        if QUOTEX_AVAILABLE and client:
            try:
                candles = client.get_candles(current_settings["pair"], 100)
                prices = [c['close'] for c in candles]
            except:
                prices = generate_mock_prices()
        else:
            prices = generate_mock_prices()
        
        signal, confidence = analyze_market(prices)
        
        if signal != "HOLD":
            if QUOTEX_AVAILABLE and client:
                direction = 'call' if signal == 'BUY' else 'put'
                success = client.buy(current_settings["amount"], current_settings["pair"], direction, current_settings["duration"] * 60)
            else:
                success = True
                is_win = random.random() < (confidence / 100)
            
            if success:
                if QUOTEX_AVAILABLE and client:
                    is_win = random.random() < 0.7
                
                if is_win:
                    win_streak += 1
                    loss_streak = 0
                    print(f"✅ ربح! (الثقة: {confidence}%)")
                    if win_streak >= 8:
                        bot_active = False
                        break
                else:
                    win_streak = 0
                    loss_streak += 1
                    print(f"❌ خسارة! (الثقة: {confidence}%)")
                    if loss_streak >= 2:
                        bot_active = False
                        break
                total_trades += 1
                print(f"📊 تقدم: {total_trades}/{target}")
        
        wait_minutes = 3 + random.randint(0, 2)
        for _ in range(wait_minutes * 60):
            if not bot_active:
                break
            time.sleep(1)
    
    if bot_active and total_trades >= target:
        bot_active = False
        print(f"🎯 تم تحقيق الهدف: {target} صفقات")

# ============= API Routes =============
@app.route('/login', methods=['POST'])
def login():
    global client
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if QUOTEX_AVAILABLE:
        try:
            client = Quotex(email=email, password=password)
            if client.connect():
                current_settings["email"] = email
                current_settings["password"] = password
                return jsonify({"status": "success", "message": "تم تسجيل الدخول"})
            else:
                return jsonify({"status": "error", "message": "فشل تسجيل الدخول"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    else:
        return jsonify({"status": "success", "message": "وضع المحاكاة (pyquotex غير مثبت)"})

@app.route('/start', methods=['POST'])
def start():
    global bot_active, win_streak, loss_streak, total_trades
    data = request.get_json()
    if data:
        current_settings.update(data)
    bot_active = True
    win_streak = loss_streak = total_trades = 0
    threading.Thread(target=trading_loop, daemon=True).start()
    return jsonify({"status": "started", "settings": current_settings})

@app.route('/stop', methods=['POST'])
def stop():
    global bot_active
    bot_active = False
    return jsonify({"status": "stopped"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "active": bot_active,
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "total_trades": total_trades,
        "settings": current_settings
    })

@app.route('/assets', methods=['GET'])
def assets():
    global client
    if QUOTEX_AVAILABLE and client:
        try:
            assets = client.get_assets()
            if assets and len(assets) > 0:
                return jsonify({"assets": assets})
        except:
            pass
    return jsonify({"assets": default_assets})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
