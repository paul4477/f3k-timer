import logging
import time
import math

class State:
    def __init__(self, player):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.slot_time = 0
        self.end_time = 0
        self.iter_group = None
        self.iter_round = None
        self.iter_section = None
        self.player = player
        self.round = None
        self.group = None
        self.section = None
        self.section_length = 0
        self.time_str = "--:--"

    def __repr__(self):
        return f"State(round={self.round}, group={self.group}, section={self.section}, slot_time={self.slot_time}, end_time={self.end_time}, no-fly={self.is_no_fly()})"

    def start(self, round=1, group=1):
        self.iter_round = iter(self.player.rounds)
        try:
            self.round = next(self.iter_round)
            self.logger.info(f"START: ROUND: {self.round}")
        except StopIteration:
            ## End of event
            self.logger.error("Trying to State.start(), no rounds, event ended")
            return
        
        self.iter_group = iter(self.round)
        try:
            self.group = next(self.iter_group)
            self.logger.info(f"START: GROUP: {self.group}")
        except StopIteration:
            ## End of round
            self.logger.debug(f"No groups in round {self.round}, cannot start")
            return

        self.iter_section = iter(self.group)
        try:
            self.section = next(self.iter_section)
            self.slot_time = self.section.sectionTime
            self.logger.info(f"START: SECTION: {self.section}")
        except StopIteration:
            ## End of group
            self.logger.debug(f"No sections in group {self.round}, cannot start")
            return
        
        self.end_time = time.time() + self.slot_time

    def resume(self):
        self.end_time = time.time() + self.slot_time

    def is_no_fly(self):
        # Determine if current time is within no-fly period
        if self.section:
            return self.section.is_no_fly()
        else:
            return True

    def next_round(self):
        try:
            self.round = next(self.iter_round)
            self.logger.info(f"NEXT_ROUND: Round: {self.round}")
            self.iter_group = iter(self.round)
            self.next_group()
            return True
        except StopIteration:
            ## End of event
            self.logger.info(f"No more rounds, event ended")
            self.slot_time = 0
            self.end_time = 0
            return False

    def next_group(self):
        try:
            self.group = next(self.iter_group)
            self.logger.info(f"NEXT_GROUP: Group: {self.group}")
            self.iter_section = iter(self.group)
            self.next_section()
            return True
        except StopIteration:
            ## End of event
            self.logger.info(f"No more groups in {self.round}")
            self.slot_time = 0
            self.end_time = 0
            return False

    def next_section(self):
        try:
            self.section = next(self.iter_section)
            self.slot_time = self.section.sectionTime
            self.end_time = time.time() + self.slot_time
            self.logger.info(f"NEXT_SECTION: Section: {self.section}")
            return True
        except StopIteration:
            ## End of group
            self.logger.info(f"No more sections in {self.group}")
            self.slot_time = 0
            self.end_time = 0
            return False
        
    def clear_section(self):
        self.slot_time = 0
        self.end_time = 0

    def get_dict(self):
        if self.player.started and (self.section is not None):
            return {
                    'slot_time': self.slot_time, 
                    'end_time': self.end_time, 
                    'no_fly': self.is_no_fly(),
                    'time_str': self.time_str if (self.slot_time or self.slot_time == 0) else '--:--',
                    'round_num': self.round.round_number if self.round else '-',
                    'group_num': self.group.group_number if self.group else '-',
                    'section': self.section.get_description(),
                    'task_name': self.round.task_name if self.round else '--------',}
        else:
            return {
                    'slot_time': 0, 
                    'end_time': 0, 
                    'no_fly': False,
                    'time_str': time.strftime("%H:%M", time.localtime(time.time())),
                    'round_num': '-',
                    'group_num': '-',
                    'section': 'Actual Time HH:MM',
                    'task_name': '--------',}
    
