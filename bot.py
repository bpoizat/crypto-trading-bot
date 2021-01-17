# coding=utf-8

import logging
import time

from indicators import calculate_indicators
import strategy
from decision import Decision

from bot_io.config import read_param
from bot_io.state import read_state
import bot_io.telegram_bot as telegram_bot

from bot_lib import *

if __name__ == "__main__":

    init_bot()

    # reading all parameters
    symbol, tf, p_indicators, p_strategy, p_stop_loss, p_take_profit, money, switchoff = read_param()

    # read saved state
    state = read_state()
    logging.info('Bot started with state: %s', state)

    # If a trade is going on, we want to have it to save it
    if state['buy_status']:
        trade = state['trade']

    # bilan is used to keep track of what happened during this execution of the bot
    bilan = 0
    isRunning = True

    telegram_bot.send_message('Bot started correctly!')

    while isRunning:
        # Get data from binance
        try:
            data = get_data(symbol, tf)
        except Exception as err:
            logging.error('Error when retrieving data: %s', err)
            time.sleep(5)
            continue

        # Calculate indicators
        indicators = calculate_indicators(data, p_indicators)

        # No trade going on
        if not state['buy_status']:
            # Analyse indicators following strategy
            decision = strategy.enter_trade(indicators, p_strategy)

            # Go long
            if decision is Decision.BUY:
                try:
                    state = enter_trade_buy(symbol, money, p_stop_loss, p_take_profit)
                except Exception as err:
                    logging.error('Error when entering trade: %s', err)
                    time.sleep(5)
                    continue

            # Go short
            elif decision is Decision.SELL:
                print('todo')

        # Long trade going on, we are long
        elif state['buy_status']:
            try:
                decision = strategy.exit_trade(symbol, state, indicators, p_strategy)
            except Exception as err:
                logging.error('Error when deciding to exit trade: %s', err)
                time.sleep(5)
                continue

            # Exit the trade by shorting
            if decision is Decision.SELL:
                try:
                    state = exit_long_trade(symbol, state)
                except Exception as err:
                    logging.error('Error when exiting trade: %s', err)
                    time.sleep(5)
                    continue

                # Money won or lost since start of the bot
                bilan += trade['bilan']
                logging.info('Bilan since start of this session is: %f', bilan)
                # If we lost too much money, we stop the bot
                if bilan < switchoff*money*-1:
                    logging.info('Lost %d, stopping the bot', bilan)
                    isRunning = False
            
            # here buy means increasing stop_loss and take_profit
            elif decision is Decision.BUY:
                # take_profit increases by half the percentage
                state['stop_loss'] = state['take_profit']
                state['take_profit'] = state['take_profit']*(1+p_take_profit/2)
                logging.info('Hitting take_profit, increasing take_profit to %f and stop_loss to %f...', state['take_profit'], state['stop_loss'])

        time.sleep(10)


