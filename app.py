from flask import Flask, render_template, request, jsonify, send_from_directory, redirect
import yfinance as yf
import talib
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os
import openai
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required
from .model import User
from .database import db
from werkzeug.security import generate_password_hash

login_manager = LoginManager()
login_manager.login_view = '/login'
csrf = CSRFProtect()
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///db.sqlite"
app.config['SECRET_KEY'] = os.urandom(32)
db.init_app(app)
login_manager.init_app(app)


with app.app_context():
    db.create_all()

#OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")


@login_manager.user_loader
def load_user(user):
    return User.query.get(int(user))

def fetch_stock_data(symbol, start_date=None, end_date=None):
    if not symbol:
        raise ValueError("股票代碼不能為空")
        
    if not start_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
    
    stock = yf.Ticker(symbol)
    stock_data = stock.history(start=start_date, end=end_date)
    if stock_data.empty:
        raise ValueError(f"找不到股票代碼 {symbol} 的數據")
    return stock_data

def calculate_indicators_with_signals(stock_data):
    indicators = {}
    signals = {}

    # 年化波動
    indicators['volatility'] = stock_data['Close'].pct_change().std() * np.sqrt(252) * 100
    # 區間報酬
    indicators['percent_change'] = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[0]) / stock_data['Close'].iloc[0]) * 100

    # MA
    ma5 = talib.MA(stock_data['Close'], timeperiod=5)
    ma20 = talib.MA(stock_data['Close'], timeperiod=20)
    ma60 = talib.MA(stock_data['Close'], timeperiod=60)
    indicators['ma5'] = ma5
    indicators['ma20'] = ma20
    indicators['ma60'] = ma60

    signals['ma'] = []
    for i in range(1, len(stock_data)):
        if ma5.iloc[i] > ma20.iloc[i] and ma5.iloc[i-1] <= ma20.iloc[i-1]:
            signals['ma'].append({'position': i, 'type': 'buy'})
        elif ma5.iloc[i] < ma20.iloc[i] and ma5.iloc[i-1] >= ma20.iloc[i-1]:
            signals['ma'].append({'position': i, 'type': 'sell'})

    # KD
    k, d = talib.STOCH(stock_data['High'], stock_data['Low'], stock_data['Close'])
    indicators['k'] = k
    indicators['d'] = d

    signals['kd'] = []
    for i in range(1, len(k)):
        if k.iloc[i] > d.iloc[i] and k.iloc[i-1] <= d.iloc[i-1]:
            signals['kd'].append({'position': i, 'type': 'buy'})
        elif k.iloc[i] < d.iloc[i] and k.iloc[i-1] >= d.iloc[i-1]:
            signals['kd'].append({'position': i, 'type': 'sell'})

    # MACD
    macd, signal, hist = talib.MACD(stock_data['Close'])
    indicators['macd'] = macd
    indicators['macd_signal'] = signal
    indicators['macd_hist'] = hist

    signals['macd'] = []
    for i in range(1, len(macd)):
        if macd.iloc[i] > signal.iloc[i] and macd.iloc[i-1] <= signal.iloc[i-1]:
            signals['macd'].append({'position': i, 'type': 'buy'})
        elif macd.iloc[i] < signal.iloc[i] and macd.iloc[i-1] >= signal.iloc[i-1]:
            signals['macd'].append({'position': i, 'type': 'sell'})

    # RSI
    rsi = talib.RSI(stock_data['Close'])
    indicators['rsi'] = rsi

    signals['rsi'] = []
    for i in range(1, len(rsi)):
        if rsi.iloc[i] < 30 and rsi.iloc[i-1] >= 30:
            signals['rsi'].append({'position': i, 'type': 'buy'})
        elif rsi.iloc[i] > 70 and rsi.iloc[i-1] <= 70:
            signals['rsi'].append({'position': i, 'type': 'sell'})

    return indicators, signals

