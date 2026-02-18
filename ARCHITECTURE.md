# F3K Timer Architecture

## Overview

F3K Timer is an event-driven, plugin-based timing system for F3K model aircraft competitions. It uses asynchronous Python with a web-based interface for control and display.

## Architecture Diagram

```mermaid
---
config:
  look: handDrawn
  theme: neutral
---
graph TB
    subgraph "Main Application"
        FT[f3k_timer.py<br/>Main Entry Point]
        EE[EventEngine<br/>Event Management]
        CLK[Clock<br/>Timing Control]
        PL[Player<br/>State Management]
    end

    subgraph "Web Layer"
        WF[WebFrontend<br/>HTTP/WebSocket Server]
        ER[event_runner.html<br/>Control Interface]
        EV[event_viewer.html<br/>Display Interface]
        ES[event_selector.html<br/>Event Search]
        ERJ[event_runner.js]
        EVJ[event_viewer.js]
    end

    subgraph "Data Layer"
        CFG[config.yml<br/>Configuration]
        RND[Round<br/>Round Data]
        GRP[Group<br/>Group Data]
        PLT[Pilot<br/>Pilot Data]
    end

    subgraph "Plugin System"
        PB[PluginBase<br/>Base Class]
        PWS[WebService Plugin<br/>HTTP Integration]
        PEX[...Other Plugins]
    end

    subgraph "External Systems"
        F3X[F3XVault API<br/>Event Data]
        EXT[External Services<br/>via WebService Plugin]
    end

    %% Main flow
    FT -->|creates| EE
    FT -->|creates| CLK
    FT -->|creates| PL
    FT -->|creates| WF
    FT -->|loads| CFG

    %% Event propagation
    EE -->|events| PL
    EE -->|events| WF
    EE -->|events| PB

    %% Player state
    PL -->|manages| RND
    RND -->|contains| GRP
    GRP -->|contains| PLT

    %% Web connections
    WF -->|serves| ER
    WF -->|serves| EV
    WF -->|serves| ES
    WF -->|SSE/WebSocket| ERJ
    WF -->|SSE/WebSocket| EVJ
    ERJ -->|control commands| WF
    EVJ -->|receives updates| WF

    %% Plugin system
    CFG -->|defines| PB
    PB -->|inherited by| PWS
    PB -->|inherited by| PEX
    PWS -->|HTTP POST| EXT

    %% External data
    ES -->|queries| F3X
    F3X -->|event data| ES
    ES -->|loads event| WF

    %% Timing
    CLK -->|tick events| EE

    style FT fill:#e1f5ff
    style EE fill:#fff4e1
    style WF fill:#e8f5e9
    style PB fill:#f3e5f5
    style CFG fill:#fce4ec
```

## Core Components

### Main Application Layer

#### f3k_timer.py (Main Entry Point)

- Loads configuration from `config.yml`
- Initializes all major components
- Sets up event loop and starts web server
- Manages plugin lifecycle

#### EventEngine

- Async event bus for component communication
- Provides pub/sub mechanism for events
- Events include: `onSecond`, `onNewRound`, `onDefPilot`, etc.
- Supports both sync and async event handlers

#### Clock

- Provides timing control with FPS limiting
- Uses `tick()` method for consistent frame timing
- Calculates actual FPS for monitoring
- Based on `pygame.time.get_ticks()` for millisecond precision

#### Player

- Manages competition state and progression
- Controls rounds, groups, and timing sections
- Generates state updates for display
- Handles control commands (start, pause, skip, etc.)

### Web Layer

#### WebFrontend (aiohttp server)

- HTTP server on configurable port (default 80)
- WebSocket endpoint (`/ws/`) for bidirectional communication
- Server-Sent Events (`/state-stream`) for state updates
- REST endpoints for control (`/control/<action>`, `/goto/<round>/<group>`)
- Serves static HTML/JS assets

#### Web Interfaces

**event_runner.html**

- Control interface for competition operators
- Large time display
- Control buttons (start, pause, skip, etc.)
- Round/group selection
- Uses EventSource for real-time updates

**event_viewer.html**

- Public display interface
- Shows current time, round, group, section
- Displays pilot list for current group
- Auto-reconnecting WebSocket for resilience

