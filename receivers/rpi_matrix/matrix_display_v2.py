#!/usr/bin/env python3
"""
matrix_display_v2.py — F3K Competition LED Matrix Display

Receives serial JSON data from the f3k-timer and renders competition
state on an RGB LED matrix.

Refactored to use an object-oriented architecture with:
  - Configuration dataclasses for each subsystem
  - FontLibrary for centralised font management
  - MatrixController wrapping the low-level RGBMatrix API
  - PilotRegistry for pilot id → name lookup
  - BaseRenderer hierarchy — one renderer per competition section
  - DisplayRouter mapping section names to the correct renderer
  - SerialReader isolating all serial I/O and JSON parsing
  - MatrixDisplayApp orchestrating the full event loop
"""

import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import serial

# ---------------------------------------------------------------------------
# Hardware driver vs. pygame simulator
#
# Pass ``--simulate`` on the command line to use the pygame LED simulator
# instead of the real rgbmatrix hardware driver.  The simulator is also
# activated automatically when the ``rgbmatrix`` package is not installed
# (e.g. when developing on a non-Raspberry Pi machine).
# ---------------------------------------------------------------------------
try:
    print ("sys.argv:", sys.argv)
    if "--simulate" in sys.argv:
        raise ImportError("simulator requested via --simulate")
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
except ImportError:
    from sim_rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging — write to stderr at DEBUG level by default; callers may override.
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SerialConfig:
    """Serial port connection parameters."""
    #port: str = "/dev/ttyUSB0"
    port: str = "COM4"
    baud_rate: int = 115200 #19200
    timeout: float = 0.3
    startup_delay: float = 0.0       # seconds to wait before opening the port


@dataclass
class MatrixConfig:
    """RGBMatrix hardware parameters."""
    rows: int = 16
    cols: int = 32
    chain_length: int = 3
    parallel: int = 3
    brightness: int = 100
    multiplexing: int = 5
    gpio_slowdown: int = 3
    row_address_type: int = 2
    pwm_lsb_nanoseconds: int = 80
    pwm_bits: int = 1
    hardware_mapping: str = "regular"


@dataclass
class DisplayConfig:
    """Display-level parameters (fonts, layout, timeouts)."""
    font_base_path: str = "../fonts"
    no_data_timeout: float = 30.0        # seconds before showing no-data screen
    pilot_list_display_time: float = 15.0  # seconds to hold pilot list display
    time_row_y: int = 48                 # y-baseline for the large time font
    colon_x: int = 41                   # x-position of the colon separator
    colon_y: int = 43
    time_sec_x: int = 50                # x-position of the seconds digits
    time_sec_y: int = 48
    header_left_x: int = 0             # x-position of the left header label
    header_right_x: int = 30           # x-position of the right header label
    header_y: int = 8
    task_name_y: int = 15
    pilot_list_start_y: int = 15
    pilot_list_line_height: int = 7
    boot_title_x: int = 10
    boot_title_y: int = 12
    boot_subtitle_y: int = 8
    display_width: int = 96              # total panel width  = cols × chain_length
    display_height: int = 48             # total panel height = rows × parallel


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TimingData:
    """Parsed payload from a 't=time' serial packet."""
    section: str
    time_s: str          # "MM:SS"
    slot_time: int
    no_fly: bool
    round_num: str
    group_letter: str
    flight_num: int
    task_name: str       # already stripped of its 13-char prefix

    @property
    def time_minutes(self) -> str:
        return self.time_s[:2]

    @property
    def time_seconds(self) -> str:
        return self.time_s[3:]

    @classmethod
    def from_dict(cls, data: dict) -> "TimingData":
        """
        Construct a TimingData from the 'd' payload of a 'time' packet.
        Raises KeyError if required fields are absent.
        """
        raw_task = data.get("task_name", "")
        task_name = raw_task[13:] if len(raw_task) > 13 else raw_task
        raw_slot = data.get("slot_time", 0)
        try:
            slot_time = int(raw_slot)
        except (ValueError, TypeError):
            slot_time = 0   # expected for placeholder values like "--:--"

        raw_flight = data.get("f_num", 0)
        try:
            flight_num = int(raw_flight)
        except (ValueError, TypeError):
            flight_num = 0   # expected for placeholder values like "-"

        return cls(
            section=data["sect"],
            time_s=data["time_s"],
            slot_time=slot_time,
            no_fly=bool(data.get("no_fly", False)),
            round_num=str(data.get("r_num", "")),
            group_letter=str(data.get("g_let", "")),
            flight_num=flight_num,
            task_name=task_name,
        )


