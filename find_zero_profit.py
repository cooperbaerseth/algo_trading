import robin_stocks as rs
import utils
import pdb

# login
rs.robinhood.login(username=utils.rh_username, 
	password=utils.rh_password, 
	expiresIn=utils.all_day, 
	by_sms=True)

doge_price = float(rs.robinhood.crypto.get_crypto_quote(symbol='DOGE', info='ask_price'))
doge_amount, value = utils.get_held_crypto_value(utils.doge_cur_pair_id)
doge_net_value, tot_buys, tot_sells = utils.get_crypto_net_val(id=utils.doge_cur_pair_id, verbose=False)

new_net = doge_net_value
new_dprice = doge_price
while new_net > 0:
	new_dprice -= 0.001
	new_net = (new_dprice * doge_amount) - (tot_buys - tot_sells)
	print("===============")
	print("Price: " + str(new_dprice))
	print("Net: " + str(new_net))





