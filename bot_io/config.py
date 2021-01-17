# Read the bot.ini file that contains the configuration and parameters

import configparser
import logging

# read the configuration file
def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')

    return config

# read the parameters file
def read_param():
    param = configparser.ConfigParser()
    param.read('param.ini')

    p_data = param['Data']

    symbol = p_data['symbol']
    timeframes = {
        'l_interval': p_data['long_interval'],
        'l_start': p_data['long_start'],
        's_interval': p_data['short_interval'],
        's_start': p_data['short_start'],
    }

    p_indicators = {
        'macd_fast': int(param['Indicators']['macd_fast']),
        'macd_slow': int(param['Indicators']['macd_slow']),
        'macd_signal': int(param['Indicators']['macd_signal']),
        'rsi_period': int(param['Indicators']['rsi_period']),
    }

    p_strategy = {
        'rsi_low_limit': float(param['Strategy']['rsi_low_limit']),
        'rsi_high_limit': float(param['Strategy']['rsi_high_limit']),
    }

    stop_loss = float(param['Strategy']['stop_loss'])
    take_profit = float(param['Strategy']['take_profit'])
    money = float(param['Strategy']['money'])
    switchoff = float(param['Strategy']['switchoff'])

    logging.debug('Reading parameters, working with %s', symbol)
    logging.debug('Timeframes are %s since %s and %s since %s', timeframes['l_interval'], timeframes['l_start'], timeframes['s_interval'], timeframes['s_start'])
    logging.debug('Indicators are %s', p_indicators)
    logging.debug('Strategy used: %s', p_strategy)
    logging.debug('Stop_loss=%f, take_profit=%f, money=%f, switchoff=%f', stop_loss, take_profit, money, switchoff)

    return symbol, timeframes, p_indicators, p_strategy, stop_loss, take_profit, money, switchoff
