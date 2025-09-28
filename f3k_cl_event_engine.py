class Clock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
        self.next_tick = None
        self.logger = logging.getLogger(self.__class__.__name__)    
        self.recent_delays = deque([0]*100)
        
    async def get_fps(self):

        return 1 / (sum(self.recent_delays) / len(self.recent_delays))
 
    async def tick(self, fps=0):
        if fps <= 0:
            return

        frame_duration = (1.0 / fps) * 1000  # ms per frame
        now = self.time_func()
        next_tick = getattr(self, "next_tick", None)
        if next_tick is None:
            next_tick = now + frame_duration
        else:
            next_tick += frame_duration

        delay = (next_tick - now) / 1000
        if delay < 0:
            delay = 0

        self.recent_delays.pop()
        self.recent_delays.appendleft(delay)
        await asyncio.sleep(delay)
        self.next_tick = next_tick
        self.last_tick = next_tick
 
 
class EventEngine:
    def __init__(self):
        self.listeners = {}
        self.logger = logging.getLogger(self.__class__.__name__)
 
    def on(self, event):
        if event not in self.listeners:
            self.listeners[event] = []
 
        def wrapper(func, *args):
            self.listeners[event].append(func)
            return func
 
        return wrapper
 
    # this function is purposefully not async
    # code calling this will do so in a "fire-and-forget" manner, and shouldn't be slowed down by needing to await a result
    def trigger(self, event, *args, **kwargs):
        asyncio.create_task(self.async_trigger(event, *args, **kwargs))
        if not "tick" in event: self.logger.debug(f"Firing: {event}")
        
 
    # whatever gets triggered is just added to the current asyncio event loop, which we then trust to run eventually
    async def async_trigger(self, event, *args, **kwargs):
        if event in self.listeners:
            import inspect
            handlers = []
            for func in self.listeners[event]:
                if inspect.iscoroutinefunction(func):
                    handlers.append(func(*args, **kwargs))
                else:
                    async def wrapper(f, *a, **kw):
                        return f(*a, **kw)
                    handlers.append(wrapper(func, *args, **kwargs))
 
            # schedule all listeners to run
            return await asyncio.gather(*handlers)
  