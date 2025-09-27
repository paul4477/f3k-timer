import serial
import time
import logging

class Pandora():
    def __init__(self, player, events):
        self.device = "/dev/ttyUSB0"
        self.player = player
        self.events = events
        self.port = None
        self.init_serial()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.register_handlers()
    
    def write(self, bytes):
        self.port.write(bytes)
        self.logger.debug(f"Sent to serial: {repr(bytes)}")
        self.port.flush()

    def register_handlers(self):
        self.events.on("pandora.tick")(self.tick)
        self.events.on("pandora.second")(self.second)

    def init_serial(self):
        try:
            self.port = serial.Serial('/dev/ttyUSB0', 19200, timeout=None)
        except:
            self.logger.exception(f"Couldn't open serial port {self.device}")

    async def tick(self, state):
        if self.port:
            pass
    async def second(self, state):
        if self.port:
            r = self.state.round_number
            g = self.state.group_number
            s = "WT"
            output = f"P|{r}|{g}|1|{t} - Description\r\nR{r}G{g}T{self.state.slot_time:04}{s}\r".encode('ascii')
            self.write()

