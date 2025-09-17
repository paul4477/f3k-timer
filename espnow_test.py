from ESPythoNOW import *

def callback(from_mac, to_mac, msg):
  print("ESP-NOW message from %s to %s: %s" % (from_mac, to_mac, msg))

espnow = ESPythoNow(interface="wlp113s0", accept_all=True, callback=callback)
espnow.start()
input() # Run until enter is pressed