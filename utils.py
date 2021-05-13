import robin_stocks as rs
import pickle
import numpy as np
from os import path
import os
import pdb

import logging
log = logging.getLogger(__name__)

# CONSTANTS
# run the following commands in the terminal to populate these variables (use your own username/password)
# export rh_username="your_username_here"
# export rh_password="your_password_here"
rh_username = os.environ.get("rh_username")
rh_password = os.environ.get("rh_password")
all_day = 86400
net_tracker_dir = "net_trackers/"
doge_hist_data_dir = "logs/collect_doge_price_logs/"
doge_cur_pair_id = 'c6996ebc-2f9b-443a-b2c2-7ddf02e0ef3a'
doge_ticker_symbol = 'DOGE'
activity_column_dict = {
		'datetime': str, 
		'trade_symbol': str, 
		'price': np.float64,
		'moving_average': np.float64,
		'trend': np.float64,
		'current_net': np.float64, 
		'current_quantity': np.float64, 
		'order_side': str, 
		'confirmed_price': np.float64, 
		'ref_price': np.float64,
		'order_amnt_dollars': np.float64, 
		'order_amnt_quant': np.float64}
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'

# price = rs.robinhood.crypto.get_crypto_quote(symbol='DOGE', info='ask_price')
# def get_price_time_pair(symbol):
# 	price = rs.robinhood.crypto.get_crypto_quote(symbol=symbol, info='ask_price')

def get_total_deposits(valid_statuses='', list_deposits=False):
	# get money transfers from bank and return current total deposit amount
	transfers = rs.robinhood.account.get_bank_transfers()
	amount_sum = 0
	for t in transfers:
		if list_deposits:
			if(t['state'] in valid_statuses or valid_statuses == ''):
				ldate = t['expected_landing_datetime']
				print("==============================================")
				print("Amount: " + t['amount'])
				print("Amount Pending: " + str((float(t['amount']) - float(t['early_access_amount']))))
				print("Direction: " + t['direction'])
				print("Landing Date: " + ldate[0:ldate.index('T')])
				print("Status: " + t['state'])
				print("==============================================\n")
		if t['direction'] == 'deposit' and t['state'] != 'cancelled':
			amount_sum += float(t['amount'])
	print("Total Deposits: " + str(amount_sum))
	return amount_sum

def get_total_invested(verbose=False):
	tot_deposits = get_total_deposits()
	buying_power = float(rs.robinhood.profiles.load_account_profile()['buying_power'])
	invested = tot_deposits - buying_power
	if verbose:	
		print('Buying Power: ' + str(buying_power))
		print('Invested: ' + str(tot_deposits - buying_power))
	return invested

def get_crypto_pair_id(crypto_id):
	# takes a crypto id and returns its dollar-crypto pair id
	pairs = rs.robinhood.crypto.get_crypto_currency_pairs()
	for p in pairs:
		if p['asset_currency']['id'] == crypto_id:
			return p['id']
	print("NO VALID PAIR ID")

def get_held_crypto_value(id='', symbol='', verbose=False):
	# return the value and amount in dollars of a given held crypto
	cryptos = rs.robinhood.crypto.get_crypto_positions()
	amount = ''
	value = ''
	for c in cryptos:
		if c['currency']['id'] == id or c['currency']['code'] == symbol:
			name = c['currency']['code']
			amount = float(c['quantity'])
			value = amount * float(rs.robinhood.crypto.get_crypto_quote(symbol=name, info='ask_price'))
			if verbose:
				print("Crypto: " + name)
				print("Amount: " + str(amount))
				print("Value: " + str(value))
	return amount, value

