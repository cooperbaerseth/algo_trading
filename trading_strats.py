# File to implement modular trading strategies, meaning that they can be run from any script.
#	- can be run on historical data or live data

import robin_stocks as rs
import sys
import logging
import time
import pickle
import pandas as pd
import numpy as np
from scipy import stats
import csv
import os
import pdb

import utils
import plotting

debug = False

class TradeInterface:
	def __init__(self, trade_symbol, net_tracker_fname, live=False, hist_file=None, hist_range=None, record_activity=True, moving_avg_params=(12, 'EMA'), plot_post_run=False):
		self.net_tracker_fname = net_tracker_fname
		self.cur_net, self.net_min = utils.get_net_tracker_info(self.net_tracker_fname)
		self.live = live
		self.hist = None
		self.cur_hist_ind = None
		self.num_sells = 0
		self.num_buys = 0
		self.num_voided_sells = 0
		self.max_net = -float("inf")
		self.min_net = float("inf")
		self.trade_symbol = trade_symbol
		self.cur_quant, self.cur_quant_val = utils.get_held_crypto_value(symbol=self.trade_symbol)
		self.start_quant, self.start_quant_val = self.cur_quant, self.cur_quant_val
		self.record_activity = record_activity
		self.activity_column_dict = utils.activity_column_dict
		self.activity_column_names = list(utils.activity_column_dict.keys())
		self.activity_row = [None for _ in range(len(self.activity_column_dict))]
		self.plot_post_run = plot_post_run
		self.hist_range = hist_range

		# moving average init
		self.moving_avg_factor = moving_avg_params[0]
		self.moving_avg_type = moving_avg_params[1]
		if self.moving_avg_type == 'SMA':
			# method 1
			self.sma_queue = np.zeros(self.moving_avg_factor)

			# # method 2
			# self.ma_sum = 0
			# self.prev_price = None
			# self.ma_counter = 0
			# self.ma_out = 0

			self.sma = 0.0
		elif self.moving_avg_type == 'EMA':
			self.ema = 0.0

		# queue to determine general trend (slope) of price
		# slope_queue_size = 5
		slope_queue_size = 10
		self.slope_queue = np.zeros(slope_queue_size)
		self.trend = None # trend will be 0 for negative, 1 for positive

		# if not running on live data, load the history file into a dataframe
		if not live:
			if hist_file == None:
				logging.error("!!!!!!!!!!!! PriceGetter: HISTORY FILE CANNOT BE BLANK WHEN RUNNING STRAT ON HIST DATA !!!!!!!!!!!!")
				self.report_and_quit()

			hist_df = pd.read_csv(filepath_or_buffer=hist_file, sep='|', names=['price', 'datetime'])
			hist_df['datetime'] = pd.to_datetime(hist_df['datetime'])
			self.hist = hist_df
			if self.hist_range != None:
				self.cur_hist_ind = self.hist_range[0]
			else:
				self.cur_hist_ind = 0

		# setup file to record activity
		if self.record_activity:
			file_name = logging.getLogger().handlers[0].baseFilename.split('/')[-1]
			file_dir = '/'.join(logging.getLogger().handlers[0].baseFilename.split('/')[:-1]) + '/'
			file_name = 'activity_log_' + file_name[:-3] + 'csv'
			self.activity_file_dir = (file_dir + file_name)
			self.activity_log_file = open((file_dir + file_name), 'a')
			self.activity_log_writer = csv.writer(self.activity_log_file, delimiter='|', lineterminator='\n')

			# write the column names as the header
			self.activity_log_writer.writerow(list(self.activity_column_dict.keys()))

	def get_col_index(self, col_name):
		return int(self.activity_column_names.index(col_name))

	def get_moving_avg(self, price):
		if self.moving_avg_type == 'SMA':
			# method 1
			# pop oldest price and put newest price
			x = self.sma_queue
			x[:-1] = x[1:]
			x[-1] = price
			self.sma = x.sum() / x.shape[0]
			self.sma_queue = x
			if debug:
				logging.info(self.sma_queue)

			# # method 2
			# if self.ma_counter > self.moving_avg_factor:
			# 	pass
			# else:
			# 	self.ma_sum += price
			# 	self.ma_out = price

		elif self.moving_avg_type == 'EMA':
			# pdb.set_trace()
			#(Close - previous EMA) * (2 / n+1) + previous EMA
			prev_ema = self.ema
			self.ema = (price - prev_ema) * (2/self.moving_avg_factor+1) + prev_ema
			print(self.moving_avg_factor)
			print(price)
			print(self.ema)
			print(prev_ema)

		# populate slope queue with current moving average and determine current slope
		y = self.slope_queue
		y[:-1] = y[1:]
		y[-1] = self.sma if self.moving_avg_type == 'SMA' else self.ema
		self.slope_queue = y
		slope, _, _, _, _ = stats.linregress(np.arange(y.shape[0]), y) # using all points for slope
		if slope > 0:
			self.trend = 1
		else:
			self.trend = 0
		
		
		if self.moving_avg_type == 'SMA':
			return self.sma
		elif self.moving_avg_type == 'EMA': 
			return self.ema

	def get_next_price(self, verbose=False):
		if self.live:
			logging.info("live")
		else:
			if self.cur_hist_ind >= self.hist.shape[0] or (self.hist_range != None and self.cur_hist_ind >= self.hist_range[1]): # second condition ends the program if we surpass the set history file range
				logging.info("!!!!!!!!!!!! Done with history processing... ending program !!!!!!!!!!!!")
				self.report_and_quit()
			if verbose: logging.info("Price: " + str(self.hist['price'][self.cur_hist_ind]))
			next_price =  self.hist['price'][self.cur_hist_ind]
			self.cur_hist_ind += 1

		ma = self.get_moving_avg(next_price)

		# record activity for all non order-specific columns
		if self.record_activity:
			if self.live:
				self.activity_row[self.get_col_index('datetime')] = pd.to_datetime(time.strftime("%Y%m%d-%H%M%S"))
			else:
				self.activity_row[self.get_col_index('datetime')] = self.hist['datetime'][self.cur_hist_ind-1]
			self.activity_row[self.get_col_index('trade_symbol')] = self.trade_symbol
			self.activity_row[self.get_col_index('price')] = next_price
			self.activity_row[self.get_col_index('moving_average')] = ma
			self.activity_row[self.get_col_index('trend')] = self.trend
			self.activity_row[self.get_col_index('current_net')] = self.cur_net
			self.activity_row[self.get_col_index('current_quantity')] = self.cur_quant

		# logging.info("price: " + str(next_price))
		# logging.info("ma: " + str(ma))
		# logging.info("ma - price: " + str(ma - next_price))

		# return next_price
		# return ma # trading based on moving average rather than actual price
		return next_price, ma

	def final_order_check(self, order_side, quantity, price, verbose=False):
		if verbose:
			notional = quantity * price
			header = "============ Order Report: " + order_side + "($" + str(price) + ")" " ============"
			logging.info(header)
			logging.info("Net tracker: " + self.net_tracker_fname)
			logging.info("Current net: " + str(self.cur_net))
			if order_side == 'buy':
				logging.info("Net change: -" + str(notional))
			elif order_side == 'sell':
				logging.info("Net change: +" + str(notional))
			logging.info("Net min: " + str(self.net_min))

			logging.info("Current held quantity: " + str(self.cur_quant))
			if order_side == 'buy':
				logging.info("Held quantity change: +" + str(quantity))
			elif order_side == 'sell':
				logging.info("Held quantity change: -" + str(quantity))

			logging.info(("="*len(header)) + "\n")
			# if verbose:
			# 	logging.info("====== Net Tracker Status ======")
			# 	logging.info("Current net: " + str(self.cur_net))
			# 	logging.info("Net min: " + str(self.net_min))
			# 	logging.info("================================\n")


		if self.cur_net < self.net_min:
		# if self.cur_net < self.net_min or self.cur_net > 30000:
			logging.info("!!!!!!!!!!!! NET PROFIT FELL BELOW NET MIN !!!!!!!!!!!!")
			logging.info("!!!!!!!!!!!! ENDING PROGRAM !!!!!!!!!!!!")
			self.report_and_quit()

	def update_net_limit_tracker(self, order_side, notional, verbose=False):
		if order_side == "buy":
			self.cur_net -= notional
		elif order_side == "sell":
			self.cur_net += notional
		else:
			logging.info("!!!!!!!!!!!! INVALID 'order_side' PARAMETER IN update_net_limit_tracker !!!!!!!!!!!!")
			return

		# save updated net limit tracker
		net_tracker_package = (self.cur_net, self.net_min)
		net_tracker_path = utils.net_tracker_dir + self.net_tracker_fname
		with open(net_tracker_path, 'wb') as f:
			pickle.dump(net_tracker_package, f)

		# update min/max net tracking
		if self.cur_net > self.max_net:
			self.max_net = self.cur_net
		if self.cur_net < self.min_net:
			self.min_net = self.cur_net

		return

	def place_order(self, symbol, trade_amount, trade_unit, order_side, ref_price, verbose=False):
		# get current price
		if self.live:
			logging.info("getting current live price in place order not implemented yet")
		else:
			price = self.hist['price'][self.cur_hist_ind-1]

		# convert amount to quantity (fractional coins not allowed with doge)
		if trade_unit == 'dollar':
			quantity = round(trade_amount/price)
		elif trade_unit == 'coin':
			quantity = trade_amount

		# if the order is a sell, check if we have enough to sell the proposed amount
		if order_side == 'sell':
			if self.cur_quant < quantity:
				if verbose:
					# logging.info("!!!!!!!!!!!! NOT ENOUGH QUANTITY TO SELL PROPOSED AMOUNT !!!!!!!!!!!!")
					# logging.info("!!!!!!!!!!!! WAITING FOR BUY !!!!!!!!!!!!\n")
					pass
				self.num_voided_sells += 1
				return None, None

		if self.live:
			# order_info = rs.robinhood.orders.order_buy_crypto_by_quantity(
		# 					symbol=symbol,
		# 					quantity=quantity,
		# 					timeInForce='gtc', 
		# 					jsonify=True)
			logging.info("order live not implemented")
		else:
			# update_net_limit_tracker(fname, order_side, notional, verbose=False)
			self.update_net_limit_tracker(
				order_side=order_side, 
				notional=(quantity*price), 
				verbose=verbose)

		#TODO: if live, confirmed price should be taken from the confirmed order info, not the price we _wanted_ (it may be different)
		if self.live:
			logging.info("..... need to get confirmed price/amount from order info here .....")
			pass
		else:
			confirmed_price = price
			confirmed_amnt_quant = quantity
			confirmed_amnt_dollars = confirmed_price*quantity

		# update total buys/sells and cur_quant/cur_val tracking
		if order_side == 'buy':
			self.num_buys += 1
			if self.live:
				# update self.cur_quant, self.cur_quant_value via robin_stocks API
				# self.cur_quant, self.cur_quant_val = utils.get_held_crypto_value(symbol=self.trade_symbol)
				pass
			else:
				self.cur_quant += quantity
				self.cur_quant_val = self.cur_quant * float(rs.robinhood.crypto.get_crypto_quote(symbol=self.trade_symbol, info='ask_price'))
		elif order_side == 'sell':
			self.num_sells += 1
			if self.live:
				# update self.cur_quant, self.cur_quant_value via robin_stocks API
				# self.cur_quant, self.cur_quant_val = utils.get_held_crypto_value(symbol=self.trade_symbol)
				pass
			else:
				self.cur_quant -= quantity
				self.cur_quant_val = self.cur_quant * float(rs.robinhood.crypto.get_crypto_quote(symbol=self.trade_symbol, info='ask_price'))

		# record order-specific activity columns
		if self.record_activity:
			self.activity_row[self.get_col_index('order_side')] = order_side
			self.activity_row[self.get_col_index('confirmed_price')] = confirmed_price
			self.activity_row[self.get_col_index('ref_price')] = ref_price
			self.activity_row[self.get_col_index('order_amnt_dollars')] = confirmed_amnt_dollars
			self.activity_row[self.get_col_index('order_amnt_quant')] = confirmed_amnt_quant

		# check if the end program condition is met and report the order details
		# self.final_order_check(order_side=order_side, quantity=quantity, price=price, verbose=True)
		self.final_order_check(order_side=order_side, quantity=quantity, price=price, verbose=False)

		# return price and quantity ordered
		return price, quantity 

	def flush_activity_record(self):
		self.activity_log_writer.writerow(self.activity_row)
		self.activity_row = [None for _ in range(len(self.activity_column_dict))]

	def report_and_quit(self):
		logging.info("============ Final Report ============")
		logging.info("Total buys: " + str(self.num_buys))
		logging.info("Total sells: " + str(self.num_sells))
		logging.info("Total voided sells: " + str(self.num_voided_sells))
		logging.info("Max net: " + str(self.max_net))
		logging.info("Min net: " + str(self.min_net))
		logging.info("Start quant: " + str(self.start_quant))
		logging.info("End quant: " + str(self.cur_quant))
		logging.info("Start val: " + str(self.start_quant_val))
		logging.info("End val: " + str(self.cur_quant_val))
		logging.info("======================================")

		# close activity record file
		if self.record_activity:
			self.activity_log_file.close()

		# show results on plot
		if self.plot_post_run:
			plotting.basic_plot(self.activity_file_dir, self)

		quit()


