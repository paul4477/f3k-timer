import logging
import time


class BackoffManager:
    """Tracks exponential backoff state for retryable operations.

    Usage:
        self._backoff = self.make_backoff()

        if self._backoff.ready():
            try:
                do_thing()
                self._backoff.success()
            except Exception as e:
                delay = self._backoff.failure()
                self.logger.warning(f"Retrying in {delay}s")
    """
    def __init__(self, initial_delay=1, max_delay=600):
        self._retry_delay = 0
        self._next_retry_at = 0
        self._initial_delay = initial_delay
        self._max_delay = max_delay

    def ready(self) -> bool:
        """Returns True if enough time has passed to attempt again."""
        return time.monotonic() >= self._next_retry_at

    def success(self):
        """Call after a successful attempt. Resets backoff."""
        self._retry_delay = 0
        self._next_retry_at = 0

    def failure(self) -> float:
        """Call after a failed attempt. Returns the new delay (seconds)."""
        self._retry_delay = min(max(self._retry_delay * 2, self._initial_delay), self._max_delay)
        self._next_retry_at = time.monotonic() + self._retry_delay
        return self._retry_delay


class PluginBase():
    def __init__(self, events, config):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.events = events
        self.register_handlers()
        self._enabled = True
        self.last_update = 0
        self.config = config
        try: self.rate_limit = 1 / int(self.config.get('rate_limit', 1))
        except ValueError: self.rate_limit = 1

    def register_handlers(self):
        self.events.on(f"{self.__class__.__name__}.tick")(self.onTick)
        self.events.on(f"{self.__class__.__name__}.second")(self.onSecond)
        self.events.on(f"{self.__class__.__name__}.newSection")(self.onNewSection)
        self.events.on(f"{self.__class__.__name__}.newGroup")(self.onNewGroup)
        self.events.on(f"{self.__class__.__name__}.newRound")(self.onNewRound)

    def make_backoff(self, initial_delay=1, max_delay=600) -> BackoffManager:
        """Create a BackoffManager for retryable operations in this plugin."""
        return BackoffManager(initial_delay=initial_delay, max_delay=max_delay)

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
   

