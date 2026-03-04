import logging
from logging import config
import time
import math
import asyncio 
import pygame
import f3k_cl_competition

class Pilot:
    def __init__(self, pilot_json):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.id = pilot_json['pilot_id']
        self.name = pilot_json['pilot_first_name'] + " " + pilot_json['pilot_last_name']
        self.logger.debug(f"Loading pilot {pilot_json['pilot_id']} {pilot_json['pilot_last_name']}")

    def __repr__(self):
        return f"Pilot: {self.name} ({self.id})"
    
    def get_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }
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
        self.time_digits = "0000"

    def __repr__(self):
        return f"State(round={self.round}, group={self.group}, section={self.section}, slot_time={self.slot_time}, end_time={self.end_time}, no-fly={self.is_no_fly()})"

    def start(self):
        self.iter_round = iter(self.player.rounds)
        self.next_round()

    def goto(self, round=1, group=1):
        # Reset iterators and step to desired round and group
        # Don't use the next_x functions to avoid firing events
        self.iter_round = iter(self.player.rounds)
        self.round = next(self.iter_round)
        while self.round.round_number != round:
            self.logger.info(f"Advancing round: round {self.round}")
            self.round = next(self.iter_round)
            
        self.iter_group = iter(self.round)
        self.group = next(self.iter_group)  
        while self.group.group_number < group:
            self.logger.info(f"Advancing group: group {self.group}")
            self.group = next(self.iter_group)  
            
        self.iter_section = iter(self.group)
        self.next_section() # This will fire events for the section start
        


    def resume(self):
        self.end_time = time.time() + self.slot_time

    def is_no_fly(self):
        # Determine if current time is within no-fly period
        if self.section:
            return self.section.is_no_fly()
        else:
            return True
    def next(self):
        if not self.next_section():
            if not self.next_group():
                if not self.next_round():
                    ## End of event
                    self.logger.info("End of event")
                    self.player.running = True # keep program alive
                    self.player.started = False
                    return False
                else:
                    self.logger.info(f"Start of round {self.round.round_number} window")
                    return True
            else:
                self.logger.info(f"Start of group in round {self.round.round_number}")
                return True
        else:
            return True
             


    def next_round(self):
        try:
            self.round = next(self.iter_round)
            self.logger.info(f"NEXT_ROUND: Round: {self.round}")
            for consumer in self.player.eventConsumers:
                self.player.events.trigger(f"{consumer.__class__.__name__}.newRound", self)


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
            for consumer in self.player.eventConsumers:
                self.player.events.trigger(f"{consumer.__class__.__name__}.newGroup", self)
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
            for consumer in self.player.eventConsumers:
                self.player.events.trigger(f"{consumer.__class__.__name__}.newSection", self)  
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
                    'no_fly': self.is_no_fly(),
                    'time_s': self.time_str if (self.slot_time or self.slot_time == 0) else '--:--',
                    'r_num': self.round.round_number if self.round else '-',
                    'g_let': self.group.group_letter if self.group else '-',
                    'f_num': self.section.get_flight_number() if self.section else '1',
                    'sect': self.section.get_description(),
                    'task_name': self.round.task_name if self.round else '--------',}
        else:
            return {
                    'slot_time': 0, 
                    'no_fly': False,
                    'time_s': time.strftime("%H:%M", time.localtime(time.time())),
                    'r_num': '-',
                    'g_let': '-',
                    'f_num': '-',
                    'sect': 'Actual Time HH:MM',
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
        self.event_id = None
        self.eventConsumers = []
        self.event_config = None

    def __iter__(self):
        return (rnd for rnd in self.rounds)
    
    def init_pre_comp(self):
        self.state.section = f3k_cl_competition.ShowTimeSection(0, None, None, 0, event_config=self.event_config)
        
    def is_running(self):
        # or more complex check that queries list of rounds and state object
        return self.running
    
    def set_config(self, event_config):
        self.event_config = event_config
        self.logger.info(f"Player configuration: {self.event_config}")

        self.event_config.setdefault('prep_time', 300)
        self.event_config.setdefault('use_strict_test_time', False)
        self.event_config.setdefault('no_fly_time', 60)
        self.event_config.setdefault('land_time', 30)
        self.event_config.setdefault('group_separation_time', 120)
        self.event_config.setdefault('competition_start_time', 600)  # 10:00 AM in minutes from midnight
        self.logger.info(f"Player configuration after defaults: {self.event_config}")

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
        self.events.on("player.reset")(self.reset)
        self.events.on("player.set_event_config")(self.update_event_config)
        
    async def load_data(self, raw_json):
        self.event_id = raw_json['event']['event_id']
        self.rounds = f3k_cl_competition.make_rounds(raw_json, self.event_config)
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
            self.state = State(self)
            self.state.start()

    async def reset(self):
        self.logger.info("Resetting event player")
        self.rounds = []
        self.state = State(self)
        self.started = False
        self.raw_json = None
        self.last_announced = 1
        self.pilots = {}
        self.event_id = None        
        self.init_pre_comp()

    async def pause(self):
        if self.started: self.started = False
        else: 
            self.started = True
            self.state.resume()
    async def skip_fwd(self, seconds=10):
        if self.state.slot_time:
            self.state.slot_time -= seconds
            self.state.end_time = time.time() + self.state.slot_time
    async def skip_back(self, seconds=10):
        ## Protect against exceeding original section length
        if self.state.slot_time:
            self.state.slot_time = min(self.state.section.sectionTime, self.state.slot_time + seconds)
            self.state.end_time = time.time() + self.state.slot_time
    async def skip_previous(self):
        if self.state.slot_time:
            self.state.slot_time = self.state.section.sectionTime
            self.state.end_time = time.time() + self.state.slot_time
    async def skip_next(self):
        self.state.next()
              

    async def goto(self, round=2, group=2):
        #await self.stop()
        self.logger.info(f"Going to round {round}, group {group}")
        self.state.goto(round, group)

    async def update_event_config(self, config_updates: dict):
        allowed = {'prep_time', 'group_separation_time', 'use_strict_test_time', 'competition_start_time'}
        for key in allowed:
            if key in config_updates:
                if key == 'use_strict_test_time':
                    self.event_config[key] = bool(config_updates[key])
                else:
                    self.event_config[key] = int(config_updates[key])
        self.logger.info(f"Event config updated: {self.event_config}")

    async def quit(self):
        self.running = False
    async def stop(self):
        self.logger.info("Stopping player")
        self.started = False        
        self.state = State(self)
    
    def _set_pilots(self, raw_json):
        pilots = {}
        for pilot in raw_json['event']['pilots']:
            pilots[int(pilot['pilot_id'])] = Pilot(pilot)
            #pilot['pilot_first_name'] + " " + pilot['pilot_last_name']
        return pilots

    def add_event_consumer(self, consumer_instance):
        self.eventConsumers.append(consumer_instance)
        self.logger.info(f"Added plugin: {consumer_instance.__class__.__name__}")

    async def update(self):
        
        if isinstance(self.state.section, f3k_cl_competition.AnnounceSection):
            self.logger.debug(f"In Announce loop {self.state.time_str} {self.state.end_time} {self.state.time_digits} {self.state.group.announce_sound}")
            ## While our annnouncement is not generated, loop - keeping the time the same?
            self.state.time_str = "--:--"
            self.state.time_digits = "0000"
            
            # Audio is not ready, so update consumers and return to outer loop
            for consumer in self.eventConsumers:
                self.events.trigger(f"{consumer.__class__.__name__}.tick", self.state)
            for consumer in self.eventConsumers:
                self.events.trigger(f"{consumer.__class__.__name__}.second", self.state)                
            #await asyncio.sleep(0.1)
            if self.state.group.announce_sound is None and not self.state.group.announce_sound_generating:
                announcement = f"This is Round {self.state.round.round_number}. Group: {self.state.group.group_letter}.\n"
                announcement += "Pilot List.\n"
                announcement += "\n".join(list(self.pilots[id].name for id in self.state.group.pilots))

                self.state.group.announce_sound_generating = True
                # Sets group.announce_sound to generated wav
                self.events.trigger("rtvoice.generate_and_store_sound", announcement, self.state.group, paragraph_silence=1)

            if not self.state.group.announce_sound is None:
                # Create sound object and trigger playing it
                self.events.trigger("audioplayer.play_audio", self.state.group.announce_sound)

                ## Wait for announcement to complete (halt outer loop)
                await asyncio.sleep(2) # sleep to ensure mixer started
                
                while pygame.mixer.get_busy():
                    #self.logger.debug(f"Mixer busy: {pygame.mixer.get_busy()}")
                    await asyncio.sleep(0.5)

                ## Not sure on timing for this, so skip it for now.
                ## Its not vital
                #self.events.trigger("audioplayer.play_audio", 
                #                pygame.mixer.Sound(
                #                    voice.generate_audio_bytes("Preparation time is beggining now.")
                #                     )
                #                )

                try: self.state.next_section()
                except TypeError: # could have no iterator
                    pass
                return # loop again
            ## Return to outer loop
            return

        now = time.time()
        # Fire generic events for consumers to deal with.
        if self.started and self.state.end_time: 
            # Calculate timings every time around the loop
            self.state.slot_time = math.ceil(max(0, self.state.end_time - now) if self.state.end_time else 0)
            self.state.time_str = f"{int(self.state.slot_time/60):02d}:{self.state.slot_time%60:02d}"
            self.state.time_digits = f"{int(self.state.slot_time/60):02d}{self.state.slot_time%60:02d}"
            
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
                # Make sure only do this once per "new" second.
                self.last_announced = self.state.slot_time

            # This clause will be triggered when our section time has expired
            # and it is therefore the end of that section:
            if now >= self.state.end_time:
                self.logger.info(f"End of section {self.state.section} in group {self.state.group}")   
                # Reset this
                #self.last_announced = None
                self.state.clear_section()

                if not self.state.next():
                            self.logger.info("End of event")
                            self.running = True # keep program alive
                            self.started = False                
        elif isinstance(self.state.section, f3k_cl_competition.ShowTimeSection):
            now_local = time.localtime(time.time())
            current_minute_of_day = now_local.tm_hour * 60 + now_local.tm_min
            last_announced = getattr(self.state.section, 'last_announced_minute', -1)

            # Only generate an announcement at 5-minute boundaries (e.g. :00, :05, :10...)
            # and only once per interval
            if (current_minute_of_day % 5 == 0) and (last_announced != current_minute_of_day):
                if self.state.section.announce_sound is None and not self.state.section.announce_sound_generating:
                    competition_start = self.event_config.get('competition_start_time', 600)
                    mins_until_start = competition_start - current_minute_of_day
                    if mins_until_start > 0:
                        if mins_until_start == 1:
                            announcement = "1 minute before competition begins."
                        else:
                            announcement = f"{mins_until_start} minutes before competition begins."
                    elif mins_until_start == 0:
                        if self.rounds:
                            await self.start()
                            return
                        else:
                            announcement = "Competition could not start as data is not loaded."
                    else:
                        announcement = f"Competition start time is set in the past. It was {abs(mins_until_start)} minutes ago based on current system time. Please check your configuration."
                        
                    self.state.section.announce_sound_generating = True
                    # Sets section.announce_sound to generated wav
                    self.events.trigger("rtvoice.generate_and_store_sound", announcement, self.state.section, paragraph_silence=1)

            if self.state.section.announce_sound is not None:
                # Create sound object and trigger playing it
                self.events.trigger("audioplayer.play_audio", self.state.section.announce_sound)

                ## Wait for announcement to complete (halt outer loop)
                await asyncio.sleep(2) # sleep to ensure mixer started

                while pygame.mixer.get_busy():
                    await asyncio.sleep(0.5)
                self.state.section.announce_sound = None
                self.state.section.announce_sound_generating = False
                self.state.section.last_announced_minute = current_minute_of_day

            await asyncio.sleep(1)
            for consumer in self.eventConsumers:
                self.events.trigger(f"{consumer.__class__.__name__}.second", self.state)
                self.events.trigger(f"{consumer.__class__.__name__}.tick", self.state)