**event_selector.html**

- Event search and loading interface
- Integrates with F3XVault API
- Filters by country, date range, event type
- Saves search preferences in cookies
- Loads selected event configuration

### Data Layer

#### Configuration (config.yml)

YAML-based configuration with multiple sections:

- `main`: Core timing parameters (prep_time, group_separation_time, voice)
- `web`: Web server settings (port)
- Plugin configurations with `module` and `object_name` for dynamic loading

#### Domain Model

**Round**

- Represents a competition round
- Contains list of Groups
- Stores task-specific configuration (window time, number of flights, etc.)

**Group**

- Represents a group of pilots flying together
- Generates timing sections via iterator (prep, no-fly, work, land, gap)
- Section durations calculated from event config and round parameters

**Pilot**

- Pilot information and state
- Associated with groups

### Plugin System

#### PluginBase

- Abstract base class for all plugins
- Receives EventEngine instance in constructor
- Can subscribe to any event type
- Configured via `config.yml`

#### Plugin Loading

Dynamic plugin instantiation from config:

```yaml
name: PluginName
module: plugin_module_name
object_name: ClassName
# ...additional plugin-specific config...
```

#### WebService Plugin

- Forwards state updates to external HTTP endpoint
- Configurable URL and HTTP method (POST/GET)
- Handles connection failures gracefully
- Implements retry logic with failure threshold

### External Systems

#### F3XVault API Integration

- RESTful API for event data
- Authentication via login credentials
- Event search with filters
- Event detail retrieval
- JSON format for event configuration

#### External Service Integration

- Via WebService plugin
- Real-time state forwarding
- JSON payload with competition state
- Configurable endpoints per deployment

## Key Design Patterns

### Event-Driven Architecture

- Components communicate via EventEngine
- Loose coupling between subsystems
- Easy to add new event types and handlers
- Supports async event propagation

### Plugin Architecture

- Core functionality extended via plugins
- Runtime plugin loading from configuration
- Plugin isolation with error handling
- No core code changes needed for extensions

### Async/Await Throughout

- Non-blocking I/O operations
- Concurrent handling of web requests and timing
- asyncio event loop manages all async tasks
- Efficient resource usage

### Client-Server with Real-Time Updates

- WebSocket for bidirectional control
- Server-Sent Events for unidirectional state streaming
- Automatic reconnection on connection loss
- Multiple simultaneous clients supported

## Event Flow

1. **Startup**
   - Load config.yml
   - Create EventEngine, Clock, Player
   - Initialize plugins from config
   - Start WebFrontend server

2. **Timing Loop**
   - Clock generates tick events at configured FPS
   - Player updates state on each tick
   - EventEngine broadcasts state changes
   - Plugins receive and process events

3. **State Updates**
   - Player emits state every second
   - WebFrontend receives state via EventEngine
   - State broadcast to all connected clients via SSE
   - Clients update UI in real-time

4. **Control Flow**
   - User clicks button in event_runner.html
   - JavaScript sends POST to `/control/<action>`
   - WebFrontend routes to Player control method
   - Player updates state, triggers events
   - New state flows back to clients

## Configuration

Example `config.yml` structure:

```yaml
---
name: main
prep_time: 120
use_strict_test_time: False
group_separation_time: 5
voice: en_US-lessac-medium

---
name: web
port: 80

---
name: Web
module: plugin_web_service
object_name: WebService
url: https://fxtiming.ddns.net/api/event/
```

## Dependencies

- **aiohttp**: Async HTTP server and client
- **pygame**: Timing and audio playback
- **PyYAML**: Configuration parsing
- **requests**: HTTP client for plugins
- **Bootstrap**: UI framework for web interfaces
- **scipy/numpy**: Audio generation for tones

## Deployment Considerations

- Designed for Raspberry Pi deployment
- Network detection script for WiFi interface configuration
- Service management via systemd
- Log rotation for production use
- Cookie-based state persistence for user preferences

## State Flow Diagram

