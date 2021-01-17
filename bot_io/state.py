# The state of the bot is saved in a JSON file
# As of now, it looks like this:
# {
#     "buy_status": false, 
#     "quantity": 0.0, 
#     "take_profit": 0.0, 
#     "stop_loss": 0.0, 
#     "trade": {
#         "entry_price": 1165.33, 
#         "quantity": 0.09, 
#         "money_spent": 104.87969999999999, 
#         "exit_price": 1100.0, 
#         "money_earned": 99.0, 
#         "bilan": -5.8796999999999855
#     }
# }
# We save the last trade in case to remember it if the bot crashes
# before it has been written to trade_record

import json

state_file = 'bot_state.json'

# Read state of the bot
def read_state():
    state = {}
    with open(state_file, 'r') as json_file:
        data = json.load(json_file)
        return data

# Write state of the bot
def write_state(state):
    with open(state_file, 'w') as json_file:
        data = json.dump(state, json_file)
        return data