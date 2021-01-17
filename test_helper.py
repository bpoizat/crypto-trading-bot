
# Return a fake order when given the price and quantity
def fake_order(price, qty):
    return {
        'status': 'FILLED',
        'orderId': 15,
        'price': str(price),
        'executedQty': qty,
        'cummulativeQuoteQty': price*qty
    }