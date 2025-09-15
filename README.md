# A Python (pygame) based F3K Timer

```
pip install requests
pip install pygame

f3k_timer.py [-h] [--prep-minutes PREP_MINUTES] [--group-separation-minutes GROUP_SEPARATION_MINUTES] eventid
```

Aim is to create a Python (pygame) based timer application that takes event information from F3XVault and constructs a playlist for live audio playback to run an F3K event.

In addition, the application will allow external integrations with time display devices via a plugin mechanism allowing live timing data to be shown on a variety of devices via mechanisms such as:
- Serial (Pandora etc) - limited to current protocol (Round, Group, State and Time)

- Web API and ESPNow broadcast (esp32 devices)
  * JSON payload
  * Realtime updates (with transmission delay correction for remote services)
  * Extensible to allow full pilot info for group info display
  * Potentially could include score info for display between groups/rounds
  * Potentially could include pilot specific "please enter your score" messages based on lack of score data

- Others? - user extensible with well defined interface

Local control will be via web interface allowing headless running. This will use websockets for interactive status and messages and control.