def get_crypto_net_val(id, verbose=False):
	# takes the "currency pair id" of a crypto and returns net profit/loss
	# ... only considers orders which have gone through (AKA 'state'=='filled')
	orders = rs.robinhood.orders.get_all_crypto_orders()
	pair_id = get_crypto_pair_id(id)
	tot_buys = 0.0
	tot_sells = 0.0
	for o in orders:
		if o['currency_pair_id'] == pair_id and o['state'] == 'filled':
			if o['side'] == 'buy':
				tot_buys += float(o['rounded_executed_notional'])
			elif o['side'] == 'sell':
				tot_sells += float(o['rounded_executed_notional'])

			if verbose:
				log.info('=======================')
				log.info('Trade: ' + o['side'])
				log.info('Amount($): ' + o['rounded_executed_notional'])
				log.info('Amount(coin): ' + o['cumulative_quantity'])
				log.info('Price/coin: ' + o['price'])
				log.info('=======================\n')

	_, tot_value = get_held_crypto_value(id=id)
	net = tot_value - (tot_buys - tot_sells)
	if verbose:
		log.info("Crypto value: " + str(tot_value))
		log.info("Cumulative buys: " + str(tot_buys))
		log.info("Cumulative sells: " + str(tot_sells))
		log.info("Net (tot_value - (tot_buys - tot_sells)): " + str(net))
	return net, tot_buys, tot_sells

# this check makes sure that the user is setting their minimum net limit, so we can stop the trading program if losses start to get out of hand
# this check can be done at the beginning of each program, and returns the current net (if resuming progress for the day), and the net minimum limit
# Concretely, it takes 3 arguments:
#	1. new_net: if true, creates a new net tracker
#	2. net_name: name of new net tracker if new_net==True, else uses and old one
#	3. new_net_val: sets the net limit when new_net==True
#	*** net trackers should be pickle files with structured as: (cur_net, net_min)
def net_limit_safety_check(args):
	# get and print main arguments
	if len(args) < 2:
		log.info("!!!!!!!!!!!! MUST DECIDE WHETHER TO USE NEW NET LIMIT !!!!!!!!!!!!")
		quit()
	new_net = True if (args[1] == "True" or args[1] == "true") else False
	net_name = args[2] if len(args) > 2 else None
	new_net_val = args[3] if len(args) > 3 else None

	log.info("====== Input Parameters ======")
	log.info("New Net: " + str(new_net))
	log.info("Net Name: " + str(net_name))
	log.info("New Net Value: " + str(new_net_val))
	log.info("==============================\n")

	# create the net file if new net being used, else use the mentioned net file
	net_tracker_path = net_tracker_dir + net_name
	if new_net:
		cur_net = 0.0
		net_min = float(new_net_val)
		net_tracker_package = (cur_net, net_min)
		with open(net_tracker_path, 'wb') as f:
			pickle.dump(net_tracker_package, f)
	else:
		if path.exists(net_tracker_path):
			cur_net, net_min = pickle.load(open(net_tracker_path, "rb"))
		else:
			log.info("!!!!!!!!!!!! NET FILE GIVEN NOT VALID !!!!!!!!!!!!")
			quit()
	log.info("====== Net Settings ======")
	log.info("Current net: " + str(cur_net))
	log.info("Net min: " + str(net_min))
	log.info("==========================\n")

	return cur_net, net_min

def get_net_tracker_info(net_tracker_fname):
	net_tracker_path = net_tracker_dir + net_tracker_fname
	if path.exists(net_tracker_path):
			cur_net, net_min = pickle.load(open(net_tracker_path, "rb"))
	else:
		log.info("!!!!!!!!!!!! NET FILE GIVEN NOT VALID !!!!!!!!!!!!")
		quit()
	return cur_net, net_min

# DEPRICATED... THIS FUNCTION FOUND IN TradeInferface CLASS NOW
# def update_net_limit_tracker(fname, order_side, notional, verbose=False):
# 	# get current net and net limit
# 	cur_net, net_min = pickle.load(open(fname, "rb"))
# 	if order_side == "buy":
# 		cur_net -= notional
# 		if verbose:
# 			logging.info("Updated net tracker " + fname + " by +" + str(notional))
# 	elif order_side == "sell":
# 		cur_net += notional
# 		if verbose:
# 			logging.info("Updated net tracker " + fname + " by -" + str(notional))
# 	else:
# 		log.info("!!!!!!!!!!!! INVALID 'order_side' PARAMETER IN update_net_limit_tracker !!!!!!!!!!!!")
# 		return
# 	return












