# A Python (pygame) based F3K Timer

```
pip install requests
pip install pygame

f3k_timer.py [-h] [--prep-minutes PREP_MINUTES] [--group-separation-minutes GROUP_SEPARATION_MINUTES] eventid
```

Aim is to create a Python (pygame) based timer application that takes event information from F3XVault and constructs a playlist.
In addition, the application will allow external integrations with time display devices via a plugin mechanism allowing live timning data to be shown on a variety of devices via mechanisms such as:
- Serial (Pandora etc)
- ESPNow broadcast (esp32 devices)
- Web API (any external website)

Local control will be via web interface allowing headless running.
