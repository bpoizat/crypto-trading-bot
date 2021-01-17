from talib import abstract
import numpy as np

def calculate_indicators(data, param_indicators):
    long_inputs = {
        'open': np.array(data['long_tf']['Open'], dtype=float),
        'high': np.array(data['long_tf']['High'], dtype=float),
        'low': np.array(data['long_tf']['Low'], dtype=float),
        'close': np.array(data['long_tf']['Close'], dtype=float),
        'volume': np.array(data['long_tf']['Volume'], dtype=float)
    }

    short_inputs = {
        'open': np.array(data['short_tf']['Open'], dtype=float),
        'high': np.array(data['short_tf']['High'], dtype=float),
        'low': np.array(data['short_tf']['Low'], dtype=float),
        'close': np.array(data['short_tf']['Close'], dtype=float),
        'volume': np.array(data['short_tf']['Volume'], dtype=float)
    }

    # Calculate indicators
    # First screen: long timeframe trend, here it's the slope of the macdh
    # matype=1 is for exponential
    macd, macdsignal, macdhist = abstract.MACDEXT(long_inputs, 
                                                  fastperiod=param_indicators['macd_fast'], fastmatype=1,
                                                  slowperiod=param_indicators['macd_slow'], slowmatype=1,
                                                  signalperiod=param_indicators['macd_signal'], signalmatype=1)

    # Second screen: intermediate timeframe, oscillator
    rsi = abstract.RSI(short_inputs, timeperiod=param_indicators['rsi_period'])

    indicators = {
        'macdhist': macdhist,
        'rsi': rsi,
    }

    return indicators