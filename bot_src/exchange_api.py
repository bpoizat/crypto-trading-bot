# Contains every function used to interface with the binance API

from binance.client import Client
import logging

from bot_src.decision import Decision

# data sent back when calling get_klines
columns_klines = ['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'Quote_asset_volume',
                    'Number_of_trades', 'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume',
                    'Can_be_ignored']


# Initialize the client to communicate with binance API
def init_client(api_key, api_secret):
    global client
    client = Client(api_key, api_secret)
    client.ping()

# Get klines of a symbol, from start to now, with a width of interval
def get_klines(symbol, interval, start):
    data = client.get_historical_klines(symbol, interval, start, end_str=None)

    # Format data
    # Data returned by binance API is list of lists
    # We want to have it as a dictionary of lists for each type of value
    transposed_data = [list(x) for x in zip(*data)]
    dict_data = dict(zip(columns_klines, transposed_data))
    return dict_data

# Get klines fortimeframes
def get_data(symbol, tf):
    data = {
        'tf': get_klines(symbol, tf['interval'], tf['start']),
    }

    return data

# Return last price for a symbol
def get_last_price(symbol):
    try:
        last_trade = client.get_recent_trades(symbol=symbol, limit=1)
    except Exception:
        raise
    return float(last_trade[-1]['price'])


# Block the bot until the order passed in parameter is filled
# Check the order status every second
def wait_order_filled(order, symbol):
    while order['status'] != 'FILLED':   # Timeout?
        logging.info('Order %d not filled: %s, waiting...', order['orderId'], order['status'])
        try:
            order = client.get_order(symbol=symbol, orderId=order['orderId'])
        except Exception as err:
            logging.error('Error when checking order: %s', err)
        time.sleep(1)


# Place market order
def place_marker_order(decision, symbol, quantity):
    if decision is Decision.BUY:
        order = client.order_market_buy(symbol=symbol, quantity=quantity)
    elif decision is Decision.SELL:
        order = client.order_market_sell(symbol=symbol, quantity=quantity)

    return order


# Get symbol info
def get_symbol_info(symbol):
    return client.get_symbol_info(symbol)


# Get list of symbols
def get_symbol_list(filter):
    # get list of all symbols
    exchange_info = client.get_exchange_info()
    symbol_info = exchange_info['symbols']
    symbol_list = [x['symbol'] for x in symbol_info]
    print('Number of symbols found: ' + str(len(symbol_list)))

    # Filter to keep only USDT
    symbols = [x for x in symbol_list if filter in x]
    print('Number of USDT pair found: ' + str(len(symbols)))
    return symbols
