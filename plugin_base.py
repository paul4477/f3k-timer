import logging
import time

class PluginBase():
    def __init__(self, events):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.events = events
        self.register_handlers()
        self.rate_limit = 1
        self._enabled = True
    
    def register_handlers(self):
        self.events.on(f"{self.__class__.__name__}.tick")(self.onTick)
        self.events.on(f"{self.__class__.__name__}.second")(self.onSecond)
        self.events.on(f"{self.__class__.__name__}.newSection")(self.onNewSection)
        self.events.on(f"{self.__class__.__name__}.newGroup")(self.onNewGroup)        
        self.events.on(f"{self.__class__.__name__}.newRound")(self.onNewRound)        

    def is_enabled(self):
        return self._enabled
    def enable(self):
        self._enabled = True
    def disable(self):
        self._enabled = False
    
    def limit_rate(self):
        ## Check how recently we've been called
        ## Reduce rate of updates to max of 1/self.rate_limit per second
        now = time.time()
        if (now - self.last_update) >= self.rate_limit:
            self.last_update = now
            return False
        else:
            return True
       
    async def onTick(self, state):
        #if (not self.limit_rate()) and self.enabled():        
        pass

    async def onSecond(self, state):
        #if self.enabled():
        pass
    async def onNewSection(self, state):
        #if self.enabled():
        pass
    async def onNewGroup(self, state):
        #if self.enabled():
        pass
    async def onNewRound(self, state):
        #if self.enabled():
        pass               


