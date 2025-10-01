import sys
import wave
from piper.voice import PiperVoice,SynthesisConfig
sys.path.insert(0, "../../")
#from f3k_cl_competition import f3k_task_timing_data

voice_file = "en_GB-northern_english_male-medium"

#voice = PiperVoice.load("../../en_US-lessac-medium.onnx")
voice = PiperVoice.load(f"../../{voice_file}.onnx")

syn_config = SynthesisConfig(
    volume=1,  # half as loud
    length_scale=1.2,  # twice as slow
    noise_scale=0.2,  # more audio variation
    noise_w_scale=0,  # more speaking variation
    normalize_audio=True, # use raw audio from voice
)

language_dir = voice_file.split('_')[0]
voice_dir = voice_file[3:]
import os.path

def generate_sound_file(filename, text_to_speak):
  full_dir = os.path.join(language_dir, voice_dir)
  if not os.path.exists(full_dir):
    os.makedirs(full_dir, exist_ok=True)
  with wave.open(os.path.join(full_dir, filename+".wav"), "wb") as wav_file:
    voice.synthesize_wav(text_to_speak, wav_file, syn_config=syn_config)




#for item in f3k_task_timing_data:
#  print (item)
#  generate_sound_file(item, f3k_task_timing_data[item]['description'])


## Announce pilots and task

## Prep
## Announce prep started
## Annonunce task name
## Times
## If test:
  ## Announce 1min to test
  ## Announce 30s to test
  ## Announce 20s to test
  ## normal beeps
## else
  ## Announce 1min to no fly
  
## Announce 30s to no fly
## Announce 20s to no fly
## beep down
## Announce no fly - pilots can't fly
## 30s to working time
## 20s to working time
## normal beep
## announce 10min working time (do we need a different file for each time slot?) 3m 7m 10m 15m
## normal beep
## 30s landing window
## Group separation time


## Prep needs to be special to have pre-amble with pilots and taks announcement


other_announcements = {
  'vx_prep_starting': "Preparation time starting.",
  'vx_prep_start': "Preparation time started.",
  'vx_round_sep': "Round separation time.",

  'vx_1m_to_test': "one minute to test time.",
  'vx_30s_to_test': "30 seconds to test time.",
  'vx_20s_to_test': "20 seconds to test time.",
  "vx_test_time": "45 second test time. Pilots may make test flights.",

  'vx_1m_to_no_fly': "one minute to no fly time.",
  'vx_30s_to_no_fly': "30 seconds to no fly time.",
  'vx_20s_to_no_fly': "20 seconds to no fly time.",
  'vx_no_flying': "No Fly window. Pilots may not launch.",

  "vx_1m_to_working_time": "one minute to start of working time",
  "vx_30s_to_working_time": "30 seconds to start of working time",
  "vx_20s_to_working_time": "20 seconds to start of working time",

  "vx_3m_window": "3 minute working window.",
  "vx_7m_window": "7 minute working window.",
  "vx_10m_window": "10 minute working window.",
  "vx_15m_window": "15 minute working window.",

  "vx_30s_landing_window": "30 second landing window",

}

for item in other_announcements:
  print (item)
  generate_sound_file(item, other_announcements[item])


"""Round 1 Group 1

Preparation time of x minutes starts in 5,4,3,2,1,

x minutes remaining in prep time for ROund Y Group ZeroDivisionError
  
599,39:                             tempEntry.spokenText += " . There is no flying allowed during this time.";

600,39:                             tempEntry.spokenTextOnCountdown += " of prep time before flight test window.";
604,39:                             tempEntry.spokenTextOnCountdown += " of prep time before no fly window.";
611,35:                         tempEntry.spokenTextOnCountdown = "before working window of Round " + round.round_number.ToString() + " Group " + group;
619,35:                         tempEntry.spokenTextOnCountdown += ", Flight 1."; # all up?
744,39:                             tempEntry.spokenText = (windowTime / 60).ToString() + " minute window for flight " + loop.ToString() + ".";
641,35:                         tempEntry.spokenText = "45 Second Flight Test Window. Pilots may now make test flights.";
642,35:                         tempEntry.spokenTextOnCountdown = " before no fly window";
668,35:                         tempEntry.spokenText = "1 Minute no fly time before working window of Round " + round.round_number.ToString() + " Group " + group;
669,35:                         tempEntry.spokenTextOnCountdown = "before working window";
674,35:                         tempEntry.spokenText += " . Pilots must not be flying during this final minnit.";
749,39:                             tempEntry.spokenText = (windowTime / 60).ToString() + " minnit working window.";
782,39:                             tempEntry.spokenText = "30 second landing window.";
785,39:                             tempEntry.spokenTextOnCountdown = "in landing window";
825,35:                         tempEntry.spokenText = betweenStringSpoken + " Group Separation Time";
828,35:                         tempEntry.spokenTextOnCountdown = "Left in group separation";
861,31:                     tempEntry.spokenText = betweenStringSpoken + " Round Separation Time";


seconds

append to minute calls (e.g left in group separation time)
Preambnle
each section start text



"""