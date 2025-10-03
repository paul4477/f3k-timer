import logging
import asyncio

import wave
from io import BytesIO

from piper import PiperVoice, SynthesisConfig

syn_config = SynthesisConfig(
    volume=1,  # half as loud
    length_scale=1.2,  # twice as slow
    noise_scale=0.2,  # more audio variation
    noise_w_scale=0,  # more speaking variation
    normalize_audio=True, # use raw audio from voice
)
#voice = PiperVoice.load('en_GB-northern_english_male-medium.onnx',
#          config_path='en_GB-northern_english_male-medium.onnx.json')

class Voice:
        def __init__(self, voice_name, config):
              self.voice_name = voice_name
              self.syn_config = config
              self._voice = PiperVoice.load(f'{voice_name}.onnx', config_path=f'{voice_name}.onnx.json')

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

#voice_name = 'en_GB-northern_english_male-medium'
voice_name = 'en_US-lessac-medium'

voice = Voice(voice_name, syn_config)