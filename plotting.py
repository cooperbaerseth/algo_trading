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
	ax.plot(plot_x, df['price'], zorder=1)

	# plot the moving average over time
	ax.plot(plot_x, df['moving_average'], '--c', linewidth=1, zorder=2)

	# plot the sells
	sell_inds = df.index[df['order_side']=='sell'].tolist()
	sell_prices = df['price'].iloc[sell_inds]
	# sell_prices = df['moving_average'].iloc[sell_inds]
	ax.scatter(sell_inds, sell_prices, color='r', zorder=3)

	# plot the buys
	buy_inds = df.index[df['order_side']=='buy'].tolist()
	buy_prices = df['price'].iloc[buy_inds]
	# buy_prices = df['moving_average'].iloc[buy_inds]
	ax.scatter(buy_inds, buy_prices, color='g', zorder=3)

	# plot trend markers
	size = 1
	offset = -0.008
	neg_trend = df.index[df['trend']==0].tolist()
	trend_mark = df['moving_average'].iloc[neg_trend] + offset
	ax.scatter(neg_trend, trend_mark, marker='v', color='g', s=size, zorder=3)

	pos_trend = df.index[df['trend']==1].tolist()
	trend_mark = df['moving_average'].iloc[pos_trend] + offset
	ax.scatter(pos_trend, trend_mark, marker='^', color='r', s=size, zorder=3)

	# set y limits
	buff = 0.01
	y = df['price']
	ax.set_ylim([y.min()-buff, y.max()+buff])

	# title
	# fig.suptitle("percent_sell_thresh: -0.5")

	ax.grid()
	plt.show()


