##
## Basic code taken from:
## https://stackoverflow.com/questions/33879523/python-how-can-i-generate-a-wav-file-with-beeps
##

# Use https://onlinetonegenerator.com/multiple-tone-generator.html
# to experiment with mixing waves

try:
    import sys
    import os
    import argparse
    import struct
    import wave
    import yaml
    from scipy import signal as sg
    import numpy as np
    import scipy.io.wavfile
    
except ImportError as err:
    print("\nFailed to import required modules.\n" \
            "Please run setup.sh to create the required virtual environment.\n")
    raise err
    sys.exit(1)

class BeepGenerator:
    def __init__(self):
        # Audio will contain a long list of samples (i.e. floating point numbers describing the
        # waveform).  If you were working with a very long sound you'd want to stream this to
        # disk instead of buffering it all in memory list this.  But most sounds will fit in 
        # memory.
        self.audio = []
        self.sample_rate = 44100.0

    def append_silence(self, duration_milliseconds=500):
        """
        Adding silence is easy - we add zeros to the end of our array
        """
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        for x in range(int(num_samples)):
            self.audio.append(0.0)

        return

    def append_sinewave(
            self,
            freq=440.0,
            duration_milliseconds=500,
            volume=1.0):
        """
        The sine wave generated here is the standard beep.  If you want something
        more aggressive you could try a square or saw tooth waveform.   Though there
        are some rather complicated issues with making high quality square and
        sawtooth waves... which we won't address here :) 
        """

        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        x = np.arange(int(num_samples))

        sine_wave = volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))

        self.audio.extend(list(sine_wave))
        return

    def append_sinewaves(
            self,
            freqs=[440.0],
            duration_milliseconds=500,
            volumes=[1.0]):
        """
        The sine wave generated here is the standard beep.  If you want something
        more aggressive you could try a square or saw tooth waveform.   Though there
        are some rather complicated issues with making high quality square and
        sawtooth waves... which we won't address here :)
        len(freqs) must be the same as len(volumes)
        """

        volumes = list(np.array(volumes)/sum(volumes))
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)
        x = np.arange(int(num_samples))

        first_it = True
        for volume, freq in zip(volumes, freqs):
            print(freq)
            if first_it:
                sine_wave = volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))
                first_it = False
            else:
                sine_wave += volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))

        self.audio.extend(list(sine_wave))
        return

    def save_wav(self, file_name):
        # Open up a wav file
        # wav params

        # 44100 is the industry standard sample rate - CD quality.  If you need to
        # save on file size you can adjust it downwards. The standard for low quality
        # is 8000 or 8kHz.

        # WAV files here are using short, 16 bit, signed integers for the 
        # sample size.  So we multiply the floating point data we have by 32767, the
        # maximum value for a short integer.  NOTE: It is theoretically possible to
        # use the floating point -1.0 to 1.0 data directly in a WAV file but not
        # obvious how to do that using the wave module in python.
        self.audio = np.array(self.audio).astype(np.float32)
        try: scipy.io.wavfile.write(file_name, int(self.sample_rate), np.array(self.audio))
        except PermissionError:
            print(f"\nFailed to open file: {file_name} for writing.\n" \
            "Do you have the file open in another application?\n\n")
            sys.exit(1)
        print (f"    Wrote: {file_name}")
        return

    def append_squarewave(
        self,
        freq=440.0, 
        duration_milliseconds=500, 
        volume=1.0):

        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        x = np.arange(int(num_samples))

        sq_wave = volume * sg.square(2 * np.pi * freq * ( x / self.sample_rate ))

        self.audio.extend(list(sq_wave))        

        return    
    
    def append_squarewaves(
            self,
            freqs=[440.0],
            duration_milliseconds=500,
            volumes=[1.0]):

        volumes = list(np.array(volumes)/sum(volumes))
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)
        x = np.arange(int(num_samples))

        first_it = True
        for volume, freq in zip(volumes, freqs):
            print(freq)
            if first_it:
                sq_wave =   volume * sg.square(2 * np.pi * freq * ( x / self.sample_rate ))
                first_it = False
            else:
                sq_wave +=   volume * sg.sawtooth(2 * np.pi * freq * ( x / self.sample_rate ))

        self.audio.extend(list(sq_wave))
        return    
    
    def append_squaresawwave(
            self,
            freq=440.0,
            freq_offset = 5,
            duration_milliseconds=500,
            volume=1.0):
        volumes = [volume] * 2
        freqs = [freq, freq + freq_offset]
        volumes = list(np.array(volumes)/sum(volumes))
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)
        x = np.arange(int(num_samples))

        first_it = True
        for volume, freq in zip(volumes, freqs):
            if first_it:
                sq_wave =   volume * sg.square(2 * np.pi * freq * ( x / self.sample_rate ))
                first_it = False
            else:
                sq_wave +=   volume * sg.sawtooth(2 * np.pi * freq * ( x / self.sample_rate ))

        self.audio.extend(list(sq_wave))
        return        

    def save_wav2(self, file_name):
        # Open up a wav file
        wav_file=wave.open(file_name,"w")

        # wav params
        nchannels = 1

        sampwidth = 2

        # 44100 is the industry standard sample rate - CD quality.  If you need to
        # save on file size you can adjust it downwards. The stanard for low quality
        # is 8000 or 8kHz.
        nframes = len(self.audio)
        comptype = "NONE"
        compname = "not compressed"
        wav_file.setparams((nchannels, sampwidth, self.sample_rate, nframes, comptype, compname))

        # WAV files here are using short, 16 bit, signed integers for the 
        # sample size.  So we multiply the floating point data we have by 32767, the
        # maximum value for a short integer.  NOTE: It is theortically possible to
        # use the floating point -1.0 to 1.0 data directly in a WAV file but not
        # obvious how to do that using the wave module in python.
        for sample in self.audio:
            wav_file.writeframes(struct.pack('h', int( sample * 32767.0 )))

        wav_file.close()
        print (f"Wrote: {file_name}")
        return    


