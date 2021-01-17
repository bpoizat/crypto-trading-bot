import logging

from decision import Decision
from exchange_api import get_last_price

# Decide if we enter a trade or not
def enter_trade(indicators, p_strategy):
    # Long timeframe: long timeframe, slope of MACDH
    macdh = indicators['macdhist']
    macdh_slope = [macdh[x] - macdh[x-1] for x in range(1, len(macdh))]

    # Short timeframe: oscillator, RSI
    rsi = indicators['rsi']

    # possible tweaks: take slope on more points
    if macdh_slope[-1] > 0 and rsi[-1] < p_strategy['rsi_low_limit']:
        logging.info('%f > 0 and %f < %f => BUYING', macdh_slope[-1], rsi[-1], p_strategy['rsi_low_limit'])
        # positive trend and oversold, go long
        return Decision.BUY
    elif macdh_slope[-1] < 0 and rsi[-1] > p_strategy['rsi_high_limit']:
        logging.info('%f < 0 and %f > %f => SELLING', macdh_slope[-1], rsi[-1], p_strategy['rsi_high_limit'])
        # negative trend and overbought, go short
        return Decision.SELL
    else:
        return Decision.NONE


# Check if we hit the stop loss or take profit price
def check_sloss_tprofit(symbol, state, indicators, p_strategy):
    decision = Decision.NONE

    # getting the last price
    try:
        last_price = get_last_price(symbol)
    except Exception:
        raise

    # if we hit the stop loss
    if last_price < state['stop_loss']:
        decision = Decision.SELL
        logging.info('Hitting stop_loss, selling...')

    # if we hit the take profit, we might continue
    elif last_price > state['take_profit']:
        # if we would buy again, don't sell and raise take_profit/stop_loss
        if enter_trade(indicators, p_strategy) is Decision.BUY:
            decision = Decision.BUY
        else:
            decision = Decision.SELL
            logging.info('Hitting take_profit, trend not as good, leaving the trade')
    return decision


# Decide if we want to exit the trade
def exit_trade(symbol, state, indicators, p_strategy):
    try:
        decision = check_sloss_tprofit(symbol, state, indicators, p_strategy)
    except Exception:
        raise

    # Long timeframe: long timeframe, slope of MACDH
    macdh = indicators['macdhist']
    macdh_slope = [macdh[x] - macdh[x-1] for x in range(1, len(macdh))]

    # Short timeframe: oscillator, RSI
    rsi = indicators['rsi']

    if decision is Decision.NONE:
        # We didn't hit take_profit or stop_loss
        if rsi[-1] > p_strategy['rsi_high_limit']:
            # overbought, sell
            logging.info('%f > %f => SELLING what we have', rsi[-1], p_strategy['rsi_high_limit'])
            return Decision.SELL
        if macdh_slope[-1] < 0:
            # negative trend, sell
            logging.info('%f < 0 => SELLING what we have', macdh_slope[-1])
            return Decision.SELL
    
    return decision