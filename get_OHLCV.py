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
    today = datetime.today()
    length = (today - start_date).days
    df_list = []
    s = start_date
    while length > 0:
        start_timestamp = int(s.timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=start_timestamp, limit=min(1000, length + 1))
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df_list.append(df)
        length -= 1000
        s += timedelta(days=1000)
    if len(df_list) > 1:
        final_df_r = pd.concat(df_list)
    else:
        final_df_r = df_list[0]
    return final_df_r


if __name__ == '__main__':
    start_date = datetime.strptime('2020-01-01', '%Y-%m-%d')
    final_df = OHLCV(exchange, symbol, timeframe, start_date)
