import robin_stocks as rs
import sys
import logging
import time
import pickle
import os
import pdb

import utils
import trading_strats as ts

# login
rs.robinhood.login(username=utils.rh_username, 
	password=utils.rh_password, 
	expiresIn=utils.all_day, 
	by_sms=True)

# logging
logfile_dir = 'logs/run_strat_on_hist_logs/' + time.strftime("%Y%m%d-%H%M%S")
logfile_name = "/" + time.strftime("%Y%m%d-%H%M%S") + ".txt" 
if not os.path.exists(logfile_dir):
    os.makedirs(logfile_dir)
logging.basicConfig(
	level=logging.INFO, 
	handlers=[logging.FileHandler(logfile_dir + logfile_name),logging.StreamHandler()],
    format='%(message)s')


def main():
	# Input arguments:
	# new_net: if True, creates a new net tracker (used to limit trades based on net profit)
	# net_name: name of the net tracker to use. If creating a new net tracker, this will be the name used
	# new_net_val: if using a new net tracker, sets the net profit limit (used to stop trading). 
	#	- this usually would be a negative number

	net_limit_tracker_fname = sys.argv[2]
	cur_net, net_min = utils.net_limit_safety_check(sys.argv)
	doge_net_value, _, _ = utils.get_crypto_net_val(id=utils.doge_cur_pair_id, verbose=False)
	invested = utils.get_total_invested(False)
	logging.info("Current net doge profit: " + str(doge_net_value))
	logging.info("Current invested amount: " + str(invested) + '\n')

	# pass hist file to trading strat function
	# hist_data_file = utils.doge_hist_data_dir + "20210425-171628.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210426-110107.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210429-074055.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210428-143019.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210429-154254.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210429-180658.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210502-220006.txt"
	hist_data_file = utils.doge_hist_data_dir + "20210505-084058.txt"	# big dip ... bug present with certain parameters
	# hist_data_file = utils.doge_hist_data_dir + "20210506-155335.txt"
	# hist_data_file = utils.doge_hist_data_dir + "20210509-143523.txt"	
	# hist_data_file = utils.doge_hist_data_dir + "20210513-114520.txt" # file with sleep(0.1) while collecting
	# hist_data_file = utils.doge_hist_data_dir + "20210515-091926.txt" # stagnant price
	# hist_data_file = utils.doge_hist_data_dir + "20210501-181836.txt"	# down up price... - profit
	# hist_data_file = utils.doge_hist_data_dir + "20210516-170749.txt"	

	# hist_data_file = utils.doge_hist_data_dir + "20210504-094158.txt" # short file for debugging
	
	ts.test_strat1(net_tracker_fname=net_limit_tracker_fname, hist_file_dir=hist_data_file, plot_post_run=True)






if __name__ == "__main__":
    main()