# ---------------------------------------------------------------------------
# Font library
# ---------------------------------------------------------------------------

class FontLibrary:
    """Loads BDF fonts from disk and provides them by logical name."""

    def __init__(self, base_path: str) -> None:
        self._base_path = base_path
        self._fonts: Dict[str, graphics.Font] = {}

    def load(self, name: str, filename: str) -> None:
        """Load a font file and register it under *name*."""
        path = f"{self._base_path}/{filename}"
        font = graphics.Font()
        try:
            font.LoadFont(path)
        except Exception as exc:
            logger.error("Failed to load font '%s' from '%s': %s", name, path, exc)
            raise
        self._fonts[name] = font
        logger.debug("Loaded font '%s' from '%s'", name, path)

    def get(self, name: str) -> graphics.Font:
        """Return a loaded font by name, raising KeyError if not found."""
        try:
            return self._fonts[name]
        except KeyError:
            logger.error("Font '%s' has not been loaded", name)
            raise


# ---------------------------------------------------------------------------
# Matrix controller
# ---------------------------------------------------------------------------

class MatrixController:
    """Wraps RGBMatrix and its offscreen canvas, managing initialisation
    and double-buffered rendering."""

    def __init__(self, config: MatrixConfig) -> None:
        self._config = config
        self._matrix: Optional[RGBMatrix] = None
        self._canvas = None

    def initialize(self) -> None:
        """Create and configure the RGBMatrix.  Raises on failure."""
        options = RGBMatrixOptions()
        options.rows = self._config.rows
        options.cols = self._config.cols
        options.chain_length = self._config.chain_length
        options.parallel = self._config.parallel
        options.brightness = self._config.brightness
        options.multiplexing = self._config.multiplexing
        options.gpio_slowdown = self._config.gpio_slowdown
        options.row_address_type = self._config.row_address_type
        options.pwm_lsb_nanoseconds = self._config.pwm_lsb_nanoseconds
        options.pwm_bits = self._config.pwm_bits
        options.hardware_mapping = self._config.hardware_mapping
        try:
            self._matrix = RGBMatrix(options=options)
            self._canvas = self._matrix.CreateFrameCanvas()
            logger.info("RGB matrix initialised (%dx%d, chain=%d, parallel=%d)",
                        self._config.cols, self._config.rows,
                        self._config.chain_length, self._config.parallel)
        except Exception as exc:
            logger.error("Failed to initialise RGB matrix: %s", exc)
            raise

    def clear_canvas(self) -> None:
        """Erase the offscreen canvas (does not affect the visible display)."""
        if self._canvas is not None:
            self._canvas.Clear()

    def swap(self) -> None:
        """Flip the offscreen canvas onto the display (vsync-safe)."""
        if self._matrix is not None and self._canvas is not None:
            self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def full_clear(self) -> None:
        """Blank both the canvas and the live display."""
        if self._canvas is not None:
            self._canvas.Clear()
        if self._matrix is not None:
            self._matrix.Clear()

    @property
    def canvas(self):
        """The current offscreen canvas to draw onto."""
        return self._canvas


# ---------------------------------------------------------------------------
# Pilot registry
# ---------------------------------------------------------------------------

class PilotRegistry:
    """Stores pilot id → display name mappings received over serial."""

    def __init__(self) -> None:
        self._pilots: Dict[str, str] = {}

    def register(self, pilot_id: str, name: str) -> None:
        self._pilots[pilot_id] = name
        logger.debug("Registered pilot id='%s' name='%s'", pilot_id, name)

    def get_name(self, pilot_id: str) -> str:
        name = self._pilots.get(pilot_id)
        if name is None:
            logger.warning("Unknown pilot id '%s'", pilot_id)
            return f"? ({pilot_id})"
        return name

    def resolve_list(self, pilot_ids: List[str]) -> List[str]:
        return [self.get_name(pid) for pid in pilot_ids]


# ---------------------------------------------------------------------------
# Pilot list store
# ---------------------------------------------------------------------------