def get_percent_diff(base_price, cur_price):
	return ((cur_price - base_price) / base_price)*100

def test_strat1(net_tracker_fname, hist_file_dir=None, plot_post_run=False):
	# Strategy summary:
	# This simple test strategy starts with a sell, waits till the price comes down a certain amount, and sells again. 
	# 	At any point, if the current price >= the last sell price, we buy back. Whether or not we put the profit back 
	#	into the subsequent buy is a variable parameter. The point is to catch when the price is making dips, sell near
	# 	the top, and buy near the bottom.

	# history range setting
	hist_range = None # uses whole history file
	# hist_range = [40000, 60000]
	# hist_range = [0, 65500]
	# hist_range = [0, 72800]
	# hist_range = [0, 37900]

	# define starting condition parameters
	# Starting condition will be when:
	#	- the price goes some percentage (percent_sell_thresh) above the average price over some defined interval (avg_interval)
	avg_interval = 50
	
	percent_sell_thresh = -1.0
	# percent_sell_thresh = -0.5
	
	buyback_percent_thresh = 2.0
	# buyback_percent_thresh = 1.0
	# buyback_percent_thresh = 0.5
	
	# buyback diminish factor shrinks the buyback threshold as we increase the number of consecutive sells (insentivises taking profit from sells)
	# buyback_dim_factor = 1 # no dim factor
	buyback_dim_factor = .9
	# buyback_dim_factor = .6
	# buyback_dim_factor = .5
	# buyback_dim_factor = .3

	# buyback_queue_factor = 3 # buyback queue factor determines how many values to store in the buyback queue before determining a buy is valid. All prices in the buyback queue must meet the buyback condition
	buyback_queue_factor = 3
	# buyback_queue_factor = 1

	sell_queue_factor = 3
	# sell_queue_factor = 1
	
	# TODO: bug with exponential moving average... check formula or implementation 
	# moving_avg_params = (12, 'EMA') # moving average to record
	# moving_avg_params = (5, 'EMA')
	# moving_avg_params = (120, 'EMA')
	# moving_avg_params = (15, 'SMA')
	# moving_avg_params = (20, 'SMA')
	# moving_avg_params = (30, 'SMA')
	# moving_avg_params = (40, 'SMA')
	# moving_avg_params = (50, 'SMA')
	# moving_avg_params = (70, 'SMA')
	# moving_avg_params = (100, 'SMA')
	moving_avg_params = (200, 'SMA')
	# moving_avg_params = (500, 'SMA')
	# moving_avg_params = (1000, 'SMA')

	# trade parameters:
	symbol = utils.doge_ticker_symbol 	# trading dogecoin
	
	# trade_on = "exact_price"	# "trad_on" determines if we make trade decisions based on the exact price or the moving average
	trade_on = "moving_average"
	
	# trade_amount = 0.5
	# trade_amount = 50
	# trade_amount = 500
	# trade_amount = 700
	trade_amount = 5000
	
	trade_unit = 'dollar'
	# trade_unit = 'coin'
	
	side = 'sell'
	# side = 'buy'
	
	# buyback type determines if we keep the profit or reinvest it in the coin (dollar reinvests)
	# buyback_type = 'coin' 
	buyback_type = 'dollar'
	# sleep_time = 0.05
	sleep_time = 0

	# initialize price getter
	if hist_file_dir == None:
		live_mode = True
	elif os.path.exists(hist_file_dir):
		live_mode = False
	else:
		logging.error("!!!!!!!!!!!! PriceGetter: HISTORY FILE CANNOT BE BLANK WHEN RUNNING STRAT ON HIST DATA !!!!!!!!!!!!")
		quit()
	# ti = TradeInterface(trade_symbol=symbol, net_tracker_fname=net_tracker_fname, live=live_mode, hist_file=hist_file_dir, record_activity=False)
	ti = TradeInterface(
		trade_symbol=symbol, 
		net_tracker_fname=net_tracker_fname, 
		live=live_mode, 
		hist_file=hist_file_dir, 
		hist_range=hist_range, 
		record_activity=True, 
		moving_avg_params=moving_avg_params, 
		plot_post_run=plot_post_run)

	# get average price over interval
	price_sum = 0.0
	for i in range(avg_interval):
		temp, _ = ti.get_next_price()
		price_sum += temp
	start_price = price_sum / avg_interval
	logging.info("Start price: " + str(start_price))

	# search for percent threshold change to start trading
	buyback_amnt = 0.0
	# ref_price = start_price.copy()
	sell_ref_price = start_price.copy()	# sell reference price tracks the local peak for reference in starting a sell sequence
	buyback_ref_price = start_price.copy() # buyback reference price tracks the local minimum in order to get the best buyback price (potentially better than leaving the buyback reference as the last sell point)
	last_trade = 'buy'
	# loop = True
	# while loop:
	# 	exact_price, ma = ti.get_next_price()
	# 	if trade_on == "exact_price":
	# 		cur_price = exact_price
	# 	elif trade_on == "moving_average":
	# 		cur_price = ma
	# 	cur_change = get_percent_diff(base_price=ref_price, cur_price=cur_price)
	# 	logging.info("===============================")
	# 	logging.info("Reference price: " + str(ref_price))
	# 	logging.info("Current price: " + str(cur_price))
	# 	logging.info("Percent change: " + str(cur_change))
	# 	logging.info("===============================\n")
	# 	if cur_change < percent_sell_thresh and ti.trend == 0:
	# 		logging.info("!!!!!!!!!!!! Percent threshold met !!!!!!!!!!!!")
	# 		# def place_order(symbol, trade_amount, trade_unit, order_side):
	# 		confirmed_price, confirmed_quantity = ti.place_order(
	# 			symbol=symbol, 
	# 			trade_amount=trade_amount, 
	# 			trade_unit=trade_unit, 
	# 			order_side=side, 
	# 			verbose=True)
	# 		ref_price = confirmed_price.copy()
	# 		if buyback_type == 'coin':
	# 			buyback_amnt += confirmed_quantity
	# 		elif buyback_type == 'dollar':
	# 			buyback_amnt += (confirmed_price * confirmed_quantity)
	# 		loop = False
	# 		continue
	# 	if cur_price > ref_price:
	# 		ref_price = cur_price
	# 	if ti.record_activity:
	# 		ti.flush_activity_record()
	# 	if live_mode == False:
	# 		time.sleep(sleep_time)

	# start main sell-buy loop here
	sleep_time = 0
	loop = True
	# last_trade = 'sell'
	consec_sells = 0
	cur_price = np.zeros(buyback_queue_factor)
	qind = 0
	while loop:
		# cur_price = ti.get_next_price() # without queue
		exact_price, ma = ti.get_next_price()# with queue
		if trade_on == "exact_price":
			temp = exact_price
		elif trade_on == "moving_average":
			temp = ma
		cur_price[qind] = temp
		# cur_change = get_percent_diff(base_price=ref_price, cur_price=cur_price)
		cur_change_sell = get_percent_diff(base_price=sell_ref_price, cur_price=cur_price)
		cur_change_buyback = get_percent_diff(base_price=buyback_ref_price, cur_price=cur_price)
		# logging.info("===============================")
		# logging.info("Reference price: " + str(ref_price))
		# logging.info("Current price: " + str(cur_price))
		# logging.info("Percent change: " + str(cur_change))
		# logging.info("===============================\n")

		# compute the buyback diminish factor... if we have no consecutive sells (0), we should set the diminish factor to 1 (no diminishing)
		if consec_sells > 0:
			cur_buyback_dim_factor = buyback_dim_factor ** consec_sells
		else:
			cur_buyback_dim_factor = 1

		# if cur_price >= ref_price: # without buyback queue factor
		if cur_price[qind] >= sell_ref_price:
			# pdb.set_trace()
			# this condition is for increasing the reference price when looking for a sell threshold
			# if cur_price > ref_price and last_trade == 'buy': # this condition makes the algo buy if we have the same price multiple times in a row
			if last_trade == 'buy':
				# ref_price = cur_price # without buyback queue factor
				sell_ref_price = cur_price[qind]
				continue # (?)
			# buy back the amount that was sold (in coins) to prevent more losses
			# - use cumul_sell_amnt for amount to buy back
			# - keep reference price the same
			# if cur_change >= (buyback_percent_thresh * cur_buyback_dim_factor): # not using a queue
			# if cur_change[qind] >= (buyback_percent_thresh * cur_buyback_dim_factor): # using only the most recent price (not making use of the queue)
			if np.where(cur_change_buyback >= (buyback_percent_thresh * cur_buyback_dim_factor), 1, 0).sum() == buyback_queue_factor: # using a queue, all percent changes in queue should meet the buyback condition 
				# plotting.basic_plot(ti.activity_file_dir)
				# pdb.set_trace()
				logging.info("!!!!!!!!!!!! STOP LOSS BUY TRIGGERED !!!!!!!!!!!!")
				confirmed_price, confirmed_quantity = ti.place_order(
					symbol=symbol, 
					trade_amount=buyback_amnt, 
					trade_unit=buyback_type, 
					order_side='buy', 
					ref_price=buyback_ref_price,
					verbose=True)
				last_trade = 'buy'
				buyback_amnt = 0.0
				consec_sells = 0
				sell_ref_price = confirmed_price
				buyback_ref_price = confirmed_price
		# elif cur_change < percent_sell_thresh: # without buyback queue factor
		# elif cur_change[qind] < percent_sell_thresh: # without using queue for sell condition
		elif np.where(cur_change_sell < percent_sell_thresh, 1, 0).sum() == sell_queue_factor: # using queue to exclude anomalous lows
			# logging.info("!!!!!!!!!!!! PERCENT THRESHOLD SELL TRIGGERED !!!!!!!!!!!!")
			if ti.trend == 0:
				confirmed_price, confirmed_quantity = ti.place_order(
					symbol=symbol, 
					trade_amount=trade_amount, 
					trade_unit=trade_unit, 
					order_side='sell', 
					ref_price=sell_ref_price,
					verbose=True)
				if confirmed_price is not None:	# place order returns none if we have no more quantity to sell
					if buyback_type == 'coin':
						buyback_amnt += confirmed_quantity
					elif buyback_type == 'dollar':
						buyback_amnt += (confirmed_price * confirmed_quantity)
					last_trade = 'sell'
					consec_sells += 1
					sell_ref_price = confirmed_price
					buyback_ref_price = confirmed_price
				else:
					sell_ref_price = cur_price[qind]
					buyback_ref_price = cur_price[qind]
		elif cur_price[qind] < buyback_ref_price:
			buyback_ref_price = cur_price[qind]
		# if price keeps going lower but the sell condition isn't met yet, set reference price lower... this means the buyback threshold will be more sensitive

		# debug price/ma
		if debug:
			logging.info("===================")
			logging.info("price: " + str(ti.hist['price'][ti.cur_hist_ind-1]))
			logging.info("queue: " + str(cur_price))
			logging.info("_next_price_: " + str(cur_price[qind]))
			logging.info("===================\n")

		# update buyback queue rolling index
		qind += 1
		if qind >= buyback_queue_factor:
			qind = 0 
		
		if ti.record_activity:
			ti.flush_activity_record()
		if live_mode == False:
			time.sleep(sleep_time)



















