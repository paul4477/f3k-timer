import sys
import wave
import os.path
sys.path.insert(0, "../../")

from piper.voice import PiperVoice,SynthesisConfig

syn_config = SynthesisConfig(
    volume=1,  
    length_scale=1.2,  
    noise_scale=0.2,  
    noise_w_scale=0,  
    normalize_audio=True, 
)

def generate_sound_file(filename, text_to_speak, voice):
  full_dir = os.path.join(language_dir, voice_dir)
  print (os.path.join(full_dir, filename)+".wav <== "+text_to_speak)
  if not os.path.exists(full_dir):
    os.makedirs(full_dir, exist_ok=True)
  with wave.open(os.path.join(full_dir, filename+".wav"), "wb") as wav_file:
    voice.synthesize_wav(text_to_speak, wav_file, syn_config=syn_config)

other_announcements = {
  'minute0': 'minute',
  'minute1': 'minutes',
  'second0': 'second',
  'second1': 'seconds',

  'vx_prep_starting': "Preparation time starting.",
  'vx_prep_start': "Preparation time started.",
  'vx_group_sep': "Group separation time.",

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
  "vx_round": "Round: ",
  "vx_group": "Group: ",

}

import argparse
def get_args():
    parser = argparse.ArgumentParser(description="Command line utility for generating langauage audio.")
    parser.add_argument(
        "--voice-file",
        default="en_US-lessac-medium",
        help="Voice (as downloaded with Piper module). Default: en_US-lessac-medium"
    )
    args = parser.parse_args()
    args.voice_path=os.path.join("..","..",f"{args.voice_file}.onnx")

    if not os.path.isfile(args.voice_path):
        print(f"Error: Voice file 'f3k-timer/{args.voice_file}.onnx' does not exist.\n"\
              "This should have been downloaded as part of running setup.sh.\n"\
                f"Use 'python -m piper.download_voices {args.voice_file}' to download.")
        return None

    try:
        args.voice = PiperVoice.load(args.voice_path)
    except Exception as e:
        print(f"Error creating voice object: {e}")
        return None

    return args

if __name__ == "__main__":
  args = get_args()
  if not args: sys.exit(1)

  language_dir = args.voice_file.split('_')[0]
  voice_dir = args.voice_file[3:]

  # Generate task descriptions
  from task_data import f3k_task_timing_data
  for item in f3k_task_timing_data:
    generate_sound_file(item, f3k_task_timing_data[item]['description'], args.voice)

  # Generate integers used for spoken times
  time_sounds = list(range(21)) + [30,45]
  for t in time_sounds:
    generate_sound_file(f"{t:04d}", str(t), args.voice)

  # Other round announcements etc
  for item in other_announcements:
    generate_sound_file(item, other_announcements[item], args.voice)
