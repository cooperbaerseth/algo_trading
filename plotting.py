import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import utils

import pdb

def basic_plot(file_dir, trade_interface):
	# load log file into pandas dataframe
	df = pd.read_csv(
		filepath_or_buffer=file_dir, 
		delimiter='|', 
		names=list(utils.activity_column_dict.keys()), 
		dtype=utils.activity_column_dict,
		header=0)

	fig, ax = plt.subplots()
	plot_x = np.arange(df.shape[0])

	# plot the price over time
	ax.plot(plot_x, df['price'], zorder=1, label='price')

	# plot the moving average over time
	ax.plot(plot_x, df['moving_average'], '--c', linewidth=1, zorder=2, label='moving avg')

	# plot the sells
	sell_inds = df.index[df['order_side']=='sell'].tolist()
	sell_prices_exact = df['price'].iloc[sell_inds]
	sell_prices_ma = df['moving_average'].iloc[sell_inds]
	sell_ref_prices = df['ref_price'].iloc[sell_inds]
	# sell_prices = df['moving_average'].iloc[sell_inds]
	ax.scatter(sell_inds, sell_prices_exact, color='r', zorder=3, label='sell price (exact)')
	ax.scatter(sell_inds, sell_prices_ma, marker='d', color='r', zorder=3, label='sell price (MA)')
	ax.scatter(sell_inds, sell_ref_prices, facecolors='none', edgecolors='r', zorder=3, label='sell reference price')

	# plot the buys
	buy_inds = df.index[df['order_side']=='buy'].tolist()
	buy_prices_exact = df['price'].iloc[buy_inds]
	buy_prices_ma = df['moving_average'].iloc[buy_inds]
	buy_ref_prices = df['ref_price'].iloc[buy_inds]
	# buy_prices = df['moving_average'].iloc[buy_inds]
	ax.scatter(buy_inds, buy_prices_exact, color='g', zorder=3, label='buy price (exact)')
	ax.scatter(buy_inds, buy_prices_ma, marker='d', color='g', zorder=3, label='buy price (MA)')
	ax.scatter(buy_inds, buy_ref_prices, facecolors='none', edgecolors='g', zorder=3, label='buy reference price')

	# plot trend markers
	size = 1
	offset = -0.008
	neg_trend = df.index[df['trend']==0].tolist()
	trend_mark = df['trend_ma'].iloc[neg_trend] + offset
	ax.scatter(neg_trend, trend_mark, marker='v', color='g', s=size, zorder=3, label='trend down')

	pos_trend = df.index[df['trend']==1].tolist()
	trend_mark = df['trend_ma'].iloc[pos_trend] + offset
	ax.scatter(pos_trend, trend_mark, marker='^', color='r', s=size, zorder=3, label='trend up')

	# set y limits
	buff = 0.01
	y = df['price']
	ax.set_ylim([y.min()-buff, y.max()+buff])

	# title
	# fig.suptitle("percent_sell_thresh: -0.5")

	plt.legend()
	ax.grid()
	plt.show()


