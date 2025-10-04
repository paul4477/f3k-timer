import serial
from plugin_base import PluginBase

class Pandora(PluginBase):
    def __init__(self, events):
        super().__init__(events)
        self.device = "/dev/ttyUSB0"
        self.port = None
        self.init_serial()
    
    def write(self, bytes):
        self.port.write(bytes)
        self.port.flush()
        self.logger.debug(f"Sent to serial: {repr(bytes)}")

    def init_serial(self):
        try:
            self.port = serial.Serial('/dev/ttyUSB0', 19200, timeout=None)
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
            self.write(output)

