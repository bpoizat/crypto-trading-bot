# coding=utf-8

import configparser
import logging
import telegram
import json
import time
# from linetimer import CodeTimer # to profile and optimize, example:
# with CodeTimer('getting data'):
#       data = get_data(config_binance, param_data)
from binance.client import Client

from binance_data import get_data, get_last_trade
from indicators import calculate_indicators
from strategy import *

isRunning = False

def read_state():
    state = {}
    with open('bot_state.json', 'r') as json_file:
        data = json.load(json_file)
        return data

def write_state(state):
    with open('bot_state.json', 'w') as json_file:
        data = json.dump(state, json_file)
        return data

if __name__ == "__main__":

    # Logging
    logging.basicConfig(filename='bot.log', encoding='utf-8', format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    logging.info('Starting bot')

    # Read config file
    config = configparser.ConfigParser()
    config.read('bot.ini')
    param_data = config['Data']
    param_indicators = config['Indicators']
    param_strategy = config['Strategy']
    logging.debug('Reading config file, sections found: %s', config.sections())

    # Telegram bot
    telegram_chat_id = config['Telegram']['chat_id']
    telegram_token = config['Telegram']['token_id']
    bot = telegram.Bot(token=telegram_token)

    # reading saved state
    state = read_state()
    logging.info('Bot starting with state: %r %f %f %f', state['buy_status'], state['quantity'], state['stop_loss'], state['take_profit'])

    client = Client(config['Binance']['api_key'], config['Binance']['api_secret'])
    money = config['Strategy']['money']
    isRunning = False

    bot.sendMessage(chat_id=telegram_chat_id, text='test')    

    while isRunning:
        # Get data from binance
        data = get_data(client, param_data)

        # Calculate indicators
        indicators = calculate_indicators(data, param_indicators)

        # Analyse indicators following strategy
        decision = strategy1(indicators, param_strategy, state['buy_status'])

        if not state['buy_status'] and decision == 'buy':
            last_trade = get_last_trade(client, param_data)
            last_price = last_trade[-1]['price']
            state['quantity'] = round(money/last_price, 2)
            logging.info('Ordering %f of %s at %f', state['quantity'], param_data['symbol'], last_price)

            # place order
            # order = client.order_market_buy(symbol=param_data['symbol'], quantity=state['quantity'])
            print(order)
            status = order['status']
            while status != 'FILLED':
                logger.debug('Order %s not filled, waiting...', order['clientOrderId'])
                time.sleep(1)
            else:
                entry_price = float(order['price'])
                state['quantity'] = float(order['executedQty'])
                logger.info('%f purchased at %f - order n:%s', state['quantity'], entry_price, order['clientOrderId'])
                message = 'Buying ' + str(state['quantity']) + ' ' + param_data['symbol'] + ' at ' + entry_price
                bot.sendMessage(chat_id=telegram_chat_id, text=message)

                state['stop_loss'] = entry_price - (entry_price*param_strategy['stop_loss'])
                state['take_profit'] = entry_price + (entry_price*param_strategy['take_profit'])
                logger.debug('Stop loss set at %f, taking profit at %f', state['stop_loss'], state['take_profit'])

                state['buy_status'] = True

                write_state(state)

        elif state['buy_status']:
            last_trade = get_last_trade(client, param_data)
            if state['stop_loss'] > float(last_trade[-1]['price']) or state['take_profit'] < float(last_trade[-1]['price']):
                decision = 'sell'

            if decision == 'sell':
                logging.info('Selling %f of %s at %f', state['quantity'], param_data['symbol'], last_trade[-1]['price'])
                # place order
                # order = client.order_market_sell(symbol=param_data['symbol'], quantity=state['quantity'])
                print(order)
                status = order['status']
                while status != 'FILLED':
                    logger.debug('Order %s not filled, waiting...', order['clientOrderId'])
                    time.sleep(1)
                else:
                    exit_price = float(order['price'])
                    quantity_sold = float(order['executedQty'])
                    state['quantity'] = 0.0   #?
                    state['take_profit'] = 0.0
                    state['stop_loss'] = 0.0
                    message = 'Sold ' + str(quantity_sold) + ' ' + param_data['symbol'] + ' at ' + exit_price
                    logger.info('%f sold at %f - order n:%s', quantity_sold, exit_price, order['clientOrderId'])

                    bot.sendMessage(chat_id=telegram_chat_id, text=message)

                    state['buy_status'] = False

                    write_state(state)

        elif decision == 'sell':
            print('todo')

    time.sleep(10)


