import ccxt
import pandas as pd
from datetime import datetime, timedelta

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


def OHLCV(exchange, symbol, timeframe, start_date=None):
    start_timestamp = int(start_date.timestamp() * 1000)
    today = datetime.today()
    length = (today - start_date).days
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=start_timestamp, limit=1000)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    if length > 1000:
        another = today - timedelta(days=length-1000)
        another_stamp = int(another.timestamp() * 1000)
        new = exchange.fetch_ohlcv(symbol, timeframe, since=another_stamp, limit=1000)
        new_df = pd.DataFrame(new, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        new_df['timestamp'] = pd.to_datetime(new_df['timestamp'], unit='ms')
        new_df.set_index('timestamp', inplace=True)
        final_df = pd.concat([df, new_df])
    else:
        final_df = df
    return final_df


if __name__=='__main__':
    start_date = datetime.strptime('2020-01-01', '%Y-%m-%d')
    final_df = OHLCV(exchange, symbol, timeframe, start_date)
