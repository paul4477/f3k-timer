import serial
import time
import logging

class Pandora():
    def __init__(self, events):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = "/dev/ttyUSB0"
        self.events = events
        self.port = None
        self.init_serial()
        self.register_handlers()
    
    def write(self, bytes):
        self.port.write(bytes)
        self.port.flush()
        self.logger.debug(f"Sent to serial: {repr(bytes)}")

    def register_handlers(self):
        self.events.on("pandora.tick")(self.tick)
        self.events.on("pandora.second")(self.second)

    def init_serial(self):
        try:
            self.port = serial.Serial('/dev/ttyUSB0', 19200, timeout=None)
            self.logger.debug(f"Serial port opened {self.device}")
            self.write(b"R00G00T0000PT\r")
        except:
            self.logger.exception(f"Couldn't open serial port {self.device}")

    async def tick(self, state):
        if self.port:
            pass
    async def second(self, state):
        if self.port:
            r = state.round.round_number
            g = state.group.group_number
            s = state.get_section_code()
            d = state.round.short_name
            output = f"P|{r:02}"\
                    f"|{g:02}"\
                      f"|1"\
                      f"|{d}\r\n" \
                      f"R{r:02}" \
                      f"G{g:02}" \
                      f"T{state.slot_time:04}" \
                      f"{s}\r".encode('ascii')
            self.write(output)

