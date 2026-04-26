# AI Agent Instructions for f3k-timer

## Project Overview

**f3k-timer** is an event-driven, async Python application for managing F3K model aircraft competition timing. It features real-time state management, a web-based control interface, and an extensible plugin system.

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component diagrams and design patterns.

## Core Architecture Pattern: Event-Driven with Plugins

This codebase uses **event-driven pub/sub architecture** where:

- **EventEngine** ([f3k_cl_event_engine.py](f3k_cl_event_engine.py)) is the central message bus
- **Player** ([f3k_cl_player.py](f3k_cl_player.py)) drives state transitions and emits events
- **Plugins** (PluginBase-derived classes) subscribe to events and perform side effects
- **WebFrontend** ([f3k_cl_web_server.py](f3k_cl_web_server.py)) is itself a plugin that bridges HTTP clients to the event system

### Key Files by Role

| File                                             | Role              | Key Responsibility                                                    |
| ------------------------------------------------ | ----------------- | --------------------------------------------------------------------- |
| [f3k_timer.py](f3k_timer.py)                     | Main entry point  | Loads config, instantiates components, manages async lifecycle        |
| [f3k_cl_event_engine.py](f3k_cl_event_engine.py) | Event bus         | Pub/sub mechanism for all component communication                     |
| [f3k_cl_player.py](f3k_cl_player.py)             | State management  | Drives timing loop, emits tick/second/section/group/round events      |
| [f3k_cl_web_server.py](f3k_cl_web_server.py)     | HTTP + plugin     | Serves web UI, broadcasts state to clients, routes control commands   |
| [f3k_cl_competition.py](f3k_cl_competition.py)   | Domain model      | Round, Group, Section, Pilot data structures                          |
| [plugin_base.py](plugin_base.py)                 | Plugin base class | Abstract class for all plugins; provides event subscription interface |
| [config.yml](config.yml)                         | Configuration     | YAML-based plugin definitions and timing parameters                   |

## Main Event Update Action (f3k_cl_player.py)

The **Player.update()** method drives all state transitions and event emissions. Understanding this is critical for implementing features:

### Event Emission Pattern

```python
async def update(self):
    # Every tick iteration fires events to all consumers
    for consumer in self.eventConsumers:
        self.events.trigger(f"{consumer.__class__.__name__}.tick", self.state)

    # When a second boundary is crossed, fire .second events
    if (self.state.slot_time > 0) and (self.last_announced != self.state.slot_time):
        for consumer in self.eventConsumers:
            self.events.trigger(f"{consumer.__class__.__name__}.second", self.state)
```

**Key insight**: Event names are namespaced by consumer class name. When adding a plugin called `MyPlugin`, it automatically receives:

- `MyPlugin.tick` - fires every loop iteration (high frequency)
- `MyPlugin.second` - fires once per second when slot_time changes (low frequency)
- `MyPlugin.newSection` - fires when transitioning to new section
- `MyPlugin.newGroup` - fires when transitioning to new group
- `MyPlugin.newRound` - fires when transitioning to new round

### State Transitions

State progresses through rounds → groups → sections. The Player uses iterators:

```python
# Advancing to next section/group/round
state.next_section()  # Calls state.next_group() if section exhausted
state.next_group()    # Calls state.next_round() if group exhausted
state.next_round()    # Returns False if event complete

# Each transition triggers newSection/newGroup/newRound events
# These events pass the full state object so plugins can extract context
```

**When modifying event emission**:

1. Always include the full `state` object as the event payload (plugins need context)
2. Trigger events to **all consumers** so plugins receive them independently
3. Use the `{consumer.__class__.__name__}.{event_type}` naming pattern for consistency

## Web Server Backend Pattern (f3k_cl_web_server.py)

WebFrontend is both an aiohttp server **and** a plugin. This dual nature is important:

### As a Plugin (EventEngine Consumer)

```python
class WebFrontend(PluginBase):
    def __init__(self, events, config, player=None):
        super().__init__(events, config)  # Registers standard handlers
        # ... custom initialization ...

    async def onTick(self, state):
        """Called every loop iteration. Broadcasts current state to web clients via SSE."""
        if not self.limit_rate(state):  # Rate limit to 6 updates/sec
            d = state.get_dict()
            for q in list(self.client_queues):
                await q.put_nowait((json.dumps(d), "time"))

    async def onNewSection(self, state):
        """Called when section changes. Broadcasts section metadata."""
        for q in list(self.client_queues):
            q.put_nowait((json.dumps({'type': state.section.__class__.__name__}), "sectionData"))
```

### As an HTTP Server

Routes handle web client commands by **triggering player events**:

```python
async def handle_control(self, request):
    # User clicks "Start" → POST /control/start
    # This becomes: events.trigger("player.start")
    self.events.trigger(f"player.{request.match_info['command']}")
    return web.Response(status=200, text="Done")

# Control commands (start, pause, skip_fwd, skip_back, goto, stop, reset)
# are handled by Player.register_handlers() which subscribes to these events
```

**Key pattern**: Web clients don't call Player methods directly. Instead:

1. HTTP request → route handler
2. Route handler → `events.trigger("player.<command>")`
3. Player's registered handler → implements the command
4. State changes → new events flow back to WebFrontend → broadcast to clients

### SSE (Server-Sent Events) Pattern

```python
async def handle_state_stream(self, request):
    queue = asyncio.Queue()
    self.client_queues.add(queue)
    async with sse_response(request) as resp:
        while resp.is_connected():
            q_item = await queue.get()
            payload, etype = q_item  # event type: "time", "sectionData", etc.
            await resp.send(payload, event=etype)
```

