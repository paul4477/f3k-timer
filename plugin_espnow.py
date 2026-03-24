from ESPythoNOW import *
import struct
from plugin_base import PluginBase
import json
import requests, urllib3
import f3k_cl_competition

class ESPNow(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.device = self.config.get('device', 'wlan0') # Default device
        self.broadcast = self.config.get('broadcast', True) # Default to broadcast
        self.format = self.config.get('format', 'json') # Default format json|struct
        self.port = None
        self.init_port()
    
    def write(self, s):
        if not self.broadcast:
            self.logger.warning("broadcast is off but not implemented")

        assert len(s)<250, f"Data too large for ESPNow packet: {len(s)}, <{s}>"
        
        #self.port.send("94:B9:7E:AD:0D:A0", s) ## m5stick 1
        if self.port:
             self.port.send("FF:FF:FF:FF:FF:FF", s)
        

    def write_message(self, msg_type='time', data={}):
        # time - time state
        # p_def - pilot definition
        # g_def - group definition
        message = json.dumps({'t': msg_type, 'd': data}, separators=(',', ':')).encode('ascii')
        self.logger.debug(f"Sending message: {message}, length: {len(message)}")
        self.write(message)


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
        if not self.limit_rate():        
            #self.write(json.dumps(state.get_dict()).encode('ascii'))
            self.write_message('time', state.get_dict())

    async def onSecond(self, state):
        ## Decide if we want to send group/pilot info (doing it less frequently)
        ## In prep section - send pilot defs every minute and at start of section
        if isinstance(state.section, f3k_cl_competition.PrepSection):
            if (state.slot_time % 60 == 50) or (state.slot_time == state.section.sectionTime):
            # Send each pilot definition
                for pilot_id in state.group.pilots:
                    self.write_message('p_def', state.player.pilots[pilot_id].get_dict())
            elif (state.slot_time % 60 == 45):                    
                self.write_message('p_list', state.group.pilots)