class Player:

    def __init__(self, events):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rounds = []
        self.state = State(self)
        self.events = events
        self.register_handlers()
        #self.mixer = pygame.mixer
        self.running = True
        self.started = False
        self.raw_json = None
        self.last_announced = 1
        
        self.pilots = {}
        self.eventConsumers = []

    def __iter__(self):
        return (rnd for rnd in self.rounds)
    
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
        
        
        import f3k_cl_competition
        self.rounds = f3k_cl_competition.make_rounds(raw_json)
        self.logger.info(f"Loaded {len(self.rounds)} rounds from event data")

        self.pilots = self._set_pilots(raw_json)
        self.logger.info(f"Loaded {len(self.pilots)} pilots from event data")
        self.logger.debug(f"Pilots: {self.pilots}")
        
        if len(self.rounds) > 0:
            self.state.round = self.rounds[0]
            self.state.slot_time = self.state.round.windowTime
            self.state.end_time = None #time.time() + self.state.round.windowTime
            self.logger.info(f"Set initial state to round {self.state.round}, window: {self.state.round.windowTime}s")
        # Store in case we need it later
        self.raw_json = raw_json

    async def start(self):
        
        if not self.started:
            self.started = True
            self.state.start()
            
            #self.events.trigger(f"audioplayer.play_minutes_and_seconds", self.state.slot_time)

    async def pause(self):
        if self.started: self.started = False
        else: 
            self.started = True
            self.state.resume()
    async def skip_fwd(self, seconds):
        if self.state.slot_time:
            self.state.slot_time -= 10
            self.state.end_time = time.time() + self.state.slot_time
    async def skip_back(self, seconds):
        ## Protect against exceeding original section length
        if self.state.slot_time:
            self.state.slot_time = min(self.state.section.sectionTime, self.state.slot_time + 10)
            self.state.end_time = time.time() + self.state.slot_time
    async def skip_previous(self):
        pass
    async def skip_next(self):
        if not self.state.next_section():
            if not self.state.next_group():
                if not self.state.next_round():
                    ## End of event
                    self.logger.info("End of event")
                    self.running = True # keep program alive
                    self.started = False

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
        self.state = State(self)
    
    def _set_pilots(self, raw_json):
        pilots = {}
        for pilot in raw_json['event']['pilots']:
            pilots[int(pilot['pilot_id'])] = pilot['pilot_first_name'] + " " + pilot['pilot_last_name']
        return pilots

    def add_event_consumer(self, consumer_instance):
        self.eventConsumers.append(consumer_instance)
        self.logger.info(f"Added plugin: {consumer_instance.__class__.__name__}")

    async def update(self):
        # calculate new state.

        ### Fire play sound event on specific times
        now = time.time()
        if self.started and self.state.end_time: 
            # Calculate timings every time around the loop
            self.state.slot_time = math.ceil(max(0, self.state.end_time - now) if self.state.end_time else 0)
            self.state.time_str = f"{int(self.state.slot_time/60):02d}:{self.state.slot_time%60:02d}"
            
            # Any consumers who want the more frequent updates can get them here.
            # We fire them all but the listeners may be null if they don't care.
            for consumer in self.eventConsumers:
                self.events.trigger(f"{consumer.__class__.__name__}.tick", self.state)
            
            # Since slot time is an integer, this clause will be triggered every
            # time we pass a second
            if  (self.state.slot_time > 0) and (self.last_announced != self.state.slot_time):
                # Fire "second" events to all consumers
                for consumer in self.eventConsumers:
                    self.logger.debug(f"calling second on {consumer}, time: {self.state.slot_time}, last_announced: {self.last_announced}")
                    self.events.trigger(f"{consumer.__class__.__name__}.second", self.state)
                self.last_announced = self.state.slot_time

        # This clause will be triggered when our section time has expired
        # and it is therefore the end of that section:
        if self.started and self.state.end_time and now >= self.state.end_time:
            self.logger.info(f"End of section {self.state.section} in group {self.state.group}")   
            # Reset this
            #self.last_announced = None
            self.state.clear_section()

            if not self.state.next_section():
                if not self.state.next_group():
                    if not self.state.next_round():
                        ## End of event
                        self.logger.info("End of event")
                        self.running = True # keep program alive
                        self.started = False
                        #self.mixer.play(pygame.mixer.Sound('sounds/horn.wav'))
                        #self.events.trigger(f"audioplayer.play_literally_end_of_event")
                        return
                    else:
                        self.logger.info(f"Start of round {self.state.round.round_number} window")
                        #for consumer in self.eventConsumers:
                         #   self.events.trigger(f"{consumer.__class__.__name__}.newRound", self.state)
                else:
                    self.logger.info(f"Start of group in round {self.state.round.round_number}")
                    #for consumer in self.eventConsumers:
                     #   self.events.trigger(f"{consumer.__class__.__name__}.newGroup", self.state)
           #else:
               # for consumer in self.eventConsumers:
                 #   self.events.trigger(f"{consumer.__class__.__name__}.newSection", self.state)
#