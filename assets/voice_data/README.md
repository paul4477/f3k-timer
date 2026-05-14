# Storage directory for Voice definitions

setup.sh will populate with default voice.

## Download of alternative voices

```
cd assets/sounds/

f3k-timer/venv-f3k-timer/bin/python -m  piper.download_voices <voice>

## e.g.
f3k-timer/venv-f3k-timer/bin/python -m  piper.download_voices en_GB-alba-medium
```

Voice data files are written to current working directory and must be moved to `assets/voice_data/`

## Regenerate voice files

Although the voice files are generated on the first run of `setup.sh`, there may be reason to regenerate the voice sound files after updates.

```
cd assets/sounds

## Default voice
../../venv-f3k-timer/bin/python generate_language.py

## Specify specific voice data
../../venv-f3k-timer/bin/python generate_language.py --voice=en_GB-alba-medium
```

## Piper TTS

https://github.com/OHF-Voice/piper1-gpl?tab=readme-ov-file
