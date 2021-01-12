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
from binance.exceptions import BinanceRequestException, BinanceAPIException, BinanceOrderException

from binance_data import get_data, get_last_trade
from indicators import calculate_indicators
from strategy import *

def read_state():
    state = {}
    with open('bot_state.json', 'r') as json_file:
        data = json.load(json_file)
        return data

def write_state(state):
    with open('bot_state.json', 'w') as json_file:
        data = json.dump(state, json_file)
        return data

def fake_order(price, qty):
    return {
        'status': 'FILLED',
        'orderId': 15,
        'price': str(price),
        'executedQty': qty
    }

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
    logging.info('Bot started with state: %r %f %f %f', state['buy_status'], state['quantity'], state['stop_loss'], state['take_profit'])

    client = Client(config['Binance']['api_key'], config['Binance']['api_secret'])
    money = float(config['Strategy']['money'])
    isRunning = True

    print('Bot started correctly!')

    while isRunning:
        # Get data from binance
        try:
            data = get_data(client, param_data)
        except (BinanceRequestException, BinanceAPIException) as err:
            logging.error('Error when retrieving data: %s', err)
            time.sleep(5)
            continue

        # Calculate indicators
        indicators = calculate_indicators(data, param_indicators)

        # Analyse indicators following strategy
        decision = strategy1(indicators, param_strategy, state['buy_status'])

        # No trade going on, we decide to enter long
        if not state['buy_status'] and decision == 'buy':
            # getting the last price
            try:
                last_trade = get_last_trade(client, param_data)
            except (BinanceRequestException, BinanceAPIException) as err:
                logging.error('Error when retrieving data: %s', err)
                time.sleep(5)
                continue
            last_price = float(last_trade[-1]['price'])

            # calculating quantity of coins to buy
            quantityToOrder = round(money/last_price, 2)
            logging.info('Ordering %f of %s at %f', quantityToOrder, param_data['symbol'], last_price)

            # place order
            try:
                # order = client.order_market_buy(symbol=param_data['symbol'], quantity=quantityToOrder)
                pass
            except (BinanceRequestException, BinanceAPIException, BinanceOrderException) as err:
                logging.error('Error when placing order: %s', err)
                time.sleep(5)
                continue
            print(order)

            # Checking if order is filled
            while order['status'] != 'FILLED':   # Timeout?
                logging.info('Order %d not filled: %s, waiting...', order['orderId'], order['status'])
                try:
                    order = client.get_order(symbol=param_data['symbol'], orderId=order['orderId'])
                except (BinanceRequestException, BinanceAPIException) as err:
                    logging.error('Error when checking order: %s', err)
                time.sleep(1)

            entry_price = float(order['price'])
            state['quantity'] = float(order['executedQty'])
            logging.info('%f purchased at %f - order n:%d', state['quantity'], entry_price, order['orderId'])

            state['stop_loss'] = entry_price - (entry_price*float(param_strategy['stop_loss']))
            state['take_profit'] = entry_price + (entry_price*float(param_strategy['take_profit']))
            logging.debug('Stop loss set at %f, take profit at %f', state['stop_loss'], state['take_profit'])

            message = 'Buying ' + str(state['quantity']) + ' ' + param_data['symbol'] + ' at ' + str(entry_price)
            try:
                bot.sendMessage(chat_id=telegram_chat_id, text=message)
            except telegram.error.TelegramError as err:
                logging.error('Error when sending telegram message: %s', err)

            state['buy_status'] = True
            write_state(state)

        # Trade going on, we are long
        elif state['buy_status']:
            # getting the last price
            try:
                last_trade = get_last_trade(client, param_data)
            except (BinanceRequestException, BinanceAPIException) as err:
                logging.error('Error when retrieving data: %s', err)
                time.sleep(5)
                continue
            last_price = float(last_trade[-1]['price'])
            
            # if we hit the stop loss or the take profit
            if state['stop_loss'] > last_price or state['take_profit'] < last_price:
                decision = 'sell'

            if decision == 'sell':
                logging.info('Selling %f of %s at %f', state['quantity'], param_data['symbol'], last_price)
                # place order
                try:
                    # order = client.order_market_sell(symbol=param_data['symbol'], quantity=state['quantity'])
                except (BinanceRequestException, BinanceAPIException, BinanceOrderException) as err:
                    logging.error('Error when placing order: %s', err)
                    time.sleep(5)
                    continue
                print(order)

                # Checking if order is filled
                while order['status'] != 'FILLED':
                    logging.info('Order %d not filled: %s, waiting...', order['orderId'], order['status'])
                    try:
                        order = client.get_order(symbol=param_data['symbol'], orderId=order['orderId'])
                    except (BinanceRequestException, BinanceAPIException) as err:
                        logging.error('Error when checking order: %s', err)
                    time.sleep(1)

                exit_price = float(order['price'])
                quantity_sold = float(order['executedQty'])
                state['quantity'] = 0.0   #?
                state['take_profit'] = 0.0
                state['stop_loss'] = 0.0
                logging.info('%f sold at %f - order n:%d', quantity_sold, exit_price, order['orderId'])

                message = 'Sold ' + str(quantity_sold) + ' ' + param_data['symbol'] + ' at ' + str(exit_price)
                try:
                    bot.sendMessage(chat_id=telegram_chat_id, text=message)
                except telegram.error.TelegramError as err:
                    logging.error('Error when sending telegram message: %s', err)

                state['buy_status'] = False
                write_state(state)

        elif decision == 'sell':
            print('todo')

        time.sleep(10)


