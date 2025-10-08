import pygame
import logging

from f3k_timer import main_config
## Voice spec - should get from config object

print(main_config)
voice_name = ''.join(main_config.get('voice', 'en_US-lessac-medium').split('_')[1:])
language = main_config.get('voice', 'en_US-lessac-medium').split('_')[0]

## Count sounds
effect_0 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0000.wav')
effect_1 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0001.wav')
effect_2 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0002.wav')
effect_3 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0003.wav')
effect_4 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0004.wav')
effect_5 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0005.wav')
effect_6 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0006.wav')
effect_7 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0007.wav')
effect_8 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0008.wav')
effect_9 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0009.wav')
effect_10 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0010.wav')
effect_11 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0011.wav')
effect_12 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0012.wav')
effect_13 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0013.wav')
effect_14 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0014.wav')

effect_15 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0015.wav')
effect_16 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0016.wav')
effect_17 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0017.wav')
effect_18 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0018.wav')
effect_19 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0019.wav')
effect_20 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0020.wav')
effect_30 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0030.wav')
effect_45 = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/0045.wav')
effect_second = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/second0.wav')
effect_seconds = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/second1.wav')
effect_minute = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/minute0.wav')
effect_minutes = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/minute1.wav')

from task_data import f3k_task_timing_data

# Task descriptions
task_audio = {}
for item in f3k_task_timing_data:
  task_audio[item] = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/{item}.wav')

# Other spoken strings
language_strings = [
"vx_prep_starting",
"vx_prep_start",
"vx_group_sep",

"vx_round",
"vx_group",

"vx_1m_to_test",
"vx_30s_to_test",
"vx_20s_to_test",
"vx_test_time",

"vx_1m_to_no_fly",
"vx_30s_to_no_fly",
"vx_20s_to_no_fly",
"vx_no_flying",

"vx_3m_window",
"vx_7m_window",
"vx_10m_window",
"vx_15m_window",

"vx_1m_to_working_time",
"vx_30s_to_working_time",
"vx_20s_to_working_time",
"vx_30s_landing_window",
]

language_audio = {}
for l in language_strings:
   language_audio[l] = pygame.mixer.Sound(f'assets/sounds/{language}/{voice_name}/{l}.wav') 

effect_countdown_beeps = pygame.mixer.Sound('assets/sounds/4321_normal.wav')
effect_countdown_beeps_3s = pygame.mixer.Sound('assets/sounds/4321_3s.wav')
effect_countdown_beeps_end = pygame.mixer.Sound('assets/sounds/4321_short_down.wav')

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
