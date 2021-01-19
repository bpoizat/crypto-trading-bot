from telegram.ext import Updater, CommandHandler
import dbus

from bot_io.config import read_config

def start(update, context):
    system_bus = dbus.SystemBus()
    systemd = system_bus.get_object(
        'org.freedesktop.systemd1',
        '/org/freedesktop/systemd1'
    )

    manager = dbus.Interface(
        systemd,
        'org.freedesktop.systemd1.Manager'
    )

    manager.StartService('crypto-bot.service', 'replace')

def stop(update, context):
    system_bus = dbus.SystemBus()
    systemd = system_bus.get_object(
        'org.freedesktop.systemd1',
        '/org/freedesktop/systemd1'
    )

    manager = dbus.Interface(
        systemd,
        'org.freedesktop.systemd1.Manager'
    )

    manager.StopService('crypto-bot.service', 'replace')


if __name__ == '__main__':
    config = read_config()

    # Initializing telegrame bot
    updater = Updater(config['Telegram']['token_id'])
    dp = updater.dispatcher()

    # Commands
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('stop', stop))

    # Run bot and wait
    updater.start_polling()
    updater.idle()