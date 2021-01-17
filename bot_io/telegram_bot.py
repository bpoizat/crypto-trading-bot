# Telegram bot, sends messages when passing an order

import telegram

# Initialize the bot and save the chat id, used when sending messages
def init_bot(telegram_token, telegram_chat_id):
    global bot
    global chat_id
    bot = telegram.Bot(token=telegram_token)
    chat_id = telegram_chat_id

# Send a message
def send_message(message):
    try:
        bot.sendMessage(chat_id=chat_id, text=message)
    except telegram.error.TelegramError as err:
        logging.error('Error when sending telegram message: %s', err)