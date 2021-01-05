# coding=utf-8

import configparser
# from linetimer import CodeTimer # to profile and optimize, example:
# with CodeTimer('getting data'):
#       data = get_data(config_binance, param_data)

from binance_data import get_data
from indicators import calculate_indicators
from strategy import *

if __name__ == "__main__":

    # Read config file
    config = configparser.ConfigParser()
    config.read('bot.ini')

    config_binance = config['Binance']
    param_data = config['Data']
    param_indicators = config['Indicators']
    param_strategy = config['Strategy']

    # Get data from binance
    data = get_data(config_binance, param_data)

    # Calculate indicators
    indicators = calculate_indicators(data, param_indicators)

    # Analyse indicators following strategy
    decision = strategy1(indicators, param_strategy)

    # setup trade (entry point, stop, target, quantity)
    # format prices
    if decision == 'buy':
        entry_price = #data['short_tf'][Close][-1]   # or market price?
        stop_loss = entry_price - (entry_price*param_strategy['stop_loss'])
        take_profit = entry_price + (entry_price*param_strategy['take_profit'])
        #quantity = 
        # fake one for backtesting
        # then real with client.place_order
    elif decision == 'sell':
        print('todo')
    # Display - optional
