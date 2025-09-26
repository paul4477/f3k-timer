from ESPythoNOW import *
import struct


def callback(from_mac, to_mac, msg):
  print("ESP-NOW message from %s to %s: %s" % (from_mac, to_mac, msg))
  print(struct.unpack('f', msg))

espnow = ESPythoNow(interface="wlx984827db7610", accept_all=True, callback=callback)
print(espnow)
espnow.start()
print(espnow)

import time
while True:
   msg=struct.pack("f", (time.time() % 1.0)*25)
   espnow.send("FF:FF:FF:FF:FF:FF", msg)
   time.sleep(0.01)
input() # Run until enter is pressed
