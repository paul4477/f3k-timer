import serial
from plugin_base import PluginBase

class Pandora(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.device = self.config.get('device', '/dev/ttyUSB0') # Default device
        self.baud = self.config.get('baud', 19200) # Default baudrate
        self.bits = self.config.get('bits', 8) # Default data bits
        self.parity = serial.PARITY_NONE #self.config.get('parity', 'N') # Default parity
        self.stop = serial.STOPBITS_ONE #self.config.get('stop', 1) # Default stop bits
        
        self.port = None
        self.init_serial()
    
    def write(self, bytes):
        self.port.write(bytes)
        self.port.flush()
        self.logger.debug(f"Sent to serial: {repr(bytes)}")

    def init_serial(self):
        try:
            self.port = serial.Serial(self.device, 
                                      baudrate=self.baud, 
                                      bytesize=self.bits, 
                                      parity=self.parity, 
                                      stopbits=self.stop, 
                                      timeout=None)
            self.logger.debug(f"Serial port opened {self.device}")
            self.write(b"R00G00T0000PT\r")
        except:
            self.logger.exception(f"Couldn't open serial port {self.device}")

    async def onSecond(self, state):
        if self.port:
            r = state.round.round_number
            g = state.group.group_number
            s = state.section.get_serial_code()
            d = state.round.short_name
            au_f = state.section.get_flight_number() or '1'
            # P|01|02|1
            output = f"P|{r:02}"\
                    f"|{g:02}"\
                      f"|{au_f}"\
                      f"|{d}\r\n" \
                      f"R{r:02}" \
                      f"G{g:02}" \
                      f"T{state.time_digits}" \
                      f"{s}\r".encode('ascii')
            try: self.write(output)
            except Exception as e:
                self.logger.error(f"Write failed to device {self.device}")

