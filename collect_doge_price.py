import robin_stocks as rs
import sys
import logging
import time
from datetime import datetime
import pickle
import pdb

import utils


# login
rs.robinhood.login(username=utils.rh_username, 
	password=utils.rh_password, 
	expiresIn=utils.all_day, 
	by_sms=True)

# rs.robinhood.authentication.logout()

# logging
logfile_name = 'logs/collect_doge_price_logs/' + time.strftime("%Y%m%d-%H%M%S") + ".txt" 
logging.basicConfig(
	level=logging.INFO, 
	handlers=[logging.FileHandler(logfile_name),logging.StreamHandler()],
    format='%(message)s')


# print doge price to text file
while True:
	price = float(rs.robinhood.crypto.get_crypto_quote(symbol=utils.doge_ticker_symbol, info='ask_price'))
	logging.info(str(price) + "|" + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
	time.sleep(0.1)
