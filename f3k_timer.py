import asyncio
 
from aiohttp import web
import pygame
import json 
import time
import decimal
import logging
Decimal = decimal.Decimal

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG, filename='f3k_timer.log')

logger = logging.getLogger(__name__)


class Clock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
 
    async def get_fps(self):
        delta = self.time_func() - self.last_tick
        if delta == 0:
            return 0.0  # or float('inf') if you prefer
        return 1000.0 / delta
    
    async def tick(self, fps=0):
        if 0 >= fps:
            return
 
        end_time = (1.0 / fps) * 1000
        current = self.time_func()
        time_diff = current - self.last_tick
        delay = (end_time - time_diff) / 1000
 
        self.last_tick = current
        if delay < 0:
            delay = 0
 
        await asyncio.sleep(delay)
 
 
class EventEngine:
    def __init__(self):
        self.listeners = {}
 
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
 
 
events = EventEngine()

class Round:
    def __init__(self, number, group_number, windowTime, noFlyTime):
        self.number = number
        self.group_number = group_number
        self.windowTime = windowTime  # in milliseconds
        self.noFlyTime = noFlyTime    # in milliseconds
class State:
    def __init__(self):
        self.round = Round(1,1, 300000, 60000) # default round 1, group 1, 5min window, 1min no-fly
        self.slot_time = 0
        self.end_time = 0

    def is_no_fly(self):
        # Determine if current time is within no-fly period
        return False
    
class Player:

    def __init__(self):
        self.rounds = []
        self.state = State()
        self.register_handlers()
        self.mixer = pygame.mixer.Channel(0)
        self.running = True

 
    def register_handlers(self):
        # handlers for control commands from web client(s)
        events.on("player.start")(self.start)
        events.on("player.pause")(self.pause)
        events.on("player.skip_fwd")(self.skip_fwd)
        events.on("player.skip_back")(self.skip_back)   
        events.on("player.skip_previous")(self.skip_previous)
        events.on("player.skip_next")(self.skip_next)
        events.on("player.goto")(self.goto)
        events.on("player.quit")(self.quit)
        
    async def start(self):
        pass
    async def pause(self):
        pass
    async def skip_fwd(self, seconds):
        pass
    async def skip_back(self, seconds):
        pass
    async def skip_previous(self):
        pass
    async def skip_next(self):
        pass
    async def goto(self, round, group):
        pass
    async def quit(self):
        self.running = False
    async def update(self):
        # calculate new times etc??
        self.state.end_time = time.time() + 600
        #for player in self.players:
        #    await player.update(window)
 

import f3k_web

async def main():
    
    
    web_server = f3k_web.WebFrontend(events)
    await web_server.startup()
 
    player = Player()
   
    clock = Clock()
    TIMEREVENT = pygame.event.custom_type()
    pygame.time.set_timer(TIMEREVENT, 15000) 
    
    while player.running:
                       
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == TIMEREVENT:
                fps = await clock.get_fps()
                logger.info(f"fps: {fps:.1f}")
        
                    

        await player.update()
        #await announcer.update(player.state) # instead have this triggered by events from player?
        await web_server.update(player.state)
        ## Pass state to all plugins to allow them to update
        #for plugin in plugins:
        #    await plugin.update(player.state)

        # limit to x fps
        await clock.tick(4)
 
 
if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()