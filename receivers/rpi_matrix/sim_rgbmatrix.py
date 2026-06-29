"""
sim_rgbmatrix.py — Pygame-based simulator for the rgbmatrix Python API.

Provides drop-in replacements for:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

Each logical LED is rendered as a coloured filled circle on a dark background.
Off LEDs are shown as dim dots so the panel outline is always visible.

Activate by passing ``--simulate`` on the command line, or automatically when
the real ``rgbmatrix`` package is not installed.

Visual tuning constants near the top of this file:
    _LED_RADIUS  — pixel radius of each simulated LED circle
    _LED_GAP     — gap in pixels between adjacent LED circles
"""

from __future__ import annotations

import logging
import sys
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pygame
except ImportError as exc:
    raise ImportError(
        "pygame is required for the matrix simulator.  "
        "Install it with:  pip install pygame"
    ) from exc


# ---------------------------------------------------------------------------
# Visual constants — adjust to taste
# ---------------------------------------------------------------------------

_LED_RADIUS: int = 4                              # radius of each simulated LED
_LED_GAP: int = 2                                 # gap between LED circles
_LED_STEP: int = _LED_RADIUS * 2 + _LED_GAP      # centre-to-centre pitch

_BG_COLOR: Tuple[int, int, int] = (15, 15, 15)   # window background
_OFF_COLOR: Tuple[int, int, int] = (35, 35, 35)  # unlit LED colour


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

class Color:
    """Drop-in replacement for ``rgbmatrix.graphics.Color``."""

    __slots__ = ("r", "g", "b")

    def __init__(self, r: int = 0, g: int = 0, b: int = 0) -> None:
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)

    def __repr__(self) -> str:
        return f"Color({self.r}, {self.g}, {self.b})"


# ---------------------------------------------------------------------------
# BDF font parser
# ---------------------------------------------------------------------------

def _parse_bdf(path: str) -> Tuple[Dict[int, dict], int]:
    """Parse a BDF font file and return ``(glyphs, font_height)``.

    ``glyphs`` maps Unicode codepoint to a glyph-info dict::

        width     : int          horizontal advance in pixels
        bbx_width : int          bounding-box width
        height    : int          bounding-box height
        xoff      : int          x offset: origin → left edge of bbox
        yoff      : int          y offset: origin → bottom of bbox (BDF upward)
        bitmap    : list[int]    one int per row; row 0 is the topmost row

    ``font_height`` is FONT_ASCENT + FONT_DESCENT from the BDF header.
    """
    glyphs: Dict[int, dict] = {}
    font_ascent = 0
    font_descent = 0

    with open(path, "r", errors="replace") as fh:
        lines = fh.readlines()

    in_char = False
    in_bitmap = False
    current_enc: Optional[int] = None
    current: dict = {}
    bitmap_rows: list = []

    for raw in lines:
        line = raw.strip()

        if line.startswith("FONT_ASCENT "):
            font_ascent = int(line.split()[1])
            continue
        if line.startswith("FONT_DESCENT "):
            font_descent = int(line.split()[1])
            continue

        if line.startswith("STARTCHAR"):
            in_char = True
            current = {}
            bitmap_rows = []
            current_enc = None
            in_bitmap = False
            continue

        if not in_char:
            continue

        if line.startswith("ENCODING "):
            current_enc = int(line.split()[1])
        elif line.startswith("DWIDTH "):
            current["width"] = int(line.split()[1])
        elif line.startswith("BBX "):
            parts = line.split()
            current["bbx_width"] = int(parts[1])
            current["height"] = int(parts[2])
            current["xoff"] = int(parts[3])
            current["yoff"] = int(parts[4])
        elif line == "BITMAP":
            in_bitmap = True
        elif in_bitmap:
            if line == "ENDCHAR":
                in_bitmap = False
                in_char = False
                if current_enc is not None and current_enc >= 0:
                    current["bitmap"] = list(bitmap_rows)
                    glyphs[current_enc] = dict(current)
            else:
                try:
                    bitmap_rows.append(int(line, 16))
                except ValueError:
                    bitmap_rows.append(0)

    font_height = (font_ascent + font_descent) if (font_ascent or font_descent) else 16
    return glyphs, font_height


