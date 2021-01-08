from binance.client import Client

columns = ['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'Quote_asset_volume',
            'Number_of_trades', 'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume',
            'Can_be_ignored']

def get_klines(client, symbol, interval, start):
    data = client.get_historical_klines(symbol, interval, start, end_str=None)

    # Format data
    # Data returned by binance API is list of lists
    # We want to have it as a dictionary of lists for each type of value
    transposed_data = [list(x) for x in zip(*data)]
    dict_data = dict(zip(columns, transposed_data))
    return dict_data

def get_data(client, param_data):
    # We need long and short timeframe
    data = {
        'long_tf': get_klines(client, param_data['symbol'], param_data['long_interval'], param_data['long_start']),
        'short_tf': get_klines(client, param_data['symbol'], param_data['short_interval'], param_data['short_start'])
    }

    return data

def get_last_trade(client, param_data):
    last_trade = client.get_recent_trades(symbol=param_data['symbol'], limit=1)

    return last_trade