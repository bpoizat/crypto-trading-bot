
def strategy1(indicators, param_strategy, buy_order_placed):
    # Triple screen

    # First screen: long timeframe, slope of MACDH
    macdh = indicators['macdhist']
    macdh_slope = [macdh[x] - macdh[x-1] for x in range(1, len(macdh))]

    # Second screen: oscillator, RSI
    rsi = indicators['rsi']

    if buy_order_placed == False:
        # possible tweaks: take slope on more points
        if macdh_slope[-1] > 0 and rsi[-1] < int(param_strategy['rsi_low_limit']):
            # positive trend and oversold, go long
            return 'buy'
        elif macdh_slope[-1] < 0 and rsi[-1] > int(param_strategy['rsi_high_limit']):
            # negative trend and overbought, go short
            return 'sell'
        else:
            return 'none'
    elif buy_order_placed == True:
        # we have some coins waiting to be sold
        if rsi[-1] > int(param_strategy['rsi_high_limit']):
            # overbought, sell
            return 'sell'
