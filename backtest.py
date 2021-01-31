# coding=utf-8

from binance.client import Client
import os
import csv
import numpy as np
from tqdm.contrib.concurrent import process_map

from exchange_api import columns_klines
from indicators import calculate_indicators
from bot_io.config import *
import strategy

from decision import Decision

full_data = []
p_strategy = {}

def extract_backtest_data(symbol):
    print('Extracting symbol: ' + symbol)

    # Read config file
    config = read_config()
    config_binance = config['Binance']

    # Read backtest config file
    config_bt = read_backtest_param()
    config_backtest = config_bt['Backtest']

    # create binance client
    client = Client(config_binance['api_key'], config_binance['api_secret'])

    # List of KLine intervals to request:
    # klines = ['1d','12h','8h','6h','4h','2h','1h','30m','15m','5m']    # remove 1m and 3m because it takes so much time
    klines = ['3m','1m']

    folder = os.path.join(config_backtest['path'], symbol)

    if not os.path.isdir(folder):
        os.mkdir(folder)

    for kline in klines:
        print('Extracted: ' + kline + ' ' + symbol)

        filename = os.path.join(folder, kline)
        filename += '.csv'
        if os.path.exists(filename):
            print('Already exists, skipping')
            continue

        data = client.get_historical_klines(symbol, kline, config_backtest['start'], config_backtest['end'])

        print('To ' + filename)

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)


def parallel_extraction():
    # multithreaded version

    # Read config file
    config = read_config()
    config_binance = config['Binance']

    # create binance client
    client = Client(config_binance['api_key'], config_binance['api_secret'])
    client.ping()

    # get list of all symbols
    exchange_info = client.get_exchange_info()
    symbol_info = exchange_info['symbols']
    symbol_list = [x['symbol'] for x in symbol_info]
    print('Number of symbols found: ' + str(len(symbol_list)))

    # Filter to keep only USDT
    symbols = [x for x in symbol_list if 'USDT' in x]
    print('Number of USDT pair found: ' + str(len(symbols)))
    print(symbols)

    print('Backtesting...')
    results = process_map(extract_backtest_data, symbols, max_workers=12)


def get_kline_from_csv(path, symbol, interval):
    folder = os.path.join(path, symbol)

    # import long
    filename = os.path.join(folder, interval)
    filename += '.csv'
    data = []

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        data = list(reader)

    transposed_data = [list(x) for x in zip(*data)]
    dict_data = dict(zip(columns_klines, transposed_data))
    return dict_data


def get_data_from_csv(path, symbol, tf):

    data = {
        'tf': get_kline_from_csv(path, symbol, tf),
    }

    return data


def print_current_kline(kline, t):
    print('Low', full_data['tf']['Low'][t])
    print('Open', full_data['tf']['Open'][t])
    print('Close', full_data['tf']['Close'][t])
    print('High', full_data['tf']['High'][t])


