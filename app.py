from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import secrets
import numpy as np
import random

app = Flask(__name__)

# ============= قاعدة بيانات التراخيص =============
valid_licenses = {
    "ALKING-TEST-123": {
        "email": "your-email@example.com",  # 🔥 غير هذا إلى إيميلك الحقيقي
        "expiry_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "device_id": None,
    },
}
ADMIN_PASSWORD = "admin123"
user_sessions = {}

def generate_random_code():
    return secrets.token_hex(4).upper()

# ============= التحليل الفني (RSI + MACD + BB) =============

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return False, False
    def ema(data, period):
        if len(data) < period:
            return data[-1]
        multiplier = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for i in range(period, len(data)):
            ema_val = (data[i] - ema_val) * multiplier + ema_val
        return ema_val
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    ema_fast_prev = ema(prices[:-1], fast)
    ema_slow_prev = ema(prices[:-1], slow)
    macd_prev = ema_fast_prev - ema_slow_prev
    signal_line = ema(prices, signal)
    signal_prev = ema(prices[:-1], signal)
    bullish = macd_line > signal_line and macd_prev <= signal_prev
    bearish = macd_line < signal_line and macd_prev >= signal_prev
    return bullish, bearish

def calculate_bollinger(prices, period=20, std_dev=2.0):
    if len(prices) < period:
        return False, False
    sma = sum(prices[-period:]) / period
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std = np.sqrt(variance)
    lower_band = sma - (std_dev * std)
    upper_band = sma + (std_dev * std)
    return prices[-1] <= lower_band, prices[-1] >= upper_band

def analyze_market(prices):
    if len(prices) < 50:
        return "HOLD", 0
    rsi = calculate_rsi(prices)
    macd_bullish, macd_bearish = calculate_macd(prices)
    at_lower, at_upper = calculate_bollinger(prices)
    
    # إشارة شراء قوية (4 شروط)
    if rsi < 25 and macd_bullish and at_lower:
        return "BUY", 85
    # إشارة بيع قوية (4 شروط)
    if rsi > 75 and macd_bearish and at_upper:
        return "SELL", 85
    # إشارة شراء متوسطة
    if rsi < 30 and macd_bullish:
        return "BUY", 70
    # إشارة بيع متوسطة
    if rsi > 70 and macd_bearish:
        return "SELL", 70
    return "HOLD", 0

# توليد بيانات شموع محاكاة (لأن السيرفر لا يدعم pyquotex حالياً)
def generate_mock_candles(base_price=1.1000, count=100):
    candles = []
    price = base_price
    for i in range(count):
        change = random.uniform(-0.003, 0.003)
        close = price + change
        candles.append(close)
        price = close
    return candles

# ============= API Routes =============

@app.route('/api/verify_license', methods=['POST'])
def verify_license():
    data = request.get_json()
    license_key = data.get('license_key')
    email = data.get('email')
    device_id = data.get('device_id')
    
    license_info = valid_licenses.get(license_key)
    if not license_info or license_info['email'] != email:
        return jsonify({'success': False, 'message': 'كود غير صالح'}), 401
    if datetime.fromisoformat(license_info['expiry_date']) < datetime.now():
        return jsonify({'success': False, 'message': 'انتهت صلاحية الكود'}), 401
    if license_info['device_id'] is None:
        valid_licenses[license_key]['device_id'] = device_id
    elif license_info['device_id'] != device_id:
        return jsonify({'success': False, 'message': 'الكود مستخدم من جهاز آخر'}), 401
    
    return jsonify({'success': True, 'message': 'كود صالح'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    license_key = data.get('license_key')
    
    license_info = valid_licenses.get(license_key)
    if not license_info or license_info['email'] != email:
        return jsonify({'success': False, 'message': 'رخصة غير صالحة'}), 401
    
    # محاكاة تسجيل الدخول
    user_sessions[license_key] = {'email': email, 'logged_in': True}
    return jsonify({'success': True, 'message': 'تم تسجيل الدخول بنجاح'})

@app.route('/api/trade', methods=['POST'])
def trade():
    data = request.get_json()
    license_key = data.get('license_key')
    pair = data.get('pair')
    amount = data.get('amount')
    duration = data.get('duration')
    
    if license_key not in user_sessions:
        return jsonify({'success': False, 'message': 'لم يتم تسجيل الدخول'}), 401
    
    # جلب بيانات الشموع للتحليل (محاكاة)
    prices = generate_mock_candles()
    signal, confidence = analyze_market(prices)
    
    if signal == "HOLD":
        return jsonify({'success': False, 'message': 'لا توجد إشارة تداول الآن', 'signal': 'HOLD'})
    
    # محاكاة نتيجة الصفقة (نسبة الربح حسب قوة الإشارة)
    win_rate = confidence / 100
    is_win = random.random() < win_rate
    
    return jsonify({
        'success': True,
        'signal': signal,
        'confidence': confidence,
        'result': 'win' if is_win else 'loss',
        'message': f'تم تنفيذ صفقة {signal} ({confidence}%) - {"رابحة 🟢" if is_win else "خاسرة 🔴"}'
    })

@app.route('/api/assets', methods=['POST'])
def get_assets():
    data = request.get_json()
    license_key = data.get('license_key')
    
    # قائمة عملات افتراضية (ستتحدث مع المنصة لاحقاً)
    assets = [
        'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD',
        'NZD/USD', 'USD/CHF', 'BTC/USD', 'ETH/USD', 'XAU/USD',
        'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'EUR/AUD'
    ]
    return jsonify({'success': True, 'assets': assets})

# ============= Admin Routes (لتوليد الأكواد) =============

@app.route('/api/generate_code', methods=['POST'])
def generate_code():
    data = request.get_json()
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    email = data.get('email')
    days = data.get('days', 30)
    new_code = generate_random_code()
    while new_code in valid_licenses:
        new_code = generate_random_code()
    valid_licenses[new_code] = {
        "email": email,
        "expiry_date": (datetime.now() + timedelta(days=days)).isoformat(),
        "device_id": None,
    }
    return jsonify({'success': True, 'code': new_code})

@app.route('/api/list_codes', methods=['POST'])
def list_codes():
    data = request.get_json()
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    codes_list = [{"code": k, **v} for k, v in valid_licenses.items()]
    return jsonify({'success': True, 'codes': codes_list})

@app.route('/api/delete_code', methods=['POST'])
def delete_code():
    data = request.get_json()
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    code = data.get('code')
    if code in valid_licenses:
        del valid_licenses[code]
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Code not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
