# F3K Timer

An event-driven, asynchronous Python application for managing F3K model aircraft competition timing. Features real-time state management, a web-based control interface, and an extensible plugin system.

## Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (`venv` or `conda`)

### Setup

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv-f3k-timer
   source venv-f3k-timer/bin/activate  # On Windows: venv-f3k-timer\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python f3k_timer.py
   ```

The web interface will be available at `http://localhost:80` (or the configured port in `config.yml`).

4. **View logs:**
   ```bash
   tail -f f3k_timer.log  # On Windows: use type f3k_timer.log or a text editor
   ```

## Configuration

Edit `config.yml` to customize:

- **Timing parameters** - prep time, group separation, landing window
- **Web server** - port and listening address
- **Plugins** - enable/disable plugins and configure their parameters
- **Voice settings** - text-to-speech language and voice selection

Example:

```yaml
---
name: main
prep_time: 300 # Preparation time in seconds
group_separation_time: 120
voice: en_US-lessac-medium
---
name: web
port: 80
```

## Project Structure

```
f3k-timer/
├── README.md                    # This file
├── ARCHITECTURE.md              # Detailed architecture and design patterns
├── AGENTS.md                    # AI agent instructions and developer guide
├── f3k_timer.py                 # Main entry point
├── f3k_cl_event_engine.py       # Event bus (pub/sub mechanism)
├── f3k_cl_player.py             # State management and timing loop
├── f3k_cl_web_server.py         # Web server and HTTP routes
├── f3k_cl_competition.py         # Domain model (Round, Group, Pilot, Section)
├── plugin_base.py               # Base class for plugins
├── config.yml                   # Main configuration file
├── requirements.txt             # Python dependencies
└── assets/
    ├── html/                    # Web UI templates
    ├── js/                      # Web client JavaScript
    ├── sounds/                  # Audio tones and tone generator
    │   ├── README.md            # Tone generator documentation
    │   ├── generate_tones.py    # Tone synthesis script
    │   ├── tone_config.yml      # Tone definitions
    │   └── generate_tones.sh    # Setup and run tone generator
    └── voice_data/              # Text-to-speech voice models
```

## Core Components

### EventEngine ([f3k_cl_event_engine.py](f3k_cl_event_engine.py))

Central pub/sub message bus enabling loose coupling between components. All inter-component communication flows through events.

### Player ([f3k_cl_player.py](f3k_cl_player.py))

Drives the competition timing loop and state management. Emits events for:

- **tick** - High-frequency updates (every iteration)
- **second** - Per-second updates
- **newSection/newGroup/newRound** - State transitions

### WebFrontend ([f3k_cl_web_server.py](f3k_cl_web_server.py))

Dual-purpose component acting as both an HTTP server and a plugin:

- Serves web UI (event_runner.html, event_viewer.html, event_selector.html)
- Broadcasts state changes to clients via Server-Sent Events (SSE)
- Routes web control commands to Player via events

### Plugin System ([plugin_base.py](plugin_base.py))

Extensible mechanism for adding features without modifying core code. Plugins:

- Inherit from `PluginBase`
- Subscribe to events via async handlers
- Are configured and loaded from `config.yml`

Example plugins:

- `plugin_web_service.py` - Forward state to external APIs
- `plugin_espnow.py` - Send updates to wireless scoreboards
- `plugin_serialjson.py` - Serial communication with hardware

### Competition Model ([f3k_cl_competition.py](f3k_cl_competition.py))

Domain objects representing competition structure:

- **Round** - A competition round
- **Group** - Pilots flying together in a round
- **Section** - Timed periods (Prep, NoFly, Work, Land, Gap, Announce)
- **Pilot** - Individual competitor

## Documentation

### For Developers

- **[AGENTS.md](AGENTS.md)** - AI agent instructions covering:
  - Event-driven architecture patterns
  - Main event update flow in Player
  - Web server plugin patterns
  - Plugin development guide
  - State object reference
  - Common pitfalls and debugging

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep dive with:
  - Component diagrams
  - Design pattern explanations
  - Event flow documentation
  - Key implementation details

### For Audio Setup

- **[assets/sounds/README.md](assets/sounds/README.md)** - Tone generator guide:
  - How to generate competition audio tones
  - YAML configuration format
  - Waveform types (sine, square, hybrid)
  - Customizing audio for your competition

## Common Tasks

### Add a New Feature

1. Choose where to implement it:
   - **Plugin** - For features that don't require core changes
   - **WebFrontend handler** - For web UI-triggered features
   - **New event type** - If you need to coordinate multiple components

2. See [AGENTS.md](AGENTS.md) for step-by-step examples and patterns

### Create a Custom Plugin

```python
# my_plugin.py
from plugin_base import PluginBase

class MyPlugin(PluginBase):
    async def onTick(self, state):
        # Called every loop iteration
        pass

    async def onSecond(self, state):
        # Called once per second
        pass

    async def onNewSection(self, state):
        # Called when section transitions
        pass
```

Add to `config.yml`:

```yaml
---
name: MyPlugin
module: my_plugin
object_name: MyPlugin
rate_limit: 10 # Optional: max events/sec
```

### Generate Audio Tones

```bash
cd assets/sounds
./generate_tones.sh
```

See [assets/sounds/README.md](assets/sounds/README.md) for details.

### Debug Event Flow

Check `f3k_timer.log` for event sequence (non-tick events logged at DEBUG level):

```bash
tail -f f3k_timer.log | grep -i "firing\|event"
```

## Web Interfaces

### Event Runner (`http://localhost/`)

Control interface for competition operators. Features:

- Large time display
- Start/pause/skip controls
- Round/group navigation
- Real-time state updates via SSE

### Event Viewer

Public display interface showing:

- Current time and section
- Round and group info
- Pilot list
- Auto-reconnecting WebSocket

### Event Selector

Event search and loading from F3XVault API.

## Testing

```bash
# Test harness for plugins
python test_plugins.py

# Audio system test
# Use the sound-test endpoint in the web UI
```

## Troubleshooting

### Port Already in Use

Change the port in `config.yml`:

```yaml
---
name: web
port: 8080
```

### Missing Audio Files

Generate tones:

```bash
cd assets/sounds && ./generate_tones.sh
```

### Event Not Firing

1. Check `f3k_timer.log` for event triggers
2. Verify plugin is enabled: `self.is_enabled()`
3. Ensure event handler is async: `async def onEventName(...)`
4. Check rate limiting isn't suppressing events: `self.limit_rate()`

### Plugin Import Errors

Verify `config.yml` has correct `module` and `object_name`:

```yaml
---
name: MyPlugin
module: my_plugin # Filename without .py
object_name: MyPlugin # Class name
```

## Dependencies

Key dependencies (see [requirements.txt](requirements.txt) for full list):

- **aiohttp** - Web server and HTTP client
- **pygame** - Timer with millisecond precision
- **PyYAML** - Configuration parsing
- **piper-tts** - Text-to-speech for announcements
- **pyserial** - Serial communication
- **scipy** & **numpy** - Audio tone generation

## License

[Specify your license here]

## Contributing

[Add contribution guidelines here]

## Support

For questions about:

- **Architecture & design** → See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Plugin development** → See [AGENTS.md](AGENTS.md)
- **Audio setup** → See [assets/sounds/README.md](assets/sounds/README.md)
- **Bugs** → Check `f3k_timer.log` and [AGENTS.md#debugging-event-flow](AGENTS.md)
