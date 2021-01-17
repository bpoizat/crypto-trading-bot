# General purpose functions used by the bot

import logging

from exchange_api import *
from bot_io.config import read_config
from bot_io.state import write_state
from bot_io.trade_recording import save_trade
import bot_io.telegram_bot as telegram_bot
from test_helper import fake_order

# Initialize the API, logging, general IO
def init_bot():
    # Read config file
    config = read_config()

    # Initialize logging
    logging.basicConfig(filename=config['Logging']['file'], format='%(asctime)s %(levelname)s: %(message)s', level=config['Logging']['level'])
    logging.info('Starting bot')

    # Initialize the telegram bot
    telegram_bot.init_bot(config['Telegram']['token_id'], config['Telegram']['chat_id'])

    # Initialize binance api
    init_client(config['Binance']['api_key'], config['Binance']['api_secret'])


# Buy symbol for money amount
# Wait for the order to be filled
def buy(symbol, money):
    # getting the last price
    try:
        last_price = get_last_price(symbol)
    except Exception:
        raise

    # calculating quantity of coins to buy
    quantityToOrder = round(money/last_price, 5)
    logging.info('Ordering %f of %s at %f', quantityToOrder, symbol, last_price)

    # place order
    try:
        order = place_marker_order(Decision.BUY, symbol, quantityToOrder)
    except Exception:
        raise

    logging.debug(order)

    # Wait until the order is filled
    wait_order_filled(order, symbol)

    return order

# Sell symbol for money amount
# Wait for the order to be filled
def sell(symbol, quantity):
    logging.info('Exiting the trade')
    # place order
    try:
        order = place_marker_order(Decision.SELL, symbol, quantity)
        pass
    except Exception:
        raise
    logging.debug(order)

    # Wait until the order is filled
    wait_order_filled(order, symbol)

    return order

# Entering a long trade
def enter_trade_buy(symbol, money, p_stop_loss, p_take_profit):
    try:
        # Buying
        order = buy(symbol, money)
    except Exception:
        raise

    # Parsing order
    money_spent = float(order['cummulativeQuoteQty'])
    quantity = float(order['executedQty'])
    entry_price = money_spent/quantity

    # Updating state
    state = {
        'buy_status': True,
        'quantity': quantity,
        'stop_loss': entry_price*(1-p_stop_loss),
        'take_profit': entry_price*(1+p_take_profit),
        'trade': {
            'entry_price': entry_price,
            'quantity': quantity,
            'money_spent': money_spent,
        }
    }
    write_state(state)

    # Sending telegram message
    message = 'Buying ' + str(quantity) + ' ' + symbol + ' at ' + str(entry_price)
    telegram_bot.send_message(message)

    logging.info('%f purchased at %f - order n:%d', quantity, entry_price, order['orderId'])
    logging.info('Stop loss set at %f, take profit at %f', state['stop_loss'], state['take_profit'])
    
    return state

# Exiting from a long trade
def exit_long_trade(symbol, state):
    try:
        # Selling
        order = sell(symbol, state['quantity'])
    except Exception:
        raise

    # Parsing order
    money_earned = float(order['cummulativeQuoteQty'])
    quantity_sold = float(order['executedQty'])
    exit_price = money_earned/quantity_sold
    if quantity_sold != state['quantity']:
        logger.warning('Quantity sold different than quantity bought, UNEXPECTED')

    # recording trade
    trade = state['trade']
    trade['exit_price'] = exit_price
    trade['money_earned'] = money_earned
    trade['bilan'] = trade['money_earned'] - trade['money_spent']
    save_trade(trade)

    # Updating state
    state['quantity'] = state['quantity'] - quantity_sold   # SHOULD BE 0
    state['take_profit'] = 0.0
    state['stop_loss'] = 0.0
    state['buy_status'] = False
    write_state(state)

    # Sending telegram message
    message = 'Sold ' + str(quantity_sold) + ' ' + symbol + ' at ' + str(exit_price) + '\nBilan = ' + str(trade['bilan'])
    telegram_bot.send_message(message)

    logging.info('%f sold at %f - order n:%d', quantity_sold, exit_price, order['orderId'])
    return state