def main():
    parser = argparse.ArgumentParser(description="Command line utility for generating audio tone files.")
    parser.add_argument(
        "--config-file",
        default="tone_config.yml",
        help="Path to the configuration file (default: tone_config.yml)"
    )
    args = parser.parse_args()
    config_path = args.config_file

    if not os.path.isfile(config_path):
        print(f"Error: Config file '{config_path}' does not exist.")
        return None

    try:
        with open(config_path, 'r') as config_file:
            config_data = list(yaml.load_all(config_file, Loader=yaml.SafeLoader))
    except Exception as e:
        print(f"Error reading or parsing YAML config file: {e}")
        return None

    print(f"Using config file: {config_path}")
    print("Config data loaded successfully.")
    return config_data

# ...existing code...

if __name__ == "__main__":
    config_data = main()
    if config_data is not None:
        #import pprint
        #pprint.pprint(config_data)

        for tone_group in config_data:
            try:
                tone_count = len(list((x for x in tone_group.get('tones', [])  if x.get('tone', None))))
                print(f"Processing: {tone_group.get('name', 'output')}. Contains {tone_count} tones.")
            except:
                print(f"Warning: Invalid format in config file. Check examples.")
                continue
            bg = BeepGenerator()
            tones = tone_group.get("tones", [])
            for item in tones:
                if "tone" in item:
                    tone = item["tone"]
                    pitch = tone.get("pitch", 440)
                    duration = tone.get("duration", 500)
                    type_ = tone.get("type", "square")
                    pitch_offset = tone.get("pitch_offset", 0)
                    # Map type to BeepGenerator method
                    if type_ == "sqsaw":
                        bg.append_squaresawwave(
                            freq=pitch,
                            freq_offset=pitch_offset,
                            duration_milliseconds=duration,
                            volume=0.85
                        )
                    elif type_ == "square":
                        bg.append_squarewave(
                            freq=pitch,
                            duration_milliseconds=duration,
                            volume=0.85
                        )
                    elif type_ == "saw":
                        # Use append_squarewaves with sawtooth for saw type
                        bg.append_squarewave(
                            freq=pitch,
                            duration_milliseconds=duration,
                            volume=0.85
                        )
                    else:
                        print(f"Warning: Unknown tone type '{type_}'")
                elif "silence" in item:
                    silence = item["silence"]
                    duration = silence.get("duration", 500)
                    bg.append_silence(duration_milliseconds=duration)
                else:
                    print(f"Warning: Invalid tone/silence entry: {item}")

            name = tone_group.get("name", "output")
            if not name.lower().endswith(".wav"):
                name += ".wav"
            
            bg.save_wav(name)

    sys.exit()
