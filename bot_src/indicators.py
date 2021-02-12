from talib import abstract
import numpy as np

def calculate_indicators(data, param_indicators):
    inputs = {
        'open': np.array(data['tf']['Open'], dtype=float),
        'high': np.array(data['tf']['High'], dtype=float),
        'low': np.array(data['tf']['Low'], dtype=float),
        'close': np.array(data['tf']['Close'], dtype=float),
        'volume': np.array(data['tf']['Volume'], dtype=float)
    }

    fast_ema = abstract.EMA(inputs, param_indicators['fast_ema'])
    slow_ema = abstract.EMA(inputs, param_indicators['slow_ema'])

    indicators = {
        'fast_ema': fast_ema,
        'slow_ema': slow_ema,
    }

    return indicators