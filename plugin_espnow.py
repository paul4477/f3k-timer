from ESPythoNOW import *
import struct
from plugin_base import PluginBase

class ESPNow(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.device = self.config.get('device', 'wlan0') # Default device
        self.broadcast = self.config.get('broadcast', True) # Default to broadcast
        self.format = self.config.get('format', 'json') # Default format json|struct
        self.port = None
        self.init_port()
        try: self.rate_limit = 1 / int(self.config.get('rate_limit', 1))
        except ValueError: self.rate_limit = 1
        self.last_update = 0
    
    def write(self, bytes):
        if not self.broadcast:
            self.logger.warning("broadcast is off but not implemented")
        self.port.send("FF:FF:FF:FF:FF:FF", bytes)
        ##self.logger.debug(f"ESPNow broadcast: {repr(bytes)}")

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


