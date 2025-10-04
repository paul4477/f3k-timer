import logging
import asyncio
import os
import wave
import pygame
from io import BytesIO

from piper import PiperVoice, SynthesisConfig

syn_config = SynthesisConfig(
    volume=1,  # half as loud
    length_scale=1.2,  # twice as slow
    noise_scale=0.2,  # more audio variation
    noise_w_scale=0,  # more speaking variation
    normalize_audio=True, # use raw audio from voice
)

class Voice:
        def __init__(self, voice_name, events, config=syn_config):
              self.logger = logging.getLogger(self.__class__.__name__)
              self.voice_name = voice_name
              self.syn_config = config
              self.events = events
              
              self._voice = PiperVoice.load(os.path.join("assets", "voice_data",f'{voice_name}.onnx'),
                                             config_path=os.path.join("assets", "voice_data",f'{voice_name}.onnx.json'))
              self.register_handlers()

        def register_handlers(self):
            self.events.on("rtvoice.generate_and_store_sound")(self.generate_and_store_sound)

        async def generate_and_store_sound(self, text_to_speech, group_obj, paragraph_silence=1.2):
              silence_int16_bytes = bytes(
                    int(self._voice.config.sample_rate * paragraph_silence * 2)
                    )
              wav_file = BytesIO()
              self.logger.debug("Received gernerate_and_store event")
              first = True
              with wave.open(wav_file, "wb") as wf:
                for sentance in text_to_speech.split("\n"):
                  if first: 
                      self._voice.synthesize_wav(sentance, wf, self.syn_config)
                      first = False
                  else: 
                       for data in self._voice.synthesize(sentance):
                            wf.writeframes(data.audio_int16_bytes)
                  wf.writeframes(silence_int16_bytes)
              wav_file.seek(0)
              self.logger.debug(f"Completed generation: {wav_file}, setting on {group_obj}.")
              #await asyncio.sleep(20) # simulate slow update
              group_obj.announce_sound = pygame.mixer.Sound(wav_file)



        def generate_audio_bytes(self, text_to_speech, paragraph_silence=1.2):
              silence_int16_bytes = bytes(
                    int(self._voice.config.sample_rate * paragraph_silence * 2)
                    )
              wav_file = BytesIO()
              first = True
              with wave.open(wav_file, "wb") as wf:
                for sentance in text_to_speech.split("\n"):
                  if first: 
                      self._voice.synthesize_wav(sentance, wf, self.syn_config)
                      first = False
                  else: 
                       for data in self._voice.synthesize(sentance):
                            wf.writeframes(data.audio_int16_bytes)
                  wf.writeframes(silence_int16_bytes)
              wav_file.seek(0)
              return wav_file