class PilotListStore:
    """
    Shared store for the pilot list of the current flying group.

    Written by the main loop when a 'p_list' packet arrives; read by
    PrepRenderer to decide whether to show the pilot list or the countdown
    timer during preparation time.
    """

    def __init__(self) -> None:
        self.pilot_ids: List[str] = []
        self._received_at: float = 0.0

    def update(self, pilot_ids: List[str]) -> None:
        """Replace the stored list and record the receipt timestamp."""
        self.pilot_ids = list(pilot_ids)
        self._received_at = time.time()
        logger.debug("Pilot list updated: %d pilots", len(self.pilot_ids))

    def clear(self) -> None:
        """Discard the stored list (e.g. when the flying group changes)."""
        self.pilot_ids = []
        self._received_at = 0.0
        logger.debug("Pilot list cleared")

    def age(self) -> float:
        """Seconds elapsed since the pilot list was last updated."""
        if not self._received_at:
            return float("inf")
        return time.time() - self._received_at


# ---------------------------------------------------------------------------
# Renderer base class and concrete renderers
# ---------------------------------------------------------------------------

class BaseRenderer(ABC):
    """Abstract renderer — subclasses implement a specific section layout."""

    def __init__(self, fonts: FontLibrary, config: DisplayConfig) -> None:
        self._fonts = fonts
        self._cfg = config

    @abstractmethod
    def render(self, canvas, data) -> None:
        """Draw this section's layout onto *canvas* using *data*."""

    def needs_render(self) -> bool:
        """Return True if this renderer needs immediate re-rendering for animation."""
        return False

    # ------------------------------------------------------------------
    # Shared drawing helpers used by multiple section renderers
    # ------------------------------------------------------------------

    def _draw_large_time(self, canvas, minutes: str, seconds: str,
                         color: graphics.Color) -> None:
        """Draw MM : SS in the large time font."""
        font = self._fonts.get("time")
        graphics.DrawText(canvas, font, 0, self._cfg.time_row_y, color, minutes)
        graphics.DrawText(canvas, font, self._cfg.colon_x, self._cfg.colon_y, color, ":")
        graphics.DrawText(canvas, font, self._cfg.time_sec_x, self._cfg.time_sec_y, color, seconds)

    def _draw_header(self, canvas, left_label: str, right_label: str,
                     left_color: graphics.Color,
                     right_color: Optional[graphics.Color] = None) -> None:
        """Draw a small header row with a left label and an optional right label."""
        font = self._fonts.get("6x12")
        if right_color is None:
            right_color = graphics.Color(255, 255, 255)
        graphics.DrawText(canvas, font, self._cfg.header_left_x,
                          self._cfg.header_y, left_color, left_label)
        if right_label:
            graphics.DrawText(canvas, font, self._cfg.header_right_x,
                              self._cfg.header_y, right_color, right_label)

    def _draw_task_name(self, canvas, task_name: str) -> None:
        """Draw the task name in the small label font."""
        font = self._fonts.get("6x9")
        graphics.DrawText(canvas, font, 0, self._cfg.task_name_y,
                          graphics.Color(255, 255, 255), task_name)

    @staticmethod
    def _round_group_label(data: TimingData) -> str:
        return f"R:{data.round_num} Gr:{data.group_letter}"

    _KR_SWEEP_SECS: float = 1.5  # duration of one left-to-right knight-rider pass

    def _draw_knight_rider(self, canvas) -> None:
        """Draw a Knight Rider oscillating red bar across the bottom two rows."""
        w = self._cfg.display_width
        h = self._cfg.display_height

        # Bounce: phase 0→1 = left→right, phase 1→2 = right→left
        phase = (time.time() / self._KR_SWEEP_SECS) % 2.0
        pos = phase if phase <= 1.0 else 2.0 - phase
        cx = int(pos * (w - 1))

        # Brightness gradient; index = pixel distance from the bright centre
        colours = [(255, 0, 0), (160, 0, 0), (60, 0, 0), (15, 0, 0)]
        half = len(colours) - 1

        for y in range(h - 2, h):          # bottom two rows
            for dx in range(-half, half + 1):
                px = cx + dx
                if 0 <= px < w:
                    canvas.SetPixel(px, y, *colours[abs(dx)])


# --- Idle / status renderers ------------------------------------------------

class BootRenderer(BaseRenderer):
    """Splash screen shown at startup before any serial data is received."""

    def needs_render(self) -> bool:
        return True

    def render(self, canvas, data) -> None:
        title_font = self._fonts.get("9x18B")
        sub_font = self._fonts.get("6x9")
        graphics.DrawText(canvas, title_font,
                          self._cfg.boot_title_x, self._cfg.boot_title_y,
                          graphics.Color(0, 255, 0), "Superfly")
        graphics.DrawText(canvas, sub_font,
                          self._cfg.boot_title_x, self._cfg.boot_subtitle_y + 17,
                          graphics.Color(0, 255, 255), "Display Ready")


