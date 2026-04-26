# F3K Timer - Tone Generator

This directory contains tools for generating audio tones used in the F3K timing system, such as beeps, countdowns, and announcement signals.

## Overview

The tone generator creates WAV audio files based on YAML configuration definitions. It uses synthesized waveforms (sine, square, and hybrid square-sawtooth waves) to produce high-quality audio tones for competition timing.

## Quick Start

### Generate All Tones

```bash
./generate_tones.sh
```

This script will:

1. Create a Python virtual environment (`venv-tone_gen`) if it doesn't exist
2. Install required dependencies
3. Run `generate_tones.py` to generate all configured tones

### Generate Specific Configuration

```bash
./generate_tones.sh --config-file tone_config_play.yml
```

Or with the default configuration:

```bash
./generate_tones.sh --config-file tone_config.yml
```

## Configuration Files

### `tone_config.yml`

Main configuration file defining all generated tones. Each entry specifies a WAV filename and a sequence of tones and silences.

**Structure:**

```yaml
---
name: output_filename.wav
tones:
  - tone:
      pitch: 440 # Frequency in Hz
      duration: 250 # Duration in milliseconds
      type: sine|square|sqsaw # Waveform type
      pitch_offset: 5 # Additional frequency (only for sqsaw type)
  - silence:
      duration: 750 # Silence duration in milliseconds
```

**Waveform Types:**

- `sine` - Pure sine wave (smooth, basic beep)
- `square` - Square wave (sharper, more defined)
- `sqsaw` - Hybrid square + sawtooth (rich, complex tone)

### `tone_config_play.yml`

Alternative configuration for playing/testing tones.

## Generated Files

Tones are saved as WAV files (44.1 kHz, 16-bit mono) in this directory:

**Common Generated Tones:**

- `start_signal.wav` - Competition start signal
- `4321_normal.wav` - Countdown sequence (4-3-2-1)
- `4321_3s.wav` - Extended countdown (3 seconds per beat)
- `4321_short_down.wav` - Short countdown
- `normal_1s.wav` - Standard single tone

## How It Works

### 1. Configuration Parsing

The `generate_tones.py` script reads YAML configuration files and extracts tone definitions.

### 2. Waveform Synthesis

For each tone entry, it:

- Calculates the required number of audio samples based on duration
- Generates the specified waveform using NumPy and SciPy
- Combines multiple frequencies for hybrid waveforms (sqsaw type)
- Appends silence sequences between tones

### 3. Audio Export

- Converts floating-point samples to 16-bit PCM audio
- Writes WAV file using `scipy.io.wavfile`
- Saves to the current directory

## Dependencies

Required Python packages (auto-installed by `generate_tones.sh`):

```
numpy>=2.3.3
PyYAML>=6.0.3
scipy>=1.16.2
```

## Advanced Usage

### Creating Custom Tones

1. Edit `tone_config.yml` and add a new entry:

```yaml
---
name: my_custom_tone.wav
tones:
  - tone:
      pitch: 880
      duration: 500
      type: sqsaw
      pitch_offset: 50
  - silence:
      duration: 250
  - tone:
      pitch: 440
      duration: 500
      type: sqsaw
      pitch_offset: 20
```

2. Generate the new tone:

```bash
./generate_tones.sh
```

3. Test the generated WAV file in the main application or with a media player.

### Using YAML Anchors for Reusability

For repeated patterns, use YAML anchors (`&`) and aliases (`*`):

```yaml
---
name: countdown.wav
tones:
  - tone: &beep
      pitch: 600
      duration: 200
      type: sqsaw
      pitch_offset: 10
  - silence: &gap
      duration: 300
  - tone: *beep
  - silence: *gap
  - tone: *beep
  - silence: *gap
```

### Experimenting with Frequencies

Use [Online Tone Generator](https://onlinetonegenerator.com/multiple-tone-generator.html) to preview and experiment with tone combinations before adding them to the configuration.

## Troubleshooting

### "Failed to open file for writing"

The WAV file is already open in another application (player, editor). Close it and retry.

### No sound output

- Check that the pitch frequencies are in audible range (20-20000 Hz)
- Verify WAV files were generated (check timestamps)
- Test with the main application's sound test interface

### Virtual Environment Issues

Remove the old venv and regenerate:

```bash
rm -rf venv-tone_gen
./generate_tones.sh
```

## Integration with f3k-timer

Generated WAV files are used by:

- **audio_library.py** - Loads and caches tone files
- **f3k_cl_audio.py** - Plays tones during competition
- **Plugin system** - Custom plugins can trigger tone playback via `events.trigger('audioplayer.play_audio', wav_obj)`

See the main [f3k-timer documentation](../../AGENTS.md) for details on audio playback integration.

## References

- **Waveform Generation**: Based on [StackOverflow: Python WAV File Generation](https://stackoverflow.com/questions/33879523/python-how-can-i-generate-a-wav-file-with-beeps)
- **NumPy/SciPy**: Signal processing for waveform synthesis
- **PyYAML**: Configuration parsing

## License

Same as parent f3k-timer project.
