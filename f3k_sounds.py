import pygame
import logging
import asyncio

pygame.mixer.init(frequency=44100, size=-16,channels=1)

pygame.mixer.music.load('assets/sounds/countdown.mp3')

effect_0 = pygame.mixer.Sound('assets/sounds/en/0000.wav')
effect_1 = pygame.mixer.Sound('assets/sounds/en/0001.wav')
effect_2 = pygame.mixer.Sound('assets/sounds/en/0002.wav')
effect_3 = pygame.mixer.Sound('assets/sounds/en/0003.wav')
effect_4 = pygame.mixer.Sound('assets/sounds/en/0004.wav')
effect_5 = pygame.mixer.Sound('assets/sounds/en/0005.wav')
effect_6 = pygame.mixer.Sound('assets/sounds/en/0006.wav')
effect_7 = pygame.mixer.Sound('assets/sounds/en/0007.wav')
effect_8 = pygame.mixer.Sound('assets/sounds/en/0008.wav')
effect_9 = pygame.mixer.Sound('assets/sounds/en/0009.wav')
effect_10 = pygame.mixer.Sound('assets/sounds/en/0010.wav')
effect_11 = pygame.mixer.Sound('assets/sounds/en/0011.wav')
effect_12 = pygame.mixer.Sound('assets/sounds/en/0012.wav')
effect_13 = pygame.mixer.Sound('assets/sounds/en/0013.wav')
effect_14 = pygame.mixer.Sound('assets/sounds/en/0014.wav')

effect_15 = pygame.mixer.Sound('assets/sounds/en/0015.wav')
effect_16 = pygame.mixer.Sound('assets/sounds/en/0016.wav')
effect_17 = pygame.mixer.Sound('assets/sounds/en/0017.wav')
effect_18 = pygame.mixer.Sound('assets/sounds/en/0018.wav')
effect_19 = pygame.mixer.Sound('assets/sounds/en/0019.wav')
effect_20 = pygame.mixer.Sound('assets/sounds/en/0020.wav')
effect_30 = pygame.mixer.Sound('assets/sounds/en/0030.wav')
effect_45 = pygame.mixer.Sound('assets/sounds/en/0045.wav')
effect_second = pygame.mixer.Sound('assets/sounds/en/second0.wav')
effect_seconds = pygame.mixer.Sound('assets/sounds/en/second1.wav')
effect_minute = pygame.mixer.Sound('assets/sounds/en/minute0.wav')
effect_minutes = pygame.mixer.Sound('assets/sounds/en/minute1.wav')

effect_horn = pygame.mixer.Sound('assets/sounds/chord.wav')

time_sounds ={0: effect_0,
                1: effect_1,
                2: effect_2,
                3: effect_3,
                4: effect_4,
                5: effect_5,
                6: effect_6,
                7: effect_7,
                8: effect_8,
                9: effect_9,
                10: effect_10,
                11: effect_11,
                12: effect_12,
                13: effect_13,
                14: effect_14,
                15: effect_15,
                16: effect_16,
                17: effect_17,
                18: effect_18,
                19: effect_19,
                20: effect_20,
                30: effect_30,
                45: effect_45,
                }

class AudioPlayer:

    def __init__(self, events):
        #self.mixer = pygame.mixer
        self.events = events
        self.logger = logging.getLogger(self.__class__.__name__)
        self.register_handlers()

    def register_handlers(self):
        self.events.on("audioplayer.play_integer")(self.play_integer)
        self.events.on("audioplayer.play_minutes_and_seconds")(self.play_minutes_and_seconds)
        self.events.on("audioplayer.play_literally_seconds")(self.play_literally_seconds)
        self.events.on("audioplayer.play_literally_minutes")(self.play_literally_minutes)
        self.events.on("audioplayer.play_literally_second")(self.play_literally_second)
        self.events.on("audioplayer.play_literally_minute")(self.play_literally_minute)

        # handlers for control commands from web client(s)
        #events.on("player.start")(self.start)
        #events.on("player.pause")(self.pause)
        #events.on("player.skip_fwd")(self.skip_fwd)
        #events.on("player.skip_back")(self.skip_back)   
        #events.on("player.skip_previous")(self.skip_previous)
        #events.on("player.skip_next")(self.skip_next)
        #events.on("player.goto")(self.goto)
        #events.on("player.stop")(self.stop)
        #events.on("player.quit")(self.quit)

    async def play_minutes_and_seconds(self, seconds):
              ## Play sounds
      self.logger.debug(f"AudioPlayer: play_minutes_and_seconds({seconds}, mod 15: {seconds%15} )")

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

    async def play_integer(self, number):
        try: time_sounds[number].play()
        except IndexError:
            self.logger.error(f"AudioPlayer: No sound for integer {number}")

    async def play_literally_seconds(self):
        effect_seconds.play()
    async def play_literally_minutes(self):
        effect_minutes.play()        
    async def play_literally_second(self):
        effect_second.play()
    async def play_literally_minute(self):
        effect_minute.play()               
        