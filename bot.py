# coding=utf-8

import configparser
import logging
import telegram
import json
import time
import csv
# from linetimer import CodeTimer # to profile and optimize, example:
# with CodeTimer('getting data'):
#       data = get_data(config_binance, param_data)
from binance.client import Client
from binance.exceptions import BinanceRequestException, BinanceAPIException, BinanceOrderException
from requests.exceptions import ReadTimeout

from binance_data import get_data, get_last_trade
from indicators import calculate_indicators
from strategy import *
from decision import Decision

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
        'executedQty': qty,
        'cummulativeQuoteQty': price*qty
    }

def save_trade(trade):
    filename = 'trade_record.csv'
    fieldnames = ['quantity', 'entry_price', 'exit_price', 'money_spent', 'money_earned', 'bilan']

    try:
        with open(filename, 'x', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(trade)
    except FileExistsError:
        # File already exists
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(trade)

if __name__ == "__main__":

    # Logging
    logging.basicConfig(filename='bot.log', format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
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

    # read saved state
    state = read_state()
    logging.info('Bot started with state: %r %f %f %f', state['buy_status'], state['quantity'], state['stop_loss'], state['take_profit'])

    # Trade record
    if state['buy_status']:
        trade = state['trade']

    client = Client(config['Binance']['api_key'], config['Binance']['api_secret'])
    money = float(config['Strategy']['money'])
    bilan = 0
    isRunning = True

    print('Bot started correctly!')

    while isRunning:
        # Get data from binance
        try:
            data = get_data(client, param_data)
        except (BinanceRequestException, BinanceAPIException, ReadTimeout) as err:
            logging.error('Error when retrieving data: %s', err)
            time.sleep(5)
            continue

        # Calculate indicators
        indicators = calculate_indicators(data, param_indicators)

        # Analyse indicators following strategy
        decision = strategy1(indicators, param_strategy, state['buy_status'])

        # No trade going on, we decide to enter long
        if not state['buy_status'] and decision is Decision.BUY:
            # getting the last price
            try:
                last_trade = get_last_trade(client, param_data)
            except (BinanceRequestException, BinanceAPIException, ReadTimeout) as err:
                logging.error('Error when retrieving data: %s', err)
                time.sleep(5)
                continue
            last_price = float(last_trade[-1]['price'])

            # calculating quantity of coins to buy
            quantityToOrder = round(money/last_price, 5)
            logging.info('Ordering %f of %s at %f', quantityToOrder, param_data['symbol'], last_price)

            # place order
            try:
                order = client.order_market_buy(symbol=param_data['symbol'], quantity=quantityToOrder)
                pass
            except (BinanceRequestException, BinanceAPIException, BinanceOrderException) as err:
                logging.error('Error when placing order: %s', err)
                time.sleep(5)
                continue
            logging.debug(order)

            # Checking if order is filled
            while order['status'] != 'FILLED':   # Timeout?
                logging.info('Order %d not filled: %s, waiting...', order['orderId'], order['status'])
                try:
                    order = client.get_order(symbol=param_data['symbol'], orderId=order['orderId'])
                except (BinanceRequestException, BinanceAPIException, ReadTimeout) as err:
                    logging.error('Error when checking order: %s', err)
                time.sleep(1)

            entry_price = float(order['cummulativeQuoteQty'])/float(order['executedQty'])
            state['quantity'] = float(order['executedQty'])
            state['stop_loss'] = entry_price - (entry_price*float(param_strategy['stop_loss']))
            state['take_profit'] = entry_price + (entry_price*float(param_strategy['take_profit']))
            logging.info('%f purchased at %f - order n:%d', state['quantity'], entry_price, order['orderId'])
            logging.info('Stop loss set at %f, take profit at %f', state['stop_loss'], state['take_profit'])

            # recording trade
            trade = {
                'entry_price': entry_price,
                'quantity': state['quantity'],
                'money_spent': entry_price*state['quantity'],
            }
            state['trade'] = trade

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
            except (BinanceRequestException, BinanceAPIException, ReadTimeout) as err:
                logging.error('Error when retrieving data: %s', err)
                time.sleep(5)
                continue
            last_price = float(last_trade[-1]['price'])
            
            # if we hit the stop loss or the take profit
            if last_price < state['stop_loss']:
                decision = Decision.SELL
                logging.info('Hitting stop_loss, selling...')
            
            # if we hit the take profit, we might continue
            elif last_price > state['take_profit']:
                # if we would buy again, don't sell and raise take_profit/stop_loss
                if strategy1(indicators, param_strategy, False) is Decision.BUY:
                    # take_profit increases by half the percentage
                    state['stop_loss'] = state['take_profit']
                    state['take_profit'] = state['take_profit']*(1+float(param_strategy['take_profit'])/2)
                    logging.info('Hitting take_profit, increasing take_profit to %f and stop_loss to %f...', state['take_profit'], state['stop_loss'])
                else:
                    decision = Decision.SELL
                    logging.info('Hitting take_profit, trend not as good, leaving the trade')

            if decision is Decision.SELL:
                logging.info('Selling %f of %s at %f', state['quantity'], param_data['symbol'], last_price)
                # place order
                try:
                    order = client.order_market_sell(symbol=param_data['symbol'], quantity=state['quantity'])
                    pass
                except (BinanceRequestException, BinanceAPIException, BinanceOrderException, ReadTimeout) as err:
                    logging.error('Error when placing order: %s', err)
                    time.sleep(5)
                    continue
                logging.debug(order)

                # Checking if order is filled
                while order['status'] != 'FILLED':
                    logging.info('Order %d not filled: %s, waiting...', order['orderId'], order['status'])
                    try:
                        order = client.get_order(symbol=param_data['symbol'], orderId=order['orderId'])
                    except (BinanceRequestException, BinanceAPIException, ReadTimeout) as err:
                        logging.error('Error when checking order: %s', err)
                    time.sleep(1)

                exit_price = float(order['cummulativeQuoteQty'])/float(order['executedQty'])
                quantity_sold = float(order['executedQty'])
                if quantity_sold != state['quantity']:
                    logger.warning('Quantity sold different than quantity bought, UNEXPECTED')
                state['quantity'] = 0.0   #?
                state['take_profit'] = 0.0
                state['stop_loss'] = 0.0
                logging.info('%f sold at %f - order n:%d', quantity_sold, exit_price, order['orderId'])

                # recording trade
                trade['exit_price'] = exit_price
                trade['money_earned'] = exit_price*quantity_sold
                trade['bilan'] = trade['money_earned'] - trade['money_spent']
                save_trade(trade)

                message = 'Sold ' + str(quantity_sold) + ' ' + param_data['symbol'] + ' at ' + str(exit_price) + '\nBilan = ' + str(trade['bilan'])
                try:
                    bot.sendMessage(chat_id=telegram_chat_id, text=message)
                except telegram.error.TelegramError as err:
                    logging.error('Error when sending telegram message: %s', err)

                state['buy_status'] = False
                write_state(state)

                # Money won or lost since start of the bot
                bilan += trade['bilan']
                print(bilan)
                if bilan < float(param_strategy['switchoff'])*money*-1:
                    logging.info('Lost %d, stopping the bot', bilan)
                    isRunning = False

        elif decision is Decision.SELL:
            print('todo')

        time.sleep(10)


