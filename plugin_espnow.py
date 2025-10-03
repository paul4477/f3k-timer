from ESPythoNOW import *
import struct
from plugin_base import PluginBase

class ESPNow(PluginBase):
    def __init__(self, events):
        super().__init__(events)
        self.device = "wlan1"
        self.port = None
        self.init_port()
        self.rate_limit = 1/6
        self.last_update = 0
    
    def write(self, bytes):
        self.port.send("FF:FF:FF:FF:FF:FF", bytes)
        #self.logger.debug(f"ESPNow broadcast: {repr(bytes)}")

    def callback(self, from_mac, to_mac, msg):
        ## We're not listening for anything here.
        pass
    
    def init_port(self):
        try:
            self.port = ESPythoNow(interface=self.device, accept_all=True, callback=self.callback)
            self.port.start()
            self.logger.debug(f"ESPNow connection opened {self.port}")
        except:
            self.logger.error(f"Couldn't start ESPNow {self.device}")

    async def onTick(self, state):
        if (not self.limit_rate()) and self.port:        
            msg=struct.pack("6p", state.time_str.encode("ascii"))
            self.write(msg)

    async def onSecond(self, state):
        if self.port:
            msg=struct.pack("6p", state.time_str.encode("ascii"))
            self.write(msg)


