from ESPythoNOW import *
import struct
from plugin_base import PluginBase
import json
import requests, urllib3

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
        #self.port.send("FF:FF:FF:FF:FF:FF", bytes)
        self.port.send("94:B9:7E:AD:0D:A0", bytes)
        ##self.logger.debug(f"ESPNow broadcast: {repr(bytes)}")

    def callback(self, from_mac, to_mac, msg):
        ## We're not listening for anything here.
        self.logger.info(f"Received: {from_mac}, {msg}")
        try:
            msg_dict = json.loads(msg)
        except:
            self.logger.error("Failed to decode json.")
        try:
            command = msg_dict['command'].strip()
        except IndexError:
            return
        c = {'<SKIP': 'skip_previous','SKIP>':'skip_next','UN/PAUSE':'pause','REW':'skip_back','FWD':'skip_fwd'}.get(command, 'pause')
        try: 
            response = requests.post(f'http://localhost/control/{c}', json = msg_dict)
        except requests.RequestException as e:
                          self.logger.error(f"Error sending state to {self.url}: {e}")
                          self.failure_count += 1
                          return
        except urllib3.exceptions.MaxRetryError as e:
                          self.logger.error(f"Max retries exceeded while sending state to {self.url}: {e}")
                          self.logger.error(f"Disabling plugin to prevent further errors.")
                          self.url = None
                          return
        #for item in msg_dict:
            #self.events.trigger("player.pause")
    
    def init_port(self):
        try:
            self.port = ESPythoNow(interface=self.device, accept_all=True, callback=self.callback)
            self.port.start()
            self.logger.debug(f"ESPNow connection opened {self.port}")
        except:
            self.logger.error(f"Couldn't start ESPNow {self.device}")

    async def onTick(self, state):
        #return
        if (not self.limit_rate()) and self.port:        
            self.write(json.dumps(state.get_dict()).encode('ascii'))
            #msg=struct.pack("6p", state.time_str.encode("ascii"))
            #self.write(state.get_dict())

    async def onSecond(self, state):
        if self.port:
            #msg=struct.pack("6p", state.time_str.encode("ascii"))
            #self.write(msg)
            self.write(json.dumps(state.get_dict()).encode('ascii'))


