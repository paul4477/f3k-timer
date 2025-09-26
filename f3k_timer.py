import asyncio
 
from aiohttp import web
import pygame
import json 
import time
import decimal
import logging
import math
from collections import deque
Decimal = decimal.Decimal

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG, filename='f3k_timer.log')

logger = logging.getLogger(__name__)


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

class State:
    def __init__(self):
        self.round = None #Round(1, 1, 300000, 60000) # default round 1, group 1, 5min window, 1min no-fly
        self.slot_time = 0
        self.end_time = 0

    def start(self):
        if self.round:
            self.slot_time = self.round.windowTime
            self.end_time = time.time() + self.slot_time
        else:
            logger.warning("No round set, cannot start")

    def is_no_fly(self):
        # Determine if current time is within no-fly period
        return False
    def get_dict(self):
        if self.round:
            return {'round': self.round.round_number, 'slot_time': self.slot_time, 'end_time': self.end_time, 'no-fly': self.is_no_fly()}
        else:
            return {'round': '', 'slot_time': self.slot_time, 'end_time': self.end_time, 'no-fly': self.is_no_fly()}
    
class Player:

    def __init__(self, events):
        self.rounds = []
        self.state = State()
        self.events = events
        self.register_handlers()
        #self.mixer = pygame.mixer
        self.running = True
        self.started = False
        self.raw_json = None
        self.last_announced = -1
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pilots = {}

    def is_running(self):
        # or more complex check that queries list of rounds and state object
        return self.running
    
    def register_handlers(self):
        self.events.on("player.data_available")(self.load_data)
        # handlers for control commands from web client(s)
        self.events.on("player.start")(self.start)
        self.events.on("player.pause")(self.pause)
        self.events.on("player.skip_fwd")(self.skip_fwd)
        self.events.on("player.skip_back")(self.skip_back)   
        self.events.on("player.skip_previous")(self.skip_previous)
        self.events.on("player.skip_next")(self.skip_next)
        self.events.on("player.goto")(self.goto)
        self.events.on("player.stop")(self.stop)
        self.events.on("player.quit")(self.quit)
        
    async def load_data(self, raw_json):
        
        self.raw_json = raw_json
        import f3k_cl_round
        self.rounds = f3k_cl_round.make_rounds(raw_json)
        self.logger.info(f"Loaded {len(self.rounds)} rounds from event data")

        self.pilots = self._set_pilots(raw_json)
        self.logger.info(f"Loaded {len(self.pilots)} pilots from event data")
        self.logger.debug(f"Pilots: {self.pilots}")
        
        if len(self.rounds) > 0:
            self.state.round = self.rounds[0]
            self.state.slot_time = self.state.round.windowTime
            self.state.end_time = None #time.time() + self.state.round.windowTime
            self.logger.info(f"Set initial state to round {self.state.round}, window: {self.state.round.windowTime}s")

    async def start(self):
        
        if not self.started:
            self.started = True
            self.state.start()
            
            #self.events.trigger(f"audioplayer.play_minutes_and_seconds", self.state.slot_time)

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
    async def goto(self, round=1, group=1):
        await self.stop()
        try: 
            self.state.round = self.rounds[round-1]
            self.state.slot_time = self.state.round.windowTime
            self.state.end_time = None
        except IndexError:
            self.logger.error(f"Invalid round in goto: {round}")
    async def quit(self):
        self.running = False
    async def stop(self):
        self.logger.info("Stopping player")
        self.started = False        
        self.state = State()
    def _set_pilots(self, raw_json):
        pilots = {}
        for pilot in raw_json['event']['pilots']:
            pilots[int(pilot['pilot_id'])] = pilot['pilot_first_name'] + " " + pilot['pilot_last_name']
        return pilots
    async def update(self):
        
        # calculate new state. 

        ### Fire play sound event on specific times

        now = time.time()
        #self.state.update_now(time.time())
        #if self.state.has_ended():
            #self.state.sections


        #self.logger.debug(f"Player update, now {now}, end_time {self.state.end_time}, slot_time {self.state.end_time - now}, started {self.started}")
        if self.started: 
            self.state.slot_time = math.ceil(max(0, self.state.end_time - now) if self.state.end_time else 0)
            if self.last_announced != self.state.slot_time:
                self.events.trigger(f"audioplayer.play_minutes_and_seconds", self.state.slot_time)
                self.last_announced = self.state.slot_time
        if self.state.end_time and now >= self.state.end_time:
            self.state.end_time = None
            self.state.slot_time = 0
            self.started = False
            #self.mixer.play(pygame.mixer.Sound('sounds/horn.wav'))
            self.logger.info(f"End of round {self.state.round.round_number} window")

import f3k_web
import f3k_sounds

async def main():
    
    web_server = f3k_web.WebFrontend(events)
    await web_server.startup()
    audio_player = f3k_sounds.AudioPlayer(events)
    player = Player(events)
    
    #data = json.load(open('test_data.json'))
    #import f3k_cl_round
    #player.rounds = f3k_cl_round.make_rounds(data)

    clock = Clock()
    TIMEREVENT = pygame.event.custom_type()
    pygame.time.set_timer(TIMEREVENT, 1000) 
    
    while player.is_running():
                       
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == TIMEREVENT:
                fps = await clock.get_fps()
                logger.info(f"fps: {fps:.1f}")
        
                    

        await player.update()
        #await announcer.update(player.state) # instead have this triggered by events from player?
        #logger.debug(f"web_server.update")
        await web_server.update(player.state)
        ## Pass state to all plugins to allow them to update
        ## Or use events triggered from player.update() to notify plugins of changes (on each whole second for example)
        #for plugin in plugins:
        #    await plugin.update(player.state)

        # limit to x fps
        await clock.tick(24)
 
 
if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()
