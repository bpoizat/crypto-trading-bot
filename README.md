# crypto-trading-bot

# Installation
Dependencies are python 3 (tested with version 3.7).
PIP packages to install: python-telegram-bot, python-binance, TA-Lib (requires the package ta-lib, which itself requires libatlas-base-dev).
Add your binance tokens to config.ini, as well as the telegram tokens.
Enter parameters of your strategy in param.ini.

# Running the bot manually
```sh
$ python bot.py
```

# Using Systemd
You can use systemd to start automatically the bot.
Copy the file crypto-bot.service to the folder /etc/systemd/system/ as root.
Enable it and run it:
```sh
$ sudo systemctl enable crypto-bot.service
$ sudo systemctl start crypto-bot.service
```

You can stop it with:
```sh
$ sudo systemctl stop crypto-bot.service
```

Check status and journal of the service:
```sh
$ systemctl status crypto-bot.service
$ journalctl -r --unit=crypto-bot.service
```

# Output
Trade are recorded as a csv in trade_record.csv

# Backtesting