Each connected client gets its own queue. When events fire, the WebFrontend plugin puts data on all queues. Clients reconnect automatically.

## Plugin Mechanism (plugin_base.py + config.yml)

### Creating a New Plugin

1. **Subclass PluginBase** and implement desired event handlers:

```python
# my_plugin.py
from plugin_base import PluginBase

class MyPlugin(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.config = config  # Plugin-specific config from config.yml

    async def onTick(self, state):
        """Called every iteration. state has .slot_time, .round, .group, .section, .section_length"""
        if state.section.is_no_fly():
            # Do something during no-fly periods
            pass

    async def onSecond(self, state):
        """Called once per second boundary."""
        pass

    async def onNewSection(self, state):
        """Called when section transitions."""
        self.logger.info(f"New section: {state.section}")
```

2. **Add to config.yml**:

```yaml
---
name: MyPlugin
module: my_plugin
object_name: MyPlugin
# Plugin-specific config below (accessed via self.config)
some_setting: value123
rate_limit: 10 # Built-in: max events/sec (uses limit_rate() if needed)
```

3. **Plugin loading** (automatic, in f3k_timer.py):

```python
# For each config section with 'module' and 'object_name':
module = importlib.import_module(config_section['module'])
plugin_object = getattr(module, config_section['object_name'])
plugin_instance = plugin_object(events, config_section)
player.eventConsumers.append(plugin_instance)
```

### PluginBase Interface

All plugins get:

- `self.events` - EventEngine instance for triggering events
- `self.config` - Dict of plugin-specific config from config.yml
- `self.logger` - Logging instance
- `self.is_enabled()`, `self.enable()`, `self.disable()` - Enable/disable plugin
- `self.limit_rate()` - Check if rate-limited (`rate_limit` calls per second)

### Event Handler Signature

```python
async def on<EventName>(self, state):
    # state is the full State object from Player
    # Contains: .round, .group, .section, .slot_time, .end_time
    # .section has: .get_time_str(), .is_no_fly(), .section_code()
    pass
```

**Do NOT** make event handlers blocking. They run in async context. Use `await asyncio.sleep()` if needed.

## State Object Reference

The `state` object passed to all event handlers:

```python
class State:
    round: Round           # Current round
    group: Group           # Current group
    section: Section       # Current section (Prep, NoFly, Work, Land, Announce, etc.)
    slot_time: int         # Seconds remaining in current time window
    end_time: float        # Unix timestamp when current section ends
    section_length: int    # Total duration of current section

    @property
    def time_str: str      # "MM:SS" formatted time
    @property
    def time_digits: str   # "MMSS" raw digits

    def is_no_fly(self) -> bool      # True if in no-fly period
    def next_section() -> bool       # Advance to next section
```

## Common Development Tasks

### Adding an Event-Driven Feature

1. Choose where the feature triggers: tick (every loop), second (per second), or at section/group/round changes
2. Create a plugin or extend WebFrontend with an event handler
3. Access the state object to make decisions
4. Trigger new events if you need to coordinate with other subsystems

Example: Send state to external API on section changes:

```python
async def onNewSection(self, state):
    await send_to_external_api(state.get_dict())
```

### Debugging Event Flow

- All non-tick events logged: `logger.debug(f"Firing: {event}")`
- Check `f3k_timer.log` for event sequence
- Enable debug logging for specific components in logging config

### Modifying Player State Transitions

State progression happens in `Player.update()`. Be careful:

- Events must fire **before** state transitions for consistent ordering
- Always pass full `state` object to event handlers
- Test with different event/round/group configurations

## Dependencies

- **aiohttp** - Web server (SSE, routes)
- **pygame** - Timer (millisecond precision via `time.get_ticks()`)
- **PyYAML** - Configuration parsing
- **piper-tts** - Text-to-speech for announcements
- **pyserial** - Serial communication for hardware devices

Run `pip install -r requirements.txt` in the venv-f3k-timer environment.

## Running & Testing

```bash
# Start main application
python f3k_timer.py

# Test harness for plugins
python test_plugins.py

# Default config loads from config.yml
# To test new plugins: add them to config.yml with module/object_name, then run f3k_timer.py
```

The application logs to `f3k_timer.log` (DEBUG level).

## Common Pitfalls

1. **Not awaiting async operations** - All event handlers are async; use `await` for I/O
2. **Blocking plugin handlers** - Plugins block the entire event loop; use `await asyncio.sleep()` instead of `time.sleep()`
3. **Modifying state directly** - Always use `state.next_section()` etc. to trigger proper events
4. **Forgetting to register handlers** - PluginBase.register_handlers() is called in `__init__`, but only for standard events
5. **Race conditions with rate limiting** - Use `self.limit_rate()` to avoid spamming events across multiple queues

## Quick Navigation

- **Modify timing logic**: [f3k_cl_player.py](f3k_cl_player.py) `Player.update()` method
- **Add HTTP endpoint**: [f3k_cl_web_server.py](f3k_cl_web_server.py) `WebFrontend.__init__()` routes
- **Add new event type**: [f3k_cl_event_engine.py](f3k_cl_event_engine.py) and trigger in Player
- **Create plugin**: Copy [plugin_base.py](plugin_base.py) pattern, add to [config.yml](config.yml)
- **Understand competition data model**: [f3k_cl_competition.py](f3k_cl_competition.py)