class NoDataRenderer(BaseRenderer):
    """Shown when no serial data has been received for the timeout period."""

    def needs_render(self) -> bool:
        return True

    def render(self, canvas, data) -> None:
        title_font = self._fonts.get("9x18B")
        sub_font = self._fonts.get("6x9")
        graphics.DrawText(canvas, title_font,
                          self._cfg.boot_title_x, self._cfg.boot_title_y,
                          graphics.Color(255, 0, 0), "Superfly")
        graphics.DrawText(canvas, sub_font,
                          self._cfg.boot_title_x + 3, self._cfg.boot_subtitle_y + 17,
                          graphics.Color(0, 255, 255), "Waiting for")        
        graphics.DrawText(canvas, sub_font,
                          self._cfg.boot_title_x + 3, self._cfg.boot_subtitle_y + 17 + 10,
                          graphics.Color(0, 255, 255), "data...")        

        self._draw_knight_rider(canvas)


# --- Competition section renderers ------------------------------------------

class TimeOfDayRenderer(BaseRenderer):
    """Displays wall-clock time (HH:MM)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 0, 255)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "TIME OF DAY", "", color)


class WaitingRenderer(BaseRenderer):
    """Countdown while waiting for the next group to begin."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 0, 255)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "WAIT", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


class AnnouncementRenderer(BaseRenderer):
    """Displayed while the announcer is reading the next group."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 0, 255)
        self._draw_header(canvas, "SPEAK", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


class PrepRenderer(BaseRenderer):
    """
    Preparation time renderer.

    The display cycles indefinitely between a pilot-list view and a countdown
    timer view for the duration of the Preparation section:

        ┌────────────────┐  ┌────────┐  ┌────────────────┐  …
        │ pilot list 15 s │  │ timer 5 s│  │ pilot list 15 s │
        └────────────────┘  └────────┘  └────────────────┘

    When the group has more than ``PILOTS_PER_PAGE`` pilots the list is split
    into pages.  Each page is held for ``PAGE_HOLD_SECS`` seconds; a
    horizontal-wipe then slides the current page out to the left while the
    next page slides in from the right over ``WIPE_SECS`` seconds.
    Page cycling restarts at the beginning of each pilot-list window.
    Animation is driven by the main loop calling ``render()`` at up to 60 fps
    whenever ``needs_render()`` returns True — no blocking sleep is used.
    """

    PILOTS_PER_PAGE: int = 5
    TIMER_SHOW_SECS: float = 5.0    # countdown timer visible per cycle
    PAGE_HOLD_SECS: float = 5.0     # seconds each page is held; total pilot window = pages × this
    WIPE_SECS: float = 0.4          # wipe transition duration

    def __init__(self, fonts: FontLibrary, config: DisplayConfig,
                 registry: PilotRegistry, pilot_list: PilotListStore) -> None:
        super().__init__(fonts, config)
        self._registry = registry
        self._pilot_list = pilot_list

    # ------------------------------------------------------------------
    # BaseRenderer interface
    # ------------------------------------------------------------------

    def render(self, canvas, data: TimingData) -> None:
        if self._pilot_list.pilot_ids:
            pilot_show_secs = self._pilot_show_secs()
            display_cycle = pilot_show_secs + self.TIMER_SHOW_SECS
            cycle_pos = self._pilot_list.age() % display_cycle
            if cycle_pos < pilot_show_secs:
                pages = self._pages()
                if len(pages) > 1:
                    self._render_paged(canvas, data, pages)
                else:
                    self._render_page(canvas, data, pages[0] if pages else [],
                                      x_offset=0)
            else:
                self._render_timer(canvas, data)
        else:
            self._render_timer(canvas, data)

    def needs_render(self) -> bool:
        """True while a page-wipe is in progress within the pilot-list window."""
        if not self._pilot_list.pilot_ids or len(self._pages()) <= 1:
            return False
        pilot_show_secs = self._pilot_show_secs()
        display_cycle = pilot_show_secs + self.TIMER_SHOW_SECS
        cycle_pos = self._pilot_list.age() % display_cycle
        if cycle_pos >= pilot_show_secs:
            return False  # currently showing the timer — no animation needed
        page_cycle_pos = cycle_pos % (self.PAGE_HOLD_SECS + self.WIPE_SECS)
        return page_cycle_pos >= self.PAGE_HOLD_SECS

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pages(self) -> List[List[str]]:
        ids = self._pilot_list.pilot_ids
        return [ids[i:i + self.PILOTS_PER_PAGE]
                for i in range(0, len(ids), self.PILOTS_PER_PAGE)]

    def _pilot_show_secs(self) -> float:
        """Total seconds the pilot list occupies per display cycle.

        Each page is held for PAGE_HOLD_SECS; there are (n-1) wipe transitions
        between the n pages.  The final page is never wiped — it simply holds
        until the timer window takes over.
        """
        n = len(self._pages())
        return n * self.PAGE_HOLD_SECS + (n - 1) * self.WIPE_SECS

    def _render_timer(self, canvas, data: TimingData) -> None:
        color = graphics.Color(0, 255, 255)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "PREP", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)

    def _render_paged(self, canvas, data: TimingData,
                      pages: List[List[str]]) -> None:
        """Render the correct page; animate a horizontal wipe when transitioning.

        Uses the position within the current *pilot-list window* (0…pilot_show_secs)
        so that page cycling always restarts from page 0 each time the pilot
        list re-appears after the timer interlude.
        """
        pilot_show_secs = self._pilot_show_secs()
        display_cycle = pilot_show_secs + self.TIMER_SHOW_SECS
        # Position within the current pilot-list window (0 … pilot_show_secs)
        pilot_age = self._pilot_list.age() % display_cycle

        page_cycle = self.PAGE_HOLD_SECS + self.WIPE_SECS
        page_idx = int(pilot_age / page_cycle) % len(pages)
        page_cycle_pos = pilot_age % page_cycle

        if page_cycle_pos < self.PAGE_HOLD_SECS:
            # Steady state — show current page
            self._render_page(canvas, data, pages[page_idx], x_offset=0,
                              page_num=page_idx, total_pages=len(pages))
        else:
            # Wipe — current page slides left, next slides in from the right
            progress = min((page_cycle_pos - self.PAGE_HOLD_SECS) / self.WIPE_SECS, 1.0)
            offset_px = int(progress * self._cfg.display_width)
            next_idx = (page_idx + 1) % len(pages)
            self._render_page(canvas, data, pages[page_idx],
                              x_offset=-offset_px,
                              page_num=page_idx, total_pages=len(pages))
            self._render_page(canvas, data, pages[next_idx],
                              x_offset=self._cfg.display_width - offset_px,
                              page_num=next_idx, total_pages=len(pages))

    def _render_page(self, canvas, data: TimingData, pilot_ids: List[str],
                     x_offset: int = 0,
                     page_num: int = 0, total_pages: int = 1) -> None:
        """Draw one page of pilots onto *canvas* shifted by *x_offset* pixels.

        Pixels that land outside [0, display_width) are silently ignored by
        both the hardware driver and the simulator, so clipping is free.
        """
        w = self._cfg.display_width
        # Skip entirely when the page is fully off-screen
        if x_offset <= -w or x_offset >= w:
            return

        font_hdr = self._fonts.get("6x12")
        font_name = self._fonts.get("6x9")

        graphics.DrawText(canvas, font_hdr, x_offset, self._cfg.header_y,
                          graphics.Color(255, 255, 0), "Pilots")
        if total_pages > 1:
            page_label = f"{page_num + 1}/{total_pages}"
            graphics.DrawText(canvas, font_hdr, x_offset + 40, self._cfg.header_y,
                              graphics.Color(200, 200, 200), page_label)
        else:
            graphics.DrawText(canvas, font_hdr, x_offset + 40, self._cfg.header_y,
                              graphics.Color(255, 255, 255),
                              self._round_group_label(data))

        y = self._cfg.pilot_list_start_y
        for pid in pilot_ids:
            name = self._registry.get_name(pid)
            graphics.DrawText(canvas, font_name, x_offset, y,
                              graphics.Color(255, 255, 255), name)
            y += self._cfg.pilot_list_line_height


class NoFlyRenderer(BaseRenderer):
    """No-fly window countdown (red)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 0, 0)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "NOFLY", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


class WorkRenderer(BaseRenderer):
    """Working window countdown (green)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(0, 255, 0)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "WORK", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


class LandRenderer(BaseRenderer):
    """Landing window countdown (yellow)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 255, 0)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "LAND", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)

class TestRenderer(BaseRenderer):
    """Test window countdown (yellow)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(255, 255, 0)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "TEST", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


# ---------------------------------------------------------------------------
# Display router
# ---------------------------------------------------------------------------

class DisplayRouter:
    """Maps competition section names to their renderer instances."""

    def __init__(self) -> None:
        self._routes: Dict[str, BaseRenderer] = {}
        self._default: Optional[BaseRenderer] = None

    def register(self, section: str, renderer: BaseRenderer) -> None:
        self._routes[section] = renderer
        logger.debug("Registered renderer for section '%s'", section)

    def set_default(self, renderer: BaseRenderer) -> None:
        self._default = renderer

    def get(self, section: str) -> Optional[BaseRenderer]:
        renderer = self._routes.get(section)
        if renderer is None:
            logger.warning("No renderer registered for section '%s'", section)
            return self._default
        return renderer


# ---------------------------------------------------------------------------
# Serial reader
# ---------------------------------------------------------------------------

class SerialReader:
    """Manages a serial port connection and decodes newline-delimited JSON."""

    def __init__(self, config: SerialConfig) -> None:
        self._config = config
        self._port: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Open the serial port.  Raises serial.SerialException on failure."""
        try:
            self._port = serial.Serial(
                self._config.port,
                self._config.baud_rate,
                timeout=self._config.timeout,
            )
            logger.info("Opened serial port %s at %d baud",
                        self._config.port, self._config.baud_rate)
        except serial.SerialException as exc:
            logger.error("Cannot open serial port '%s': %s",
                         self._config.port, exc)
            raise

    def disconnect(self) -> None:
        if self._port and self._port.is_open:
            self._port.close()
            logger.info("Serial port %s closed", self._config.port)

    def has_data(self) -> bool:
        """Return True if at least one byte is waiting in the input buffer."""
        try:
            return bool(self._port and self._port.in_waiting > 0)
        except serial.SerialException as exc:
            logger.error("Serial error checking in_waiting: %s", exc)
            return False

    def read_json(self) -> Optional[dict]:
        """
        Read one line from the serial port and return its parsed JSON object.
        Returns None on decode error, JSON error, serial error, or empty line.
        """
        if not self._port:
            return None
        raw = b""
        try:
            raw = self._port.readline()
        except serial.SerialException as exc:
            logger.error("Serial read error: %s", exc)
            return None

        if not raw:
            return None

        try:
            line = raw.decode("utf-8").rstrip()
        except UnicodeDecodeError as exc:
            logger.warning("Could not decode serial bytes as UTF-8: %s", exc)
            return None

        if not line:
            return None

        logger.debug("Serial RX: %s", line)

        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse error on line '%s': %s", line, exc)
            return None

    def flush_input(self) -> None:
        """Discard any bytes currently in the input buffer."""
        if self._port and self._port.is_open:
            self._port.reset_input_buffer()
            logger.debug("Serial input buffer flushed")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class MatrixDisplayApp:
    """
    Orchestrates serial input, pilot registry, display routing, and the
    main event loop.
    """

    def __init__(
        self,
        serial_config: SerialConfig,
        matrix_config: MatrixConfig,
        display_config: DisplayConfig,
    ) -> None:
        self._display_cfg = display_config
        self._log = logging.getLogger(self.__class__.__name__)

        self._fonts = FontLibrary(display_config.font_base_path)
        self._matrix = MatrixController(matrix_config)
        self._serial = SerialReader(serial_config)
        self._startup_delay: float = serial_config.startup_delay
        self._pilots = PilotRegistry()
        self._router = DisplayRouter()

        # Track round/group across packet types
        self._last_round_num: str = ""
        self._last_group_letter: str = ""
        self._last_data_time: float = 0.0

        # Deduplication: (section, slot_time) pair of the last rendered frame
        self._last_rendered_key: Optional[tuple] = None

        # Active renderer + its last data — used to drive animation re-renders
        self._active_renderer: Optional[BaseRenderer] = None
        self._active_data: Optional[TimingData] = None

        # Shared pilot list store — written by the loop, read by PrepRenderer
        self._pilot_list_store = PilotListStore()

        # Cached renderer references for states not keyed by section name
        self._boot_renderer: Optional[BaseRenderer] = None
        self._no_data_renderer: Optional[BaseRenderer] = None

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_fonts(self) -> None:
        font_map = {
            "time":  "matrix_time-40.bdf",
            "6x12":  "clR6x12.bdf",
            "6x9":   "6x9.bdf",
            "9x18B": "9x18B.bdf",
        }
        for name, filename in font_map.items():
            self._fonts.load(name, filename)
        logger.info("All fonts loaded")

    def _setup_routes(self) -> None:
        fonts = self._fonts
        cfg = self._display_cfg
        pilots = self._pilots

        section_renderers: Dict[str, BaseRenderer] = {
            "Actual Time HH:MM":        TimeOfDayRenderer(fonts, cfg),
            "Waiting for next group":   WaitingRenderer(fonts, cfg),
            "Announcement in progress": AnnouncementRenderer(fonts, cfg),
            "Preparation Time":         PrepRenderer(fonts, cfg, pilots, self._pilot_list_store),
            "No Fly Time":              NoFlyRenderer(fonts, cfg),
            "Working Time":             WorkRenderer(fonts, cfg),
            "Landing Window":           LandRenderer(fonts, cfg),
            "Test Flying Time":         TestRenderer(fonts, cfg),
        }
        for section, renderer in section_renderers.items():
            self._router.register(section, renderer)

        self._boot_renderer = BootRenderer(fonts, cfg)
        self._no_data_renderer = NoDataRenderer(fonts, cfg)
        logger.info("Display routes configured (%d sections)", len(section_renderers))

    def initialize(self) -> None:
        """Load fonts, initialise hardware, and register renderers."""
        logger.info("Initialising MatrixDisplayApp")
        self._load_fonts()
        self._matrix.initialize()
        self._setup_routes()
        # Serial port is opened in run() so the boot animation plays first.

    def shutdown(self) -> None:
        """Release hardware resources."""
        logger.info("Shutting down MatrixDisplayApp")
        self._serial.disconnect()
        self._matrix.full_clear()

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_and_swap(self, renderer: BaseRenderer, data) -> None:
        self._matrix.clear_canvas()
        renderer.render(self._matrix.canvas, data)
        self._matrix.swap()

    def _show_boot_screen(self) -> None:
        self._active_renderer = self._boot_renderer
        self._active_data = None
        self._render_and_swap(self._boot_renderer, None)
        logger.info("Boot screen displayed")

    def _show_no_data_screen(self) -> None:
        self._active_renderer = self._no_data_renderer
        self._active_data = None
        self._render_and_swap(self._no_data_renderer, None)
        logger.warning("No serial data for %.0fs — showing no-data screen",
                       self._display_cfg.no_data_timeout)

    # ------------------------------------------------------------------
    # Packet handlers
    # ------------------------------------------------------------------

    def _handle_time_packet(self, payload: dict) -> None:
        try:
            timing = TimingData.from_dict(payload)
        except KeyError as exc:
            self._log.warning("Missing field in 'time' packet: %s — payload: %s", exc, payload)
            return
        except (TypeError, ValueError) as exc:
            self._log.warning("Invalid value in 'time' packet: %s — payload: %s", exc, payload)
            return

        # Clear the stale pilot list whenever the flying group changes so that
        # PrepRenderer shows the timer (not the previous group's names) while
        # waiting for the new p_list packet to arrive.
        if (timing.round_num != self._last_round_num
                or timing.group_letter != self._last_group_letter):
            self._pilot_list_store.clear()
            self._last_rendered_key = None
            self._log.info(
                "Group changed (R:%s G:%s \u2192 R:%s G:%s) \u2014 pilot list cleared",
                self._last_round_num, self._last_group_letter,
                timing.round_num, timing.group_letter,
            )

        self._last_round_num = timing.round_num
        self._last_group_letter = timing.group_letter

        renderer = self._router.get(timing.section)
        if renderer is None:
            self._log.warning("No renderer for section '%s'; skipping render",
                              timing.section)
            return

        # Always keep active refs current so the animation loop can re-render
        self._active_renderer = renderer
        self._active_data = timing

        render_key = (timing.section, timing.slot_time)
        if render_key == self._last_rendered_key and not renderer.needs_render():
            self._log.debug("Skipping duplicate frame: section='%s' slot_time=%d",
                            timing.section, timing.slot_time)
            return

        self._log.debug("Rendering section '%s' slot_time=%d",
                        timing.section, timing.slot_time)
        self._render_and_swap(renderer, timing)
        self._last_rendered_key = render_key

    def _handle_pilot_def(self, payload: dict) -> None:
        try:
            pilot_id = str(payload["id"])
            name = str(payload["name"])
        except KeyError as exc:
            self._log.warning("Missing field in 'p_def' packet: %s", exc)
            return
        self._log.info("Registering pilot: id='%s' name='%s'", pilot_id, name)
        self._pilots.register(pilot_id, name)

    def _handle_pilot_list(self, payload) -> None:
        if not isinstance(payload, list):
            self._log.warning(
                "Expected list payload for 'p_list', got %s", type(payload).__name__
            )
            return
        self._pilot_list_store.update([str(pid) for pid in payload])
        # Clear the dedup key so the next time packet triggers an immediate
        # re-render to show the pilot list rather than waiting for slot_time
        # to change.
        self._last_rendered_key = None
        self._log.info("Stored pilot list (%d pilots); PrepRenderer will display it",
                       len(payload))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _is_data_timed_out(self) -> bool:
        return time.time() - self._last_data_time >= self._display_cfg.no_data_timeout

    def run(self) -> None:
        """
        Blocking main loop.  Reads serial packets, dispatches them to the
        appropriate handler, and manages the no-data timeout screen.
        """
        self._last_data_time = time.time()   # start the no-data timeout clock
        self._show_boot_screen()

        # Startup delay — animate the boot screen while waiting for the serial
        # device to become ready (e.g. a microcontroller that needs time to boot).
        if self._startup_delay > 0:
            logger.info("Startup delay: %.1f s", self._startup_delay)
            deadline = time.time() + self._startup_delay
            while time.time() < deadline:
                if self._active_renderer is not None and self._active_renderer.needs_render():
                    self._render_and_swap(self._active_renderer, self._active_data)
                time.sleep(0.016)

        self._serial.connect()

        no_data_displayed = False
        was_animating = False   # tracks whether the previous iteration was animating
        logger.info("Entering main display loop — press CTRL-C to stop")

        while True:
            # -- Timeout check -------------------------------------------
            if self._is_data_timed_out() and not no_data_displayed:
                self._show_no_data_screen()
                no_data_displayed = True

            # -- Wait for data (small sleep avoids CPU spin when idle) ----
            if not self._serial.has_data():
                # Drive animation frames (e.g. pilot-list page wipes) even
                # when no new serial packet has arrived.
                #
                # When needs_render() goes False we render ONE extra frame so
                # the display lands cleanly at the fully-completed wipe position
                # rather than freezing a few pixels short of the destination
                # (was_animating catches the True→False transition).
                animating = (self._active_renderer is not None
                             and self._active_renderer.needs_render())
                if animating or was_animating:
                    if self._active_renderer is not None:
                        self._render_and_swap(self._active_renderer, self._active_data)
                    time.sleep(0.016)  # cap at ~60 fps
                else:
                    time.sleep(0.01)
                was_animating = animating
                continue

            # -- Read and parse packet ------------------------------------
            packet = self._serial.read_json()
            if packet is None:
                continue

            msg_type = packet.get("t")
            payload = packet.get("d")

            if msg_type is None or payload is None:
                self._log.warning("Malformed packet (missing 't' or 'd'): %s", packet)
                continue

            # Reset no-data state on any valid packet
            self._last_data_time = time.time()
            if no_data_displayed:
                logger.info("Serial data resumed")
                no_data_displayed = False

            # -- Dispatch -------------------------------------------------
            if msg_type == "time":
                self._handle_time_packet(payload)

            elif msg_type == "p_def":
                self._handle_pilot_def(payload)

            elif msg_type == "p_list":
                self._handle_pilot_list(payload)

            else:
                self._log.info("Unrecognised packet type '%s'", msg_type)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    serial_config = SerialConfig(
        #port="/dev/ttyUSB0",
        #baud_rate=19200,
        port="COM4",
        baud_rate=19200,
        startup_delay=3.0,
        timeout=0.3,
    )
    matrix_config = MatrixConfig(
        rows=16,
        cols=32,
        chain_length=3,
        parallel=3,
        brightness=100,
        multiplexing=5,
        gpio_slowdown=3,
        row_address_type=2,
        pwm_lsb_nanoseconds=80,
        pwm_bits=1,
        hardware_mapping="regular",
    )
    display_config = DisplayConfig(
        font_base_path="../fonts",
        no_data_timeout=30.0,
        pilot_list_display_time=15.0,
        time_row_y=48,
        display_width=matrix_config.cols * matrix_config.chain_length,
        display_height=matrix_config.rows * matrix_config.parallel,
    )

    app = MatrixDisplayApp(serial_config, matrix_config, display_config)
    try:
        app.initialize()
        app.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down")
    except serial.SerialException as exc:
        logger.error("Serial port error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected fatal error: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