### Player and State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uninitialized: Player Created

    Uninitialized --> PreComp: init_pre_comp()
    PreComp --> DataLoaded: load_data(raw_json)

    DataLoaded --> Ready: Data Available
    Ready --> Running: start()

    Running --> Paused: pause()
    Paused --> Running: pause() (resume)

    Running --> AnnounceRound: next_round()
    AnnounceRound --> AnnounceGenerating: generate_and_store_sound
    AnnounceGenerating --> AnnouncePlaying: sound ready
    AnnouncePlaying --> PrepSection: announcement complete

    PrepSection --> NextSection: time expires / skip_next()
    NextSection --> WorkSection: next_section()
    WorkSection --> NextSection: time expires
    NextSection --> LandSection: next_section()
    LandSection --> NextSection: time expires
    NextSection --> GapSection: next_section()

    GapSection --> NextGroup: time expires / next_group()
    NextGroup --> AnnounceRound: more groups

    NextGroup --> NextRound: no more groups
    NextRound --> AnnounceRound: more rounds
    NextRound --> EventComplete: no more rounds

    Running --> TimeAdjusted: skip_fwd() / skip_back() / skip_previous()
    TimeAdjusted --> Running: time adjusted

    Running --> GotoRound: goto(round, group)
    GotoRound --> Running: jumped to position

    Running --> Stopped: stop()
    Paused --> Stopped: stop()
    Stopped --> Running: start()

    EventComplete --> ShowTime: event finished
    ShowTime --> ShowTime: display clock

    DataLoaded --> Reset: reset()
    Ready --> Reset: reset()
    Running --> Reset: reset()
    Paused --> Reset: reset()
    Stopped --> Reset: reset()
    EventComplete --> Reset: reset()
    Reset --> Uninitialized: cleared

    Running --> Shutdown: quit()
    Paused --> Shutdown: quit()
    Shutdown --> [*]

    note right of AnnounceRound
        Generates speech:
        "Round X, Group Y"
        + pilot list
    end note

    note right of PrepSection
        Sections iterate:
        prep → work → land → gap
        (varies by task type)
    end note

    note right of ShowTime
        Displays actual time
        when not in competition
    end note
```

### State Transitions Details

**Initialization Flow:**

1. `Player` created with `EventEngine` reference
2. `init_pre_comp()` sets up `ShowTimeSection` (displays actual time)
3. `load_data()` parses event JSON, creates rounds/groups/pilots
4. Player enters `Ready` state

**Competition Flow:**

1. `start()` creates new `State` object and calls `state.start()`
2. `state.start()` initializes round iterator and calls `next_round()`
3. `next_round()` fires `newRound` event, initializes group iterator
4. `next_group()` fires `newGroup` event, initializes section iterator
5. `next_section()` fires `newSection` event, sets `slot_time` and `end_time`

**Timing Loop (in `update()`):**

- Each tick: calculate remaining `slot_time` from `end_time`
- Fire `tick` events to all consumers
- When second changes: fire `second` events to all consumers
- When `now >= end_time`: call `state.next()` to advance

**Section Progression:**

- `state.next()` tries `next_section()` → `next_group()` → `next_round()` in order
- Each returns `True` if successful, `False` if iterator exhausted
- Announcement sections wait for audio generation and playback before advancing

**Control Commands:**

- `pause()`: toggles between paused/running, resumes time on unpause
- `skip_fwd(seconds)`: reduces `slot_time`, recalculates `end_time`
- `skip_back(seconds)`: increases `slot_time` up to section length
- `skip_previous()`: resets to full section time
- `skip_next()`: forces immediate advancement to next section/group/round
- `goto(round, group)`: manually positions iterators without firing all events
- `stop()`: stops timing, resets state
- `reset()`: full reset to uninitialized state
- `quit()`: sets `running = False`, exits main loop

**Special Sections:**

- `AnnounceSection`: generates and plays speech before each group
- `ShowTimeSection`: displays actual time when no competition running
- Standard sections: Prep, NoFly, Work, Land, Gap (task-dependent)

**Event Propagation:**
Each state change fires events to registered consumers:

- `{Consumer}.newRound` - new round started
- `{Consumer}.newGroup` - new group started
- `{Consumer}.newSection` - new timing section started
- `{Consumer}.tick` - every update loop iteration
- `{Consumer}.second` - every second of timing
