# coding=utf-8

from binance.client import Client
import configparser
import os
import csv
import dateparser
import math
import numpy as np
from multiprocessing import Pool
from tqdm import tqdm

from exchange_api import get_klines, columns_klines
from indicators import calculate_indicators
from bot_io.config import *
import strategy

from decision import Decision

config = configparser.ConfigParser()
full_data = []
symbol = ''
tf = {}
p_indicators = {}
p_strategy = {}
# p_stop_loss = 0.0
# p_take_profit = 0.0
fee = 0.0
money = 0.0

def extract_backtest_data():
    # Read config file
    config = configparser.ConfigParser()
    config.read('bot.ini')
    config_binance = config['Binance']
    config_backtest = config['Backtest']

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

    # List of KLine intervals to request:
    klines = ['1d','12h','8h','6h','4h','2h','1h','30m','15m','5m']    # remove 1m and 3m because it takes so much time

    # Iterate over list of symbols:
    for symbol in symbols:
        folder = os.path.join(config_backtest['path'], symbol)

        if not os.path.isdir(folder):
            os.mkdir(folder)
        
        for kline in klines:
            print('Extract: ' + kline + ' ' + symbol)

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
    long_interval = tf['l_interval']
    short_interval = tf['s_interval']
    
    data = {
        'long_tf': get_kline_from_csv(path, symbol, long_interval),
        'short_tf': get_kline_from_csv(path, symbol, short_interval),
    }

    return data


def backtest_loop(list_param):
    # Load params
    p_stop_loss = list_param['stop_loss']
    p_take_profit = list_param['take_profit']

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
    # We start at 26+9 = 35 (MACD-slow + signal) * 6 for 6h->1h
    for t in range(35*6, len(indicators['rsi'])):
        indicator_t = {
            'macdhist': indicators['macdhist'][:math.ceil(t/6)],
            'rsi': indicators['rsi'][:t]
        }

        # No trade going on
        if not state['buy_status']:
            # Analyse indicators following strategy
            decision = strategy.enter_trade(indicator_t, p_strategy)

            # Go long
            if decision is Decision.BUY:
                state['buy_status'] = True
                entry_price = float(full_data['short_tf']['Close'][t])
                quantity = money/entry_price
                state = {
                    'buy_status': True,
                    'stop_loss': entry_price*(1-p_stop_loss),
                    'take_profit': entry_price*(1+p_take_profit),
                }

                # print('Buying for', money , 'at', buy_price, 'qty', quantity, 'time', t)
                fees += fee*money

        # Long trade going on, we are long
        elif state['buy_status']:
            decision = Decision.NONE

            # First we check if we hit the stop loss or take profit threshold
            if float(full_data['short_tf']['Low'][t]) < state['stop_loss']:
                # stop_loss was hit
                sell_price = stop_loss
                benefits += (sell_price - entry_price)*quantity
                negative_trade += 1
                state['buy_status'] = False
            elif float(full_data['short_tf']['High'][t]) > state['take_profit']:
                # if we would buy again, don't sell and raise take_profit/stop_loss
                if strategy.enter_trade(indicators, p_strategy) is Decision.BUY:
                    decision = Decision.BUY
                else:
                    # we can take profit by selling at market price
                    sell_price = take_profit
                    benefits += (sell_price - entry_price)*quantity
                    positive_trade += 1
                    state['buy_status'] = False

            if decision is Decision.NONE:
                decision = strategy.exit_trade(indicators, p_strategy)
                # Exit the trade by shorting
                if decision is Decision.SELL:
                    sell_price = take_profit
                    benefits += (sell_price - entry_price)*quantity
                    state['buy_status'] = False
                    if sell_price > entry_price:
                        positive_trade += 1
                    else:
                        negative_trade += 1

            # here buy means increasing stop_loss and take_profit
            elif decision is Decision.BUY:
                # take_profit increases by half the percentage
                state['stop_loss'] = state['take_profit']
                state['take_profit'] = state['take_profit']*(1+p_take_profit/2)
    
    number_trade = positive_trade + negative_trade
    benefits -= fees

    result = {
        'stop_loss': p_stop_loss,
        'take_profit': p_take_profit,
        'number_trade': number_trade,
        'positive_trade': positive_trade/number_trade if number_trade != 0 else 0,
        'negative_trade': negative_trade/number_trade if number_trade != 0 else 0,
        'benefits': benefits,
    }
    return result


if __name__ == '__main__':
    # Read backtest config file
    config_bt = read_backtest_param()

    # reading all parameters
    symbol, tf, p_indicators, p_strategy, p_stop_loss, p_take_profit, _, _ = read_param()
    fee = float(config_bt['Backtest']['fee'])
    money = float(config_bt['Backtest']['money'])

    full_data = get_data_from_csv(config_bt['Backtest']['path'], symbol, tf)
    results = []

    # multithread version
    list_param = []
    for stop_loss in np.arange(0.03, 0.11, 0.01):
        for take_profit in np.arange(0.03, 0.11, 0.01):
            list_param.append({
                'stop_loss': stop_loss,
                'take_profit': take_profit,
            })

    print('Backtesting...')
    with Pool(12) as p:
        results = list(tqdm(p.imap(backtest_loop, list_param), total=len(list_param)))

    # Write results to CSV
    folder = os.path.join(config_bt['Backtest']['path_result'], symbol)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    filename = os.path.join(folder, tf['l_interval'] + tf['s_interval'])
    filename += '.csv'

    with open(filename, 'w', newline='') as f:
        fieldnames = ['stop_loss', 'take_profit', 'number_trade', 'positive_trade', 'negative_trade', 'benefits']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            writer.writerow(row)
