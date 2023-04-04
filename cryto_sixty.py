import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from forex_python.converter import CurrencyRates
import get_OHLCV

def calculate_sharpe_ratio(profits):
    # Calculate daily returns
    daily_returns = np.array(profits) / 100 / 365
    # Calculate annualized average return and standard deviation
    avg_return = np.mean(daily_returns)
    std_dev = np.std(daily_returns)
    # Calculate Sharpe ratio
    sharpe_ratio = (avg_return / std_dev) * np.sqrt(365)
    return sharpe_ratio


def sixty_OHLCV(exchange, symbol, timeframe, start_date=None):
    start_date -= timedelta(days=60)
    start_timestamp = int(start_date.timestamp() * 1000)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=start_timestamp, limit=61)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df



def cal_RSI(df, rsi_period=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def ma_signal(df):
    short_sma = df['close'].rolling(20).mean()
    long_sma = df['close'].rolling(50).mean()
    ret_df = pd.DataFrame(np.where(short_sma > long_sma, 1.0, 0.0), index=df.index, columns=['value'])
    return ret_df


def ma_rsi_strategy_sixty_day(past_df, price_df, start_date, end_date, ma_period=20, rsi_period=14, rsi_oversold=30, rsi_overbought=70,
                              stop_loss_pct=0.02, start_capital=1000):
    # Calculate moving average
    ma = ma_signal(past_df)
    # Calculate RSI
    rsi = cal_RSI(past_df, rsi_period)

    # Initialize variables
    position = 0
    stop_loss = 0
    balance = 0
    money = start_capital
    shares = 0
    curr_date = start_date
    cahs_flow=[]
    trades = [{
        'type': 'Begin',
        'price': 0,
        'shares': shares,
        'balance': balance,
        'stop_loss': stop_loss,
        'money': money
    }]


    print(f'Start !!! Today is {curr_date}')
    while curr_date.date() != end_date.date():
        price = price_df['close'][curr_date]
        rsi_val = rsi[curr_date]
        ma_sig = ma['value'][curr_date]
        shares = trades[-1]['shares']
        balance = shares*price
        money = trades[-1]['money']
        print(f'today is {curr_date}, cashflow is {balance+money}, rsi is {rsi_val}, ma signal:{ma_sig}')

        if rsi_val < rsi_oversold and position == 0 and ma_sig == 1:  # Buy signal
            stop_loss = price * (1 - stop_loss_pct)
            shares += money / price
            balance += shares * price
            money -= shares * price
            trades.append({
                'type': 'buy',
                'price': price,
                'shares': shares,
                'balance': balance,
                'stop_loss': stop_loss,
                'money': money
            })
            position = 1

        elif price < stop_loss and position == 1:  # Stop loss triggered
            balance -= shares * price
            money += shares * price
            trades.append({
                'type': 'stop loss',
                'price': price,
                'shares': 0,
                'balance': max(balance, 0),
                'money': money
            })
            position = 0

        elif rsi_val > rsi_overbought and position == 1 and ma_sig == 0:  # Sell signal
            balance -= shares * price
            money += shares * price
            trades.append({
                'type': 'sell',
                'price': price,
                'shares': 0,
                'balance': max(balance, 0),
                'money': money
            })
            position = 0

        curr_date = curr_date + timedelta(days=1)
        df = sixty_OHLCV(exchange, symbol, timeframe, curr_date)
        rsi = cal_RSI(df, rsi_period)
        ma = ma_signal(df)
        if len(trades) != 0:
            cahs_flow.append(money+balance)

    # Clear poisition
    price = price_df['close'][curr_date]
    shares = trades[-1]['shares']
    balance -= shares * price
    money += shares * price
    trades.append({
        'type': 'sell',
        'price': price,
        'shares': 0,
        'balance': balance,
        'money': money
    })

    return [trades, cahs_flow]

def assess_port(money, start_capital, start_date, trades, cash_flow):
    ret = np.diff(cash_flow)/cash_flow[:-1] * 100
    final_return = money - start_capital
    total_profit = np.sum(ret)
    profit_per_trade = np.mean(ret)
    sharpe_ratio = calculate_sharpe_ratio(ret)
    num_trades = len(trades) // 2

    c = CurrencyRates()
    ex = c.get_rate('USD', 'CNY')

    res_np = np.array([total_profit, profit_per_trade, sharpe_ratio, num_trades])
    start = start_date
    res_df = pd.DataFrame(res_np, index=['Total profit', 'Profit per trade', 'Sharpe ratio', 'Number of trades'],
                          columns=[start.strftime('%Y-%m-%d')])
    res_df.loc[f'Final return in USD', start.strftime('%Y-%m-%d')] = final_return
    res_df.loc[f'Final return in CNY', start.strftime('%Y-%m-%d')] = final_return * ex
    res_df.loc['Return Percentage', start.strftime('%Y-%m-%d')] = final_return / start_capital * 100
    res_df.to_excel(f"crypto_start_from_{start.strftime('%Y-%m-%d')}.xlsx")

    print("Total profit: {:.2f}%".format(total_profit))
    print("Profit per trade: {:.2f}%".format(profit_per_trade))
    print("Sharpe ratio: {:.2f}".format(sharpe_ratio))
    print("Number of trades: {}".format(num_trades))
    print(f"Invest {start_capital}, then get {cash_flow[-1]}")
    return res_df


def plot_ma_rsi_strategy(df, trades):
    ma_period = 20
    ma_20 = df['close'].rolling(20).mean()
    ma_50 = df['close'].rolling(50).mean()
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.plot(df.index, df['close'], label='Price')
    ax.plot(df.index, ma_20, label='Moving Average (20 days)')
    ax.plot(df.index, ma_50, linestyle='dashed',label='Moving Average (50 days)')
    start_date = df.index[0]
    for trade in trades:
        if trade['type'] == 'buy':
            if trade['price'] in df['close'].values:
                ax.scatter(df.index[df['close'] == trade['price']][0], trade['price'], color='red', marker='^', s=100)
        elif trade['type'] == 'sell':
            if trade['price'] in df['close'].values:
                ax.scatter(df.index[df['close'] == trade['price']][0], trade['price'], color='green', marker='v', s=100)
    ax.legend()
    print("The graph is using Chinese style(i.e red for buy and green for sell)")
    ax.set_title(
        'MA RSI Strategy Backtest - {} - {} - MA {} - RSI {} / {} - Stop Loss {}%'.format(symbol, start_date, ma_period,
                                                                                          rsi_period, rsi_oversold,
                                                                                          stop_loss_pct))
    plt.show()
    return [fig, ax, plt]

def plot_cashflow(df, cash_flow):
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.plot(df.index, cash_flow, linestyle='-', label='Cashflow')
    ax.legend()
    ax.set_title("Cash flow")
    return fig

if __name__=='__main__':
    api_key = 'input your api_key'
    api_se = 'input your secrete'

    # Connect to Binance API
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_se,
        'enableRateLimit': True,
        'rateLimit': 1000,
    })

    # Set parameters
    symbol = 'BTC/USDT'
    timeframe = '1d'
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    stop_loss_pct = 0.05  # 5%
    start_capital = 1000

    s_sixty = datetime.strptime('2022-01-01', '%Y-%m-%d')
    e_sixty = datetime.today()

    past_df = sixty_OHLCV(exchange, symbol, timeframe, start_date=s_sixty)
    price_df = get_OHLCV.OHLCV(exchange, symbol, timeframe, start_date=s_sixty)

    trades, cash_flow = ma_rsi_strategy_sixty_day(past_df, price_df, s_sixty, e_sixty)

    res_df = assess_port(cash_flow[-1], start_capital, s_sixty, trades, cash_flow)
    res_df.to_excel(f"start from {s_sixty.date()}_sixty.xlsx")
    fig, ax, plt = plot_ma_rsi_strategy(price_df, trades)

    ff = plot_cashflow(price_df[1:], cash_flow)
    fig.savefig(f"start_{s_sixty.date()}_60_rebalnce.png")
    ff.savefig(f"start_{s_sixty.date()}_60_cashflow.png")