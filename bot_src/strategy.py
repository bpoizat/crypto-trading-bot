import logging

from bot_src.decision import Decision

# Decide if we enter a trade or not
def enter_trade(indicators, p_strategy):
    slow_ema = indicators['slow_ema']
    fast_ema = indicators['fast_ema']

    if slow_ema[-1] < fast_ema[-1]:
        # logging.info('%f > 0 and %f < %f => BUYING', macdh_slope[-1], rsi[-1], p_strategy['rsi_low_limit'])
        # positive trend, go long
        return Decision.BUY
    elif slow_ema[-1] > fast_ema[-1]:
        # logging.info('%f < 0 and %f > %f => SELLING', macdh_slope[-1], rsi[-1], p_strategy['rsi_high_limit'])
        # negative trend, go short
        return Decision.SELL
    else:
        return Decision.NONE


# Decide if we want to exit the trade
def exit_trade(indicators, p_strategy):
    slow_ema = indicators['slow_ema']
    fast_ema = indicators['fast_ema']

    if slow_ema[-1] > fast_ema[-1]:
        return Decision.SELL

    return Decision.NONE