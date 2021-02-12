# Read the bot.ini file that contains the configuration and parameters

import configparser
import logging

# read the configuration file
def read_config():
    config = configparser.ConfigParser()
    config.read('ini_files/config.ini')

    return config

# read the parameters file
def read_param():
    param = configparser.ConfigParser()
    param.read('ini_files/param.ini')

    p_data = param['Data']

    symbol = p_data['symbol']
    timeframes = {
        'interval': p_data['interval'],
        'start': p_data['start'],
    }

    p_indicators = {
        'fast_ema': int(param['Indicators']['fast_ema']),
        'slow_ema': int(param['Indicators']['slow_ema']),
    }

    p_strategy = {
        'stop_loss': float(param['Strategy']['stop_loss']),
        'take_profit': float(param['Strategy']['take_profit']),
        'money': float(param['Strategy']['money']),
        'switchoff': float(param['Strategy']['switchoff']),
    }

    stop_loss = float(param['Strategy']['stop_loss'])
    take_profit = float(param['Strategy']['take_profit'])
    money = float(param['Strategy']['money'])
    switchoff = float(param['Strategy']['switchoff'])

    logging.debug('Reading parameters, working with %s', symbol)
    logging.debug('Timeframes is %s', timeframes)
    logging.debug('Indicators are %s', p_indicators)
    logging.debug('Strategy used: %s', p_strategy)

    return symbol, timeframes, p_indicators, p_strategy

# read the backtest config file
def read_backtest_param():
    config = configparser.ConfigParser()
    config.read('ini_files/backtest.ini')

    return config