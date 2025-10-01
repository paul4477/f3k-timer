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

        def generate_audio_bytes(self, text_to_speech):
              wav_file = BytesIO()
              with wave.open(wav_file, "wb") as wf:
                    self._voice.synthesize_wav(text_to_speech, wf, self.syn_config)
              wav_file.seek(0)
              return wav_file

voice_name = 'en_GB-northern_english_male-medium'

voice = Voice(voice_name, syn_config)