def get_gpt_analysis(stock_data, indicators, signals):
    try:
        # 吃最進30天股價
        recent_data = stock_data.tail(30).copy()
        recent_close = recent_data['Close'].iloc[-1]
        recent_volume = recent_data['Volume'].iloc[-1]
        prev_close = recent_data['Close'].iloc[-2]
        avg_volume = recent_data['Volume'].mean()

        # 計算價格和成交量變化
        price_change = ((recent_close - prev_close) / prev_close) * 100
        volume_change = ((recent_volume - avg_volume) / avg_volume) * 100

        # 計算歷史價格
        price_history = {
            '7天前': stock_data['Close'].iloc[-7] if len(stock_data) >= 7 else None,
            '30天前': stock_data['Close'].iloc[-30] if len(stock_data) >= 30 else None,
            '90天前': stock_data['Close'].iloc[-90] if len(stock_data) >= 90 else None
        }
        
        volume_history = {
            '7天平均': stock_data['Volume'].tail(7).mean(),
            '30天平均': stock_data['Volume'].tail(30).mean(),
            '90天平均': stock_data['Volume'].tail(90).mean()
        }

        # 計算各期間漲跌幅
        price_changes = {}
        for period, price in price_history.items():
            if price is not None:
                change = ((recent_close - price) / price) * 100
                price_changes[period] = change

        # 過去30天的每日價格
        daily_data = []
        for i in range(29, -1, -1):
            if i < len(recent_data):
                date = recent_data.index[i].strftime('%Y-%m-%d')
                daily_data.append(
                    f"日期: {date}, "
                    f"開盤: {recent_data['Open'].iloc[i]:.2f}, "
                    f"最高: {recent_data['High'].iloc[i]:.2f}, "
                    f"最低: {recent_data['Low'].iloc[i]:.2f}, "
                    f"收盤: {recent_data['Close'].iloc[i]:.2f}, "
                    f"成交量: {recent_data['Volume'].iloc[i]:,.0f}"
                )

        # GPT 分析
        prompt = f"""請分析以下股票技術指標數據並提供專業且精簡的投資建議：

            1. 價格分析：
            - 最新收盤價：{recent_close:.2f}
            - 日漲跌幅：{price_change:.2f}%
            - 年化波動率：{indicators['volatility']:.2f}%
            - 區間報酬率：{indicators['percent_change']:.2f}%

            2. 歷史價格走勢：
            - 7天前價格：{price_history['7天前']:.2f}，漲跌幅：{price_changes.get('7天前', 'N/A'):.2f}%
            - 30天前價格：{price_history['30天前']:.2f}，漲跌幅：{price_changes.get('30天前', 'N/A'):.2f}%
            - 90天前價格：{price_history['90天前']:.2f}，漲跌幅：{price_changes.get('90天前', 'N/A'):.2f}%

            3. 成交量分析：
            - 最新成交量：{recent_volume:,.0f}
            - 相對平均成交量變化：{volume_change:.2f}%
            - 7天平均成交量：{volume_history['7天平均']:,.0f}
            - 30天平均成交量：{volume_history['30天平均']:,.0f}
            - 90天平均成交量：{volume_history['90天平均']:,.0f}

            4. 技術指標：
            MA指標：
            - MA5：{indicators['ma5'].iloc[-1]:.2f}
            - MA20：{indicators['ma20'].iloc[-1]:.2f}
            - MA60：{indicators['ma60'].iloc[-1]:.2f}

            KD指標：
            - K值：{indicators['k'].iloc[-1]:.2f}
            - D值：{indicators['d'].iloc[-1]:.2f}

            MACD指標：
            - MACD：{indicators['macd'].iloc[-1]:.2f}
            - Signal：{indicators['macd_signal'].iloc[-1]:.2f}

            RSI指標：{indicators['rsi'].iloc[-1]:.2f}

            5. 最近30天每日交易數據：
            {chr(10).join(daily_data)}

            6. 最近買賣訊號：
            {str(signals)}

            請提供：
            1. 綜合技術分析（包含對過去30天價量趨勢的分析）
            2. 短期、長期走勢研判
            3. 建議操作策略 (需要壓力支撐、技術線型的型態、買賣交易操作的策略)"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一位專業的股票技術分析師，擅長解讀技術指標、歷史價量及型態，並提供繁體中文投資建議。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT分析錯誤: {str(e)}")
        return "無法獲取GPT分析結果"

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    from .form import LoginForm
    form = LoginForm()

    if form.validate_on_submit():        
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        login_user(user)
        return redirect('/')

    return render_template('login.html', form=form)


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    from .form import SignupForm
    form = SignupForm()

    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password1.data
    
        new_user = User(email=email, name=username, password=generate_password_hash(password, method='scrypt'))
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login') 

    return render_template('signup.html', form=form)


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect('/login')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/static/<path:path>')
def send_static_file(path):
    return send_from_directory('static', path)

@app.route('/query', methods=['POST'])
def query_stock():
    data = request.json
    symbol = data.get('symbol')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    try:
        stock_data = fetch_stock_data(symbol, start_date, end_date)
        indicators, signals = calculate_indicators_with_signals(stock_data)
        
        # GPT 分析
        gpt_analysis = get_gpt_analysis(stock_data, indicators, signals)

        serializable_indicators = {}
        for key, value in indicators.items():
            if isinstance(value, pd.Series):
                serializable_indicators[key] = [float(x) if pd.notna(x) else None for x in value]
            else:
                serializable_indicators[key] = float(value)

        stock_data_dict = stock_data.reset_index().to_dict(orient='records')

        return jsonify({
            'stock_data': stock_data_dict,
            'indicators': serializable_indicators,
            'signals': signals,
            'gpt_analysis': gpt_analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
