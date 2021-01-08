# coding=utf-8

from binance.client import Client
import configparser
import os
import csv
import dateparser
import math
import numpy as np
from linetimer import CodeTimer # to profile and optimize
from multiprocessing import Pool
from tqdm import tqdm

from binance_data import get_klines, columns
from indicators import calculate_indicators
from strategy import *

config = configparser.ConfigParser()
full_data = []

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
    dict_data = dict(zip(columns, transposed_data))
    return dict_data


def get_data_from_csv(config_backtest, param_data):
    symbol = param_data['symbol']
    long_interval = param_data['long_interval']
    short_interval = param_data['short_interval']
    path = config_backtest['path']
    
    data = {
        'long_tf': get_kline_from_csv(path, symbol, long_interval),
        'short_tf': get_kline_from_csv(path, symbol, short_interval),
    }

    return data


def backtest_loop(list_param):
    # load params
    p_stop_loss = list_param['stop_loss']
    p_take_profit = list_param['take_profit']
    p_rsi_high = list_param['rsi_high_limit']
    p_rsi_low = list_param['rsi_low_limit']

    config['Strategy']['rsi_low_limit'] = str(p_rsi_low)
    config['Strategy']['rsi_high_limit'] = str(p_rsi_high)

    # Load data previously extracted from binance
    short_data = full_data['short_tf']

    # Calculate indicators
    indicators = calculate_indicators(full_data, config['Indicators'])

    buy_order_placed = False
    sell_order_placed = False

    money_initial = float(config['Backtest']['money'])
    fee = float(config['Backtest']['fee'])

    # For result analysis
    quantity = 0
    positive_trade = 0
    negative_trade = 0
    fees = 0
    money = money_initial

    # We start at 26+9 = 35 (MACD-slow + signal) * 6 for 6h->1h
    for t in range(35*6, len(indicators['rsi'])):
        indicator_t = {
            'macdhist': indicators['macdhist'][:math.ceil(t/6)],
            'rsi': indicators['rsi'][:t]
        }

        # Analyse indicators following strategy
        decision = strategy1(indicator_t, config['Strategy'], buy_order_placed)

        # No order placed
        if buy_order_placed == False and sell_order_placed == False:
            if decision == 'buy':
                buy_order_placed = True
                buy_price = float(short_data['Close'][t])
                stop_loss = buy_price * (1-p_stop_loss)
                take_profit = buy_price * (1+p_take_profit)
                quantity = money/buy_price
                # print('Buying for', money , 'at', buy_price, 'qty', quantity, 'time', t)
                fees += fee*money
                # put all money ou keep benefits?
                money = 0
            # elif decision == 'sell':
            #     sell_order_placed = True
            #     sell_price = float(short_data['Close'][t])
            #     stop_loss = sell_price * (1+float(config['Strategy']['stop_loss']))
            #     take_profit = sell_price * (1-float(config['Strategy']['take_profit']))
            #     quantity = money/sell_price
            #     # print('Selling for', money , 'at', sell_price, 'qty', quantity, 'time', t)
            #     fees += money*fee
            #     money += money # or quantity*sell_price

        # A buy order was placed (and fullfilled)
        elif buy_order_placed == True:
            if stop_loss > float(short_data['Low'][t]):
                # stop_loss was hit
                sell_price = stop_loss
                buy_order_placed = False
                money += (sell_price * quantity) * (1-fee)
                quantity = 0
                negative_trade += 1
                # print('Stop_loss hit at', sell_price, 'time', t, '\tMoney is now', money)
            elif take_profit < float(short_data['Close'][t]):
                # we can take profit by selling at market price
                sell_price = take_profit
                buy_order_placed = False
                money += (sell_price * quantity) * (1-fee)
                quantity = 0
                positive_trade += 1
                # print('Taking profit at', sell_price, 'qty', quantity, 'time', t, '\tMoney is now', money)
            elif decision == 'sell':
                sell_price = float(short_data['Close'][t])
                buy_order_placed = False
                money += (sell_price * quantity) * (1-fee)
                quantity = 0
                if sell_price <= buy_price:
                    negative_trade += 1
                else:
                    positive_trade += 1
                # print('selling at market price', sell_price, 'time', t, '\tMoney is now', money)
        
        # # A sell order was placed (and fullfilled)
        # elif sell_order_placed == True:
        #     if stop_loss < float(short_data['High'][t]):
        #         # stop_loss was hit
        #         buy_price = stop_loss
        #         sell_order_placed = False
        #         money -= (buy_price * quantity) * (1-fee)
        #         negative_trade += 1
        #         # print('Stop_loss hit at', buy_price, 'time', t, '\tMoney is now', money)
        #     elif take_profit > float(short_data['Close'][t]):
        #         # we can take profit by buying at market price
        #         buy_price = take_profit
        #         sell_order_placed = False
        #         money -= (buy_price * quantity) * (1-fee)
        #         positive_trade += 1
        #         # print('Taking profit at', buy_price, 'qty', quantity, 'time', t, '\tMoney is now', money)
        #     elif decision == 'buy':
        #         buy_price = float(short_data['Close'][t])
        #         sell_order_placed = False
        #         money -= (buy_price * quantity) * (1-fee)
        #         if sell_price <= buy_price:
        #             negative_trade += 1
        #         else:
        #             positive_trade += 1
        #         # print('buying at market price', sell_price, 'time', t, '\tMoney is now', money)


    number_trade = positive_trade + negative_trade
    result = {
        'stop_loss': p_stop_loss,
        'take_profit': p_take_profit,
        'rsi_low_limit': p_rsi_high,
        'rsi_high_limit': p_rsi_low,
        'number_trade': number_trade,
        'positive_trade': positive_trade/number_trade if number_trade != 0 else 0,
        'negative_trade': negative_trade/number_trade if number_trade != 0 else 0,
        'benefits': ((money + quantity*float(short_data['Close'][-1]) - fees)/money_initial - 1),
    }
    return result


if __name__ == '__main__':
    # Read config file
    # config = configparser.ConfigParser()
    config.read('bot.ini')

    full_data = get_data_from_csv(config['Backtest'], config['Data'])
    results = []

    # multithread version
    list_param = []
    for stop_loss in np.arange(0.03, 0.11, 0.01):
        for take_profit in np.arange(0.03, 0.11, 0.01):
            for rsi_low_limit in range(0, 101, 10):
                for rsi_high_limit in range(0, 101, 10):
                    list_param.append({
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'rsi_low_limit': rsi_low_limit,
                        'rsi_high_limit': rsi_high_limit
                    })

    print('Backtesting...')
    with Pool(12) as p:
        results = list(tqdm(p.imap(backtest_loop, list_param), total=len(list_param)))

    # Write results to CSV
    folder = os.path.join(config['Backtest']['path_result'], config['Data']['symbol'])
    if not os.path.isdir(folder):
        os.mkdir(folder)
    filename = os.path.join(folder, config['Data']['long_interval'] + config['Data']['short_interval'])
    filename += '.csv'

    with open(filename, 'w', newline='') as f:
        fieldnames = ['stop_loss', 'take_profit', 'rsi_low_limit', 'rsi_high_limit', 'number_trade', 'positive_trade', 'negative_trade', 'benefits']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            writer.writerow(row)
