import math
import wave
import struct
from scipy import signal as sg
import numpy as np



import numpy as np
import scipy.io.wavfile


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
        scipy.io.wavfile.write(file_name, int(self.sample_rate), np.array(self.audio))
        print (f"Wrote: {file_name}")
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
                #sine_wave = volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))
                first_it = False
            else:
                sq_wave +=   volume * sg.sawtooth(2 * np.pi * freq * ( x / self.sample_rate ))
                #sine_wave += volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))

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
            #print(freq)
            if first_it:
                sq_wave =   volume * sg.square(2 * np.pi * freq * ( x / self.sample_rate ))
                #sine_wave = volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))
                first_it = False
            else:
                sq_wave +=   volume * sg.sawtooth(2 * np.pi * freq * ( x / self.sample_rate ))
                #sine_wave += volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))

        self.audio.extend(list(sq_wave))
        return        
    """def append_squaresawwave(
        self,
        freq=440.0, 
        duration_milliseconds=500, 
        volume=1.0):

        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        for x in range(int(num_samples)):
            square = sg.square(2 * np.pi * freq * ( x / self.sample_rate ))
            saw = sg.sawtooth(2 * np.pi * freq+75 * ( x / self.sample_rate ))
            self.audio.append(volume/2 * (square))
            self.audio2.append(volume/2 * (saw))
            #self.audio.append(volume * math.sin(2 * math.pi * freq * ( x / self.sample_rate )))
        self.audio
        return"""
        
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


if __name__ == "__main__":
    bg = BeepGenerator()
    freq_beep = 550
    freq_tone = 732
    saw_offset = 5
    short = 250# ms
    long=1000 #ms
    volume=0.85

    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)

    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_tone,  freq_offset=saw_offset, duration_milliseconds=long)
    bg.save_wav("4321_normal.wav")
    bg = BeepGenerator()
    bg.append_squaresawwave(volume=volume, freq=freq_tone,  freq_offset=saw_offset, duration_milliseconds=long)
    bg.save_wav("normal_1s.wav")
    
    bg = BeepGenerator()
    long=3000
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_tone,  freq_offset=saw_offset, duration_milliseconds=long)
    bg.save_wav("4321_3s.wav")

    bg = BeepGenerator()
    freq_beep = 500
    freq_tone = 442
    short = 100
    long = 300
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    bg.append_squaresawwave(volume=volume, freq=freq_beep,  freq_offset=saw_offset, duration_milliseconds=short)
    bg.append_silence(1000-short)
    
    bg.append_squaresawwave(volume=volume, freq=freq_tone,  freq_offset=saw_offset, duration_milliseconds=long)
    bg.save_wav("4321_short_down.wav")
  