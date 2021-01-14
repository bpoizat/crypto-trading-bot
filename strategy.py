import logging

def strategy1(indicators, param_strategy, buy_order_placed):
    # Triple screen

    # First screen: long timeframe, slope of MACDH
    macdh = indicators['macdhist']
    macdh_slope = [macdh[x] - macdh[x-1] for x in range(1, len(macdh))]

    # Second screen: oscillator, RSI
    rsi = indicators['rsi']

    if buy_order_placed == False:
        # possible tweaks: take slope on more points
        if macdh_slope[-1] > 0 and rsi[-1] < float(param_strategy['rsi_low_limit']):
            logging.info('%f > 0 and %f < %f => BUYING', macdh_slope[-1], rsi[-1], float(param_strategy['rsi_low_limit']))
            # positive trend and oversold, go long
            return 'buy'
        elif macdh_slope[-1] < 0 and rsi[-1] > float(param_strategy['rsi_high_limit']):
            logging.debug('%f < 0 and %f > %f => SELLING', macdh_slope[-1], rsi[-1], float(param_strategy['rsi_high_limit']))
            # negative trend and overbought, go short
            return 'sell'
        else:
            logging.debug('macdh_slope[-1]: %f and rsi[-1]:%f => NOTHING', macdh_slope[-1], rsi[-1])
            return 'none'
    elif buy_order_placed == True:
        # we have some coins waiting to be sold
        if rsi[-1] > int(param_strategy['rsi_high_limit']):
            # overbought, sell
            logging.info('%f > %f => SELLING what we have', rsi[-1], float(param_strategy['rsi_high_limit']))
            return 'sell'
        if macdh_slope[-1] < 0:
            # negative trend, sell
            logging.info('%f < 0 => SELLING what we have', macdh_slope[-1])
            return 'sell'
