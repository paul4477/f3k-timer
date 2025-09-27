import logging
from ESPythoNOW import *
import struct
import time

class ESPNow():
    def __init__(self, events):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = "wlan1"
        self.events = events
        self.port = None
        self.init_port()
        self.register_handlers()
        self.rate_limit = 1/6
        self.last_update = 0
    
    def write(self, bytes):
        self.port.send("FF:FF:FF:FF:FF:FF", bytes)
        self.logger.debug(f"ESPNow broadcast: {repr(bytes)}")

    def register_handlers(self):
        self.events.on("espnow.tick")(self.tick)
        self.events.on("espnow.second")(self.second)

    def callback(self, from_mac, to_mac, msg):
        ## We're not listening for anything here.
        pass
    
    def init_port(self):
        try:
            self.port = ESPythoNow(interface=self.device, accept_all=True, callback=self.callback)
            self.port.start()
            self.logger.debug(f"ESPNow connection opened {self.port}")
        except:
            self.logger.exception(f"Couldn't start ESPNow {self.device}")

    def format_sec_min(self, seconds):
        return f"{int(seconds/60)}:"

    def limit_rate(self):
        ## Check how recently we've been called
        ## Reduce rate of updates to max of 1/self.rate_limit per second
        now = time.time()
        if (now - self.last_update) >= self.rate_Limit:
            self.last_update = now
            return False
        else:
            return True
       
    async def tick(self, state):
        if (not self.limit_rate()) and self.port:        
            msg=struct.pack("6p", self.state.time_str.encode("ascii"))
            self.write(msg)

    async def second(self, state):
        if self.port:
            msg=struct.pack("6p", self.state.time_str.encode("ascii"))
            self.write(msg)


