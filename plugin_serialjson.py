import serial
import f3k_cl_competition
from plugin_base import PluginBase
import json
import struct


class SerialJson(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.device = self.config.get('device', '/dev/ttyUSB1') # Default device
        self.baud = self.config.get('baud', 19200) # Default baudrate
        self.bits = self.config.get('bits', 8) # Default data bits
        self.parity = serial.PARITY_NONE #self.config.get('parity', 'N') # Default parity
        self.stop = serial.STOPBITS_ONE #self.config.get('stop', 1) # Default stop bits
        
        self.port = None
        self.init_serial()
    
    def write(self, bytes):
        try:
            #bytes = struct.pack('>H', len(bytes)) + bytes  # Prepend length of message as 2 bytes
            self.port.write(bytes + '\r'.encode('ascii'))
            self.port.flush()
            self.logger.debug(f"Sent to serial {self.device}: {repr(bytes)}")
        except Exception as e:
                self.logger.error(f"Write failed to device {self.device} with error: {e}")

    def init_serial(self):
        try:
            self.port = serial.Serial(self.device, 
                                      baudrate=self.baud, 
                                      bytesize=self.bits, 
                                      parity=self.parity, 
                                      stopbits=self.stop, 
                                      timeout=None)
            self.logger.debug(f"Serial port opened {self.device}")
        except Exception as e:
            self.logger.error(f"Couldn't open serial port {self.device} with error: {e}")

    def write_message(self, msg_type='time', data={}):
        # time - time state
        # p_def - pilot definition
        # g_def - group definition
        message = json.dumps({'t': msg_type, 'd': data}, separators=(',', ':')).encode('ascii')
        self.logger.debug(f"Sending message: {message}, length: {len(message)}")
        self.write(message)

    async def onTick(self, state):
        if not self.limit_rate():        
            #self.write(json.dumps(state.get_dict()).encode('ascii'))
            self.write_message('time', state.get_dict())

    async def onSecond(self, state):
        # Leave the time updates to the onTick method
        ##self.write_message('time', state.get_dict())

        ## Decide if we want to send group/pilot info (doing it less frequently)
        ## In prep section - send pilot defs every minute and at start of section
        if isinstance(state.section, f3k_cl_competition.PrepSection) and \
            ((state.slot_time % 60 == 50) or (state.slot_time == state.section.sectionTime)):
            # Send each pilot definition
            for pilot_id in state.group.pilots:
                self.write_message('p_def', state.player.pilots[pilot_id].get_dict())
            self.write_message('p_list', state.group.pilots)

