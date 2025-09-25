from ESPythoNOW import *
import struct
import time

from collections import deque

base  = [0]*100
last_hundred = deque(base)

def callback(from_mac, to_mac, msg):
  #print("ESP-NOW message from %s to %s: %s" % (from_mac, to_mac, msg))
  #print(struct.unpack('f', msg))
  struct.unpack('f', msg)
  last_hundred.pop()
  last_hundred.appendleft(time.time())
  

espnow = ESPythoNow(interface="wlan0", accept_all=True, callback=callback)
print(espnow)
espnow.start()
print(espnow)

import time
while True:#True:
   msg=struct.pack("f", (time.time() % 1.0)*25)
   #espnow.send("FF:FF:FF:FF:FF:FF", msg)
   try: print (1/((last_hundred[0] - last_hundred[99]) / 100.0)) 
   except: pass
   time.sleep(5)
input() # Run until enter is pressed
