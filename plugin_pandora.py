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
        self._backoff = self.make_backoff(max_delay=30)
        self.init_serial()
    
    def write(self, bytes):
        if self.port is None:
            if self._backoff.ready():
                self.init_serial()
            if self.port is None:
                return  # still failing, skip write
        try:
            self.port.write(bytes)
            self.port.flush()
            self._backoff.success()
            self.logger.debug(f"Sent to serial {self.device}: {repr(bytes)}")
        except Exception as e:
            self.port = None
            delay = self._backoff.failure()
            self.logger.error(f"Write failed to device {self.device} with error: {e}")
            self.logger.warning(f"Retrying serial connection in {delay}s")

    def init_serial(self):
        try:
            self.port = serial.Serial(self.device, 
                                      baudrate=self.baud, 
                                      bytesize=self.bits, 
                                      parity=self.parity, 
                                      stopbits=self.stop, 
                                      timeout=None)
            self._backoff.success()
            self.logger.debug(f"Serial port opened {self.device}")
            self.write(b"R00G00T0000PT\r")
        except Exception as e:
            self.port = None
            delay = self._backoff.failure()
            self.logger.error(f"Couldn't open serial port {self.device} with error: {e}")
            self.logger.warning(f"Retrying serial connection in {delay}s")

    async def onSecond(self, state):
        if self.port is not None:
            r_num = state.round.round_number if state.round else 0
            g_num = state.group.group_number if state.group else 0
            serial_code = state.section.get_serial_code() if state.section else "ST"
            short_name = state.round.short_name if state.round else "- - N/A"
            au_f = state.section.get_flight_number() or "0"
            
            output = f"P|{r_num:02}"\
                    f"|{g_num:02}"\
                      f"|{au_f}"\
                      f"|{short_name}\r\n" \
                      f"R{r_num:02}" \
                      f"G{g_num:02}" \
                      f"T{state.time_digits}" \
                      f"{serial_code}\r".encode('ascii')
            self.write(output)
