# Save all trades in a csv file

import csv

# save a trade in the csv file
# if the file doesn't exist, it's created
def save_trade(trade):
    filename = 'output/trade_record.csv'
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