# ---------------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------------

class Font:
    """Drop-in replacement for ``rgbmatrix.graphics.Font``."""

    def __init__(self) -> None:
        self._glyphs: Dict[int, dict] = {}
        self._font_height: int = 16

    def LoadFont(self, path: str) -> None:
        """Load a BDF font file from *path*."""
        try:
            self._glyphs, self._font_height = _parse_bdf(path)
            logger.debug(
                "SimFont loaded '%s'  %d glyphs  height=%d",
                path, len(self._glyphs), self._font_height,
            )
        except Exception as exc:
            logger.error("SimFont: cannot load '%s': %s", path, exc)
            raise

    @property
    def height(self) -> int:
        return self._font_height


# ---------------------------------------------------------------------------
# DrawText
# ---------------------------------------------------------------------------

def DrawText(
    canvas: "SimCanvas",
    font: Font,
    x: int,
    y: int,
    color: Color,
    text: str,
) -> int:
    """Drop-in replacement for ``rgbmatrix.graphics.DrawText``.

    *y* is the **baseline** row (row 0 = top of matrix, increasing downward).

    Returns the total horizontal advance (width of the rendered string in
    pixels), matching the real rgbmatrix behaviour.

    Bit layout for BDF bitmaps
    --------------------------
    Each row is stored as a hex integer.  The most-significant bit of the
    first (leftmost) byte is pixel column 0.  Bytes are padded to
    ``ceil(bbx_width / 8)`` bytes per row.

    Coordinate conversion (BDF → matrix)
    -------------------------------------
    BDF uses upward y; the matrix uses downward pixel rows.  The top-left
    corner of a glyph's bounding box in matrix pixel coordinates is::

        top_row = y_matrix_baseline - yoff_bdf - bbx_height + 1
    """
    if not font._glyphs:
        return 0

    advance = 0
    for ch in text:
        enc = ord(ch)
        glyph = font._glyphs.get(enc)
        if glyph is None:
            space = font._glyphs.get(32)
            advance += space["width"] if space else 6
            continue

        g_w: int = glyph.get("bbx_width", glyph.get("width", 6))
        g_h: int = glyph["height"]
        xoff: int = glyph["xoff"]
        yoff: int = glyph["yoff"]
        bitmap: list = glyph["bitmap"]

        bytes_per_row = (g_w + 7) // 8
        total_bits = bytes_per_row * 8

        # Top-left of bounding box in matrix (downward) pixel coordinates:
        # bitmap row 0 is the topmost BDF row = (yoff + g_h - 1) above baseline
        # → matrix pixel row = y - (yoff + g_h - 1) = y - yoff - g_h + 1
        top_row = y - yoff - g_h + 1

        for row_idx, row_bits in enumerate(bitmap[:g_h]):
            py = top_row + row_idx
            for col_idx in range(g_w):
                # MSB of the leftmost byte = column 0
                bit_pos = total_bits - 1 - col_idx
                if (row_bits >> bit_pos) & 1:
                    px = x + advance + xoff + col_idx
                    canvas.SetPixel(px, py, color.r, color.g, color.b)

        advance += glyph["width"]

    return advance


# ---------------------------------------------------------------------------
# DrawLine
# ---------------------------------------------------------------------------

def DrawLine(
    canvas: "SimCanvas",
    x1: int, y1: int,
    x2: int, y2: int,
    color: Color,
) -> None:
    """Drop-in replacement for ``rgbmatrix.graphics.DrawLine``.

    Draws a straight line from (x1, y1) to (x2, y2) using Bresenham's
    line algorithm.
    """
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    x, y = x1, y1
    while True:
        canvas.SetPixel(x, y, color.r, color.g, color.b)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


# ---------------------------------------------------------------------------
# Thin 'graphics' namespace object  (mirrors  from rgbmatrix import graphics)
# ---------------------------------------------------------------------------

class _Graphics:
    Color = Color
    Font = Font
    DrawText = staticmethod(DrawText)
    DrawLine = staticmethod(DrawLine)


graphics = _Graphics()


# ---------------------------------------------------------------------------
# Offscreen canvas
# ---------------------------------------------------------------------------

class SimCanvas:
    """Offscreen pixel buffer — drop-in for the opaque rgbmatrix canvas type.

    Stores only lit pixels (sparse dict) so memory use scales with content
    rather than total panel size.
    """

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._pixels: Dict[Tuple[int, int], Tuple[int, int, int]] = {}

    # -- rgbmatrix canvas interface ------------------------------------------

    def Clear(self) -> None:
        self._pixels.clear()

    def SetPixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            key = (x, y)
            if r == 0 and g == 0 and b == 0:
                self._pixels.pop(key, None)
            else:
                self._pixels[key] = (r, g, b)


# ---------------------------------------------------------------------------
# RGBMatrixOptions
# ---------------------------------------------------------------------------

class RGBMatrixOptions:
    """Drop-in replacement for ``rgbmatrix.RGBMatrixOptions``."""

    def __init__(self) -> None:
        self.rows: int = 16
        self.cols: int = 32
        self.chain_length: int = 1
        self.parallel: int = 1
        self.brightness: int = 100
        self.multiplexing: int = 0
        self.gpio_slowdown: int = 1
        self.row_address_type: int = 0
        self.pwm_lsb_nanoseconds: int = 130
        self.pwm_bits: int = 11
        self.hardware_mapping: str = "regular"


# ---------------------------------------------------------------------------
# RGBMatrix — pygame-backed main class
# ---------------------------------------------------------------------------

class RGBMatrix:
    """Drop-in replacement for ``rgbmatrix.RGBMatrix``.

    Opens a pygame window sized to contain one circle per LED, separated by
    small gaps.  ``SwapOnVSync`` renders the offscreen canvas and returns a
    fresh one for the next frame (double-buffer pattern).
    """

    def __init__(self, options: RGBMatrixOptions) -> None:
        self._cols = options.cols * options.chain_length
        self._rows = options.rows * options.parallel
        self._alive = True

        win_w = self._cols * _LED_STEP + _LED_GAP
        win_h = self._rows * _LED_STEP + _LED_GAP

        pygame.init()
        self._screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption(
            f"F3K Matrix Simulator  ({self._cols}×{self._rows} LEDs)"
        )
        self._screen.fill(_BG_COLOR)
        pygame.display.flip()

        logger.info(
            "SimMatrix: %d×%d LED matrix → %d×%d px pygame window",
            self._cols, self._rows, win_w, win_h,
        )

    # -- rgbmatrix API -------------------------------------------------------

    def CreateFrameCanvas(self) -> SimCanvas:
        """Return a blank offscreen canvas sized to the full panel."""
        return SimCanvas(self._cols, self._rows)

    def SwapOnVSync(self, canvas: SimCanvas) -> SimCanvas:
        """Render *canvas* to the window and return a new blank canvas.

        Also pumps pygame events so the window stays responsive.
        """
        if not self._alive:
            return SimCanvas(self._cols, self._rows)
        self._pump_events()
        self._draw(canvas)
        return SimCanvas(self._cols, self._rows)

    def Clear(self) -> None:
        """Blank the display."""
        if not self._alive:
            return
        self._screen.fill(_BG_COLOR)
        pygame.display.flip()

    # -- internal ------------------------------------------------------------

    def _pump_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._alive = False
                pygame.quit()
                sys.exit(0)

    def _draw(self, canvas: SimCanvas) -> None:
        """Render all LEDs: lit pixels use their colour; unlit use _OFF_COLOR."""
        self._screen.fill(_BG_COLOR)
        pixels = canvas._pixels
        draw_circle = pygame.draw.circle
        screen = self._screen

        for row in range(self._rows):
            cy = _LED_GAP + row * _LED_STEP + _LED_RADIUS
            for col in range(self._cols):
                cx = _LED_GAP + col * _LED_STEP + _LED_RADIUS
                color = pixels.get((col, row), _OFF_COLOR)
                draw_circle(screen, color, (cx, cy), _LED_RADIUS)

        pygame.display.flip()