def backtest_loop(list_param):
    # Load params
    p_stop_loss = list_param['stop_loss']
    p_take_profit = list_param['take_profit']
    p_indicators = {
        'slow_ema': list_param['slow_ema'],
        'fast_ema': list_param['fast_ema'],
    }
    symbol = list_param['symbol']
    p_strategy = list_param['p_strategy']
    money = p_strategy['money']
    fee = list_param['fee']

    # Calculate indicators
    indicators = calculate_indicators(full_data, p_indicators)

    # Initialize state
    state = {
        "buy_status": False, 
        "take_profit": 0.0, 
        "stop_loss": 0.0, 
    }

    # Backtest results
    negative_trade = 0
    positive_trade = 0
    benefits = 0
    fees = 0

    # Looping on the backtest data
    # We start at slow-ema
    for t in range(p_indicators['slow_ema'], len(indicators['slow_ema'])):
        indicator_t = {
            'slow_ema': indicators['slow_ema'][:t],
            'fast_ema': indicators['fast_ema'][:t]
        }

        # No trade going on
        if not state['buy_status']:
            # Analyse indicators following strategy
            decision = strategy.enter_trade(indicator_t, p_strategy)

            # Go long
            if decision is Decision.BUY:
                state['buy_status'] = True
                entry_price = float(full_data['tf']['Close'][t])
                quantity = money/entry_price
                state = {
                    'buy_status': True,
                    'stop_loss': entry_price*(1-p_stop_loss),
                    'take_profit': entry_price*(1+p_take_profit),
                }

                # print('Buying at', entry_price, 'stop_loss:', state['stop_loss'], 'take_profit:', state['take_profit'], 'time:', t)
                fees += fee*money

        # Long trade going on, we are long
        elif state['buy_status']:
            decision = Decision.NONE
            # print_current_kline(full_data, t)
            # print('Stop loss is',state['stop_loss'])

            # First we check if we hit the stop loss or take profit threshold
            if state['stop_loss'] > float(full_data['tf']['Low'][t]):
                # stop_loss was hit
                sell_price = state['stop_loss']
                benefits += (sell_price - entry_price)*quantity
                if sell_price > entry_price:
                    positive_trade += 1
                else:
                    negative_trade += 1
                state['buy_status'] = False
                # print('Selling/stoploss at', sell_price, 'benefits:', benefits, 'time:', t)
            elif state['take_profit'] < float(full_data['tf']['High'][t]):
                # if we would buy again, don't sell and raise take_profit/stop_loss
                if strategy.enter_trade(indicators, p_strategy) is Decision.BUY:
                    decision = Decision.BUY
                    pass
                else:
                    # we can take profit by selling at market price
                    sell_price = state['take_profit']
                    benefits += (sell_price - entry_price)*quantity
                    positive_trade += 1
                    state['buy_status'] = False
                    # print('Selling/takeprofit at', sell_price, 'benefits:', benefits, 'time:', t)

            if decision is Decision.NONE:
                decision = strategy.exit_trade(indicators, p_strategy)
                # Exit the trade by shorting
                if decision is Decision.SELL:
                    sell_price = float(full_data['tf']['Close'][t])
                    benefits += (sell_price - entry_price)*quantity
                    state['buy_status'] = False
                    # print('Shorting at', sell_price, 'benefits:', benefits, 'time:', t)
                    if sell_price > entry_price:
                        positive_trade += 1
                    else:
                        negative_trade += 1

            # here buy means increasing stop_loss and take_profit
            elif decision is Decision.BUY:
                # take_profit increases by half the percentage
                state['stop_loss'] = state['take_profit']*(1-p_stop_loss)
                state['take_profit'] = state['take_profit']*(1+p_take_profit)
                # print('Increasing take profit', state['take_profit'], 'stop loss', state['stop_loss'], 'benefits:', benefits, 'time:', t)
    
    number_trade = positive_trade + negative_trade
    benefits -= fees

    result = {
        'stop_loss': p_stop_loss,
        'take_profit': p_take_profit,
        'slow_ema': p_indicators['slow_ema'],
        'fast_ema': p_indicators['fast_ema'],
        'number_trade': number_trade,
        'positive_trade': positive_trade/number_trade if number_trade != 0 else 0,
        'negative_trade': negative_trade/number_trade if number_trade != 0 else 0,
        'benefits': benefits/money,
    }
    return result


if __name__ == '__main__':
    # Read backtest config file
    config_bt = read_backtest_param()

    # reading all parameters
    symbol, tf, p_indicators, p_strategy = read_param()

    full_data = get_data_from_csv(config_bt['Backtest']['path'], symbol, tf['interval'])
    results = []

    # multithread version
    list_param = []
    for stop_loss in np.arange(0.02, 0.11, 0.01):
        for take_profit in np.arange(0.02, 0.11, 0.01):
            for slow_ema in range(15, 25, 1):
                for fast_ema in range(5, 15, 1):
                    list_param.append({
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'slow_ema': slow_ema,
                        'fast_ema': fast_ema,
                        'symbol': symbol,
                        'p_strategy': p_strategy,
                        'fee': float(config_bt['Backtest']['fee']),
                    })

    print('Backtesting...')
    results = process_map(backtest_loop, list_param, max_workers=12, chunksize=12)
    # print(results)

    # Write results to CSV
    folder = os.path.join(config_bt['Backtest']['path_result'], symbol)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    filename = os.path.join(folder, tf['interval'])
    filename += '.csv'

    with open(filename, 'w', newline='') as f:
        fieldnames = ['stop_loss', 'take_profit', 'slow_ema', 'fast_ema', 'number_trade', 'positive_trade', 'negative_trade', 'benefits']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            writer.writerow(row)
