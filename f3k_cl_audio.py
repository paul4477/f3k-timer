import pygame
import logging
import asyncio

from plugin_base import PluginBase
import audio_library

class AudioPlayer(PluginBase):

    def __init__(self, events):
        super().__init__(events)
        self.register_more_handlers()

    def register_more_handlers(self):
        self.events.on("audioplayer.play_integer")(self.play_integer)
        
        self.events.on("audioplayer.play_literally_seconds")(self.play_literally_seconds)
        self.events.on("audioplayer.play_literally_minutes")(self.play_literally_minutes)
        self.events.on("audioplayer.play_literally_second")(self.play_literally_second)
        self.events.on("audioplayer.play_literally_minute")(self.play_literally_minute)
        self.events.on("audioplayer.play_bytes")(self.onPlayBytes)
        self.events.on("audioplayer.play_audio")(self.onPlayAudio)
        
  
    async def onSecond(self, state):
      ## Triggered on every change of second
      ## Logic here to decide what sound to play

      ## Can state look up next and previous round/group/section?
      audio = state.section.audio_times.get(state.slot_time, None)
      if audio:
         self.events.trigger(f"audioplayer.play_audio", audio)
      ## Look at pre-announce for the next section
      
      next_section = state.section.get_next_section()
      if next_section:
        audio = next_section.pre_announce_times.get(-state.slot_time, None)
        self.logger.debug(f"in onSecond. state.slot_time is {state.slot_time}, next_section: {next_section}, audio: {audio}, {next_section.pre_announce_times}")
        if audio:
         self.events.trigger(f"audioplayer.play_audio", audio)

      #if state.slot_time == state.section.start_audio[0]:
      #   self.events.trigger(f"audioplayer.play_audio", state.section.start_audio[1])

      if state.slot_time in state.section.say_seconds:
          seconds = state.slot_time
          self.logger.debug(f"in onSecond. state.slot_time is {state.slot_time}")
          if seconds % 15 == 0 and seconds > 60:
            match (seconds%60):
                case 45 | 30 | 15:
                  self.events.trigger(f"audioplayer.play_integer", int(seconds/60))
                  await asyncio.sleep(0.6)
                  self.events.trigger(f"audioplayer.play_integer", (seconds%60))
                  
                  #self.events.trigger(f"audioplayer.play_literally_seconds")
                case 0:
                  self.events.trigger(f"audioplayer.play_integer", int(seconds/60))
                  await asyncio.sleep(0.5)
                  self.events.trigger(f"audioplayer.play_literally_minutes")              
          
          match seconds:
                case 60:
                  self.events.trigger(f"audioplayer.play_integer", 1)
                  await asyncio.sleep(0.35)
                  self.events.trigger(f"audioplayer.play_literally_minute")    
                case 45:
                  self.events.trigger(f"audioplayer.play_integer", seconds)
                  await asyncio.sleep(0.8)
                  self.events.trigger(f"audioplayer.play_literally_seconds")   
                case 30:
                  self.events.trigger(f"audioplayer.play_integer", seconds)
                  await asyncio.sleep(0.6)
                  self.events.trigger(f"audioplayer.play_literally_seconds")   

                case 0: 
                  self.events.trigger(f"audioplayer.play_integer", 0)

                case x if x < 0:
                  pass
                case x if x <=20 : 
                  self.events.trigger(f"audioplayer.play_integer", seconds)
    
    async def onNewSection(self, state):
        self.logger.debug(f"in onNewSection. state.slot_time is {state.slot_time}")
        #pass
    async def onNewGroup(self, state):
        #if self.enabled():
        pass
    async def onNewRound(self, state):
        #if self.enabled():
        pass  
    
    async def play_integer(self, number):
        try: audio_library.time_sounds[number].play()
        except IndexError:
            self.logger.error(f"AudioPlayer: No sound for integer {number}")

    async def play_literally_seconds(self):
        audio_library.effect_seconds.play()
    async def play_literally_minutes(self):
        audio_library.effect_minutes.play()        
    async def play_literally_second(self):
        audio_library.effect_second.play()
    async def play_literally_minute(self):
        audio_library.effect_minute.play()         
    
    async def onPlayBytes(self, bytesio):
        while pygame.mixer.get_busy():
           await asyncio.sleep(0.2)
        pygame.mixer.music.queue(bytesio, namehint='wav')
        pygame.mixer.music.play()
        while pygame.mixer.get_busy():
           await asyncio.sleep(0.2)

    async def onPlayAudio(self, audio):
        audio.play()


        