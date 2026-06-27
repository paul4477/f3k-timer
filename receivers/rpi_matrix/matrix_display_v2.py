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
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# ---------------------------------------------------------------------------
# Logging — write to stderr at DEBUG level by default; callers may override.
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SerialConfig:
    """Serial port connection parameters."""
    port: str = "/dev/ttyUSB0"
    baud_rate: int = 19200
    timeout: float = 0.3


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
    colon_x: int = 45                   # x-position of the colon separator
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
    boot_title_y: int = 32
    boot_subtitle_y: int = 8


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
        return cls(
            section=data["sect"],
            time_s=data["time_s"],
            slot_time=int(data["slot_time"]),
            no_fly=bool(data.get("no_fly", False)),
            round_num=str(data.get("r_num", "")),
            group_letter=str(data.get("g_let", "")),
            flight_num=int(data.get("f_num", 0)),
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


# --- Idle / status renderers ------------------------------------------------

class BootRenderer(BaseRenderer):
    """Splash screen shown at startup before any serial data is received."""

    def render(self, canvas, data) -> None:
        title_font = self._fonts.get("9x18B")
        sub_font = self._fonts.get("6x9")
        graphics.DrawText(canvas, title_font,
                          self._cfg.boot_title_x, self._cfg.boot_title_y,
                          graphics.Color(0, 255, 0), "Superfly")
        graphics.DrawText(canvas, sub_font,
                          0, self._cfg.boot_subtitle_y,
                          graphics.Color(0, 255, 255), "Display Ready")


class NoDataRenderer(BaseRenderer):
    """Shown when no serial data has been received for the timeout period."""

    def render(self, canvas, data) -> None:
        title_font = self._fonts.get("9x18B")
        graphics.DrawText(canvas, title_font,
                          self._cfg.boot_title_x, self._cfg.boot_title_y,
                          graphics.Color(255, 0, 0), "Superfly")


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
    """Preparation time countdown (cyan)."""

    def render(self, canvas, data: TimingData) -> None:
        color = graphics.Color(0, 255, 255)
        self._draw_large_time(canvas, data.time_minutes, data.time_seconds, color)
        self._draw_header(canvas, "PREP", self._round_group_label(data), color)
        self._draw_task_name(canvas, data.task_name)


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


class PilotListRenderer(BaseRenderer):
    """Scrolls through the list of pilots flying in the upcoming group."""

    def __init__(self, fonts: FontLibrary, config: DisplayConfig,
                 registry: PilotRegistry) -> None:
        super().__init__(fonts, config)
        self._registry = registry

    def render(self, canvas, data: dict) -> None:
        """
        *data* keys:
            pilot_ids   : list[str]
            round_num   : str
            group_letter: str
        """
        font_hdr = self._fonts.get("6x12")
        font_name = self._fonts.get("6x9")
        pilot_ids: List[str] = data.get("pilot_ids", [])
        round_num: str = data.get("round_num", "")
        group_letter: str = data.get("group_letter", "")

        graphics.DrawText(canvas, font_hdr, 0, self._cfg.header_y,
                          graphics.Color(255, 255, 0), "Pilots")
        graphics.DrawText(canvas, font_hdr, 40, self._cfg.header_y,
                          graphics.Color(255, 255, 255),
                          f"R:{round_num} Gr:{group_letter}")

        y = self._cfg.pilot_list_start_y
        for pilot_id in pilot_ids:
            name = self._registry.get_name(pilot_id)
            graphics.DrawText(canvas, font_name, 0, y,
                              graphics.Color(255, 255, 255), name)
            y += self._cfg.pilot_list_line_height


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
        self._pilots = PilotRegistry()
        self._router = DisplayRouter()

        # Track round/group across packet types (p_list needs last time values)
        self._last_round_num: str = ""
        self._last_group_letter: str = ""
        self._last_data_time: float = 0.0

        # Deduplication: (section, slot_time) pair of the last rendered frame
        self._last_rendered_key: Optional[tuple] = None

        # Cached renderer references for states not keyed by section name
        self._boot_renderer: Optional[BaseRenderer] = None
        self._no_data_renderer: Optional[BaseRenderer] = None
        self._pilot_list_renderer: Optional[PilotListRenderer] = None

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
            "Preparation Time":         PrepRenderer(fonts, cfg),
            "No Fly Time":              NoFlyRenderer(fonts, cfg),
            "Working Time":             WorkRenderer(fonts, cfg),
            "Landing Window":           LandRenderer(fonts, cfg),
        }
        for section, renderer in section_renderers.items():
            self._router.register(section, renderer)

        self._boot_renderer = BootRenderer(fonts, cfg)
        self._no_data_renderer = NoDataRenderer(fonts, cfg)
        self._pilot_list_renderer = PilotListRenderer(fonts, cfg, pilots)
        logger.info("Display routes configured (%d sections)", len(section_renderers))

    def initialize(self) -> None:
        """Load fonts, initialise hardware, and open the serial port."""
        logger.info("Initialising MatrixDisplayApp")
        self._load_fonts()
        self._matrix.initialize()
        self._setup_routes()
        self._serial.connect()

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
        self._render_and_swap(self._boot_renderer, None)
        logger.info("Boot screen displayed")

    def _show_no_data_screen(self) -> None:
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
            self._log.warning("Missing field in 'time' packet: %s", exc)
            return
        except (TypeError, ValueError) as exc:
            self._log.warning("Invalid value in 'time' packet: %s", exc)
            return

        self._last_round_num = timing.round_num
        self._last_group_letter = timing.group_letter

        render_key = (timing.section, timing.slot_time)
        if render_key == self._last_rendered_key:
            self._log.debug("Skipping duplicate frame: section='%s' slot_time=%d",
                            timing.section, timing.slot_time)
            return

        renderer = self._router.get(timing.section)
        if renderer is None:
            self._log.warning("No renderer for section '%s'; skipping render",
                              timing.section)
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
        self._pilots.register(pilot_id, name)

    def _handle_pilot_list(self, payload) -> None:
        if not isinstance(payload, list):
            self._log.warning(
                "Expected list payload for 'p_list', got %s", type(payload).__name__
            )
            return

        data = {
            "pilot_ids":    [str(pid) for pid in payload],
            "round_num":    self._last_round_num,
            "group_letter": self._last_group_letter,
        }
        self._render_and_swap(self._pilot_list_renderer, data)
        time.sleep(self._display_cfg.pilot_list_display_time)
        self._serial.flush_input()

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

        no_data_displayed = False
        logger.info("Entering main display loop — press CTRL-C to stop")

        while True:
            # -- Timeout check -------------------------------------------
            if self._is_data_timed_out() and not no_data_displayed:
                self._show_no_data_screen()
                no_data_displayed = True

            # -- Wait for data (small sleep avoids CPU spin when idle) ----
            if not self._serial.has_data():
                time.sleep(0.01)
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
        port="/dev/ttyUSB0",
        baud_rate=19200,
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
