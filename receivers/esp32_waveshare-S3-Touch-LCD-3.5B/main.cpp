/**
 * ESP32-S3-Touch-LCD-3.5B — F3K Timer Stopwatch
 *
 * Portrait orientation (320 × 480, rotation = 0).
 *
 * Receives F3K event state over ESP-NOW (channel 4) and displays context
 * alongside a local stopwatch controlled via the onboard BOOT button and
 * the PWR button (via AXP2101 PMU):
 *
 *   BOOT button  GPIO 0    →  short press:  Start / Stop stopwatch
 *                          →  hold 1.5 s:   toggle selected time invalid / valid
 *   PWR  button  AXP2101   →  short press:  scroll saved-times list
 *                          →  long press:   clear all saved times
 *   Touch (AXS15231B)      →  tap list row: select that entry directly
 *                          →  long press list row (0.8 s): toggle invalid / valid
 *                          →  tap [CLR] in list header: clear all saved times
 *
 * Display layout (portrait 320 × 480):
 *
 *   ┌─────────────────────────────────┐  y = 0
 *   │ 3.8V  R1 GA                     │  battery voltage + round / group  (size 3)
 *   │ WORK                     02:30  │  section abbrev + evt time        (size 3)
 *   │ Task F - Distance...            │  task name (scrolling marquee)    (size 3)
 *   │                                 │
 *   │           00:00.0               │  stopwatch  GREEN=running         (size 5)
 *   │                                 │               CYAN=stopped
 *   ├─────────────────────────────────┤  divider  y = 268
 *   │ # Time (0)          [CLR]       │  list header + clear button       (size 3)
 *   │ 1   00:45.2                     │  saved flight times               (size 3)
 *   │ 2   01:23.7                     │  (tap=select, long-press=toggle)  × 6 rows
 *   └─────────────────────────────────┘  y = 480
 *
 * Stopwatch behaviour:
 *   BOOT short press              →  starts from 00:00.0 (GREEN)
 *   BOOT short press (running)    →  stops, saves time to list, resets to 00:00.0 (CYAN)
 *   BOOT hold 1.5 s               →  toggle selected entry invalid / valid
 *   PWR short press (AXP2101)     →  scroll saved-times list (wraps)
 *   PWR long press  (AXP2101)     →  clear all saved times
 *   Touch tap on list row         →  select that row directly (bypasses scroll)
 *   Touch long press on list row  →  toggle that row invalid / valid
 *   Touch tap on [CLR] button     →  clear all saved times
 *
 * Dependencies (Library Manager / PlatformIO):
 *   - GFX_Library_for_Arduino     (moononournation)  >= 1.5.5
 *   - TCA9554                     (offline install from Waveshare example package)
 *   - esp_lcd_touch_axs15231b     (offline install from Waveshare example package)
 *   - XPowersLib                  (lewisxhe/XPowersLib)  >= 0.2.9
 *   - ArduinoJson                 (bblanchon/ArduinoJson) >= 6.x
 *   - esp_now, esp_wifi           (bundled with ESP32 Arduino core)
 *
 * Audio: The ES8311 audio codec requires full I2S setup not yet implemented.
 *        Beep functions are Serial-only stubs.
 * TODO:  Implement beep feedback via ES8311 I2S (see 04_es8311_example).
 *
 * Note: onDataRecv uses ESP32 Arduino core 3.x (esp-idf 5.x) signature.
 * For core 2.x replace:  const esp_now_recv_info_t *recv_info
 *               with:    const uint8_t *mac
 *
 * Device reference:  https://docs.waveshare.com/ESP32-S3-Touch-LCD-3.5B
 */

// ── Target AXP2101 chip variant before including XPowersLib ──────────────────
#define XPOWERS_CHIP_AXP2101

#include <Wire.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <ArduinoJson.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <Arduino_GFX_Library.h>
#include "TCA9554.h"
#include <XPowersLib.h>
#include "esp_lcd_touch_axs15231b.h"

// ── 16-bit RGB565 colour constants (guarded in case the GFX library provides them) ──
#ifndef BLACK
#define BLACK 0x0000
#endif
#ifndef WHITE
#define WHITE 0xFFFF
#endif
#ifndef RED
#define RED 0xF800
#endif
#ifndef GREEN
#define GREEN 0x07E0
#endif
#ifndef CYAN
#define CYAN 0x07FF
#endif
#ifndef YELLOW
#define YELLOW 0xFFE0
#endif
#ifndef DARKGREY
#define DARKGREY 0x7BEF
#endif

// ── LCD hardware pins ─────────────────────────────────────────────────────────
// QSPI display interface (AXS15231B driver).
// Verified from Waveshare 08_gfx_helloworld example.
#define LCD_QSPI_CS 12
#define LCD_QSPI_CLK 5
#define LCD_QSPI_D0 1
#define LCD_QSPI_D1 2
#define LCD_QSPI_D2 3
#define LCD_QSPI_D3 4
#define GFX_BL 6 // backlight GPIO (active HIGH)

// ── I2C bus ───────────────────────────────────────────────────────────────────
// All three I2C devices share a single Wire bus (SDA=8, SCL=7), confirmed by
// the LVGL example (09_lvgl_arduino_v8) which inits Wire(8,7) then calls
// TCA.begin() and bsp_touch_init(&Wire, ...) on the same instance.
// NOTE: The GFX helloworld example (08) used Wire(21,22) — this appears to be
// for a different board variant.  If TCA init fails, try swapping to 21/22.
#define I2C_SDA 8
#define I2C_SCL 7
#define TCA_I2C_SDA I2C_SDA
#define TCA_I2C_SCL I2C_SCL
#define PMU_I2C_SDA I2C_SDA
#define PMU_I2C_SCL I2C_SCL

// ── Button GPIOs ──────────────────────────────────────────────────────────────
// BOOT button: onboard, active-LOW, INPUT_PULLUP.
#define BTN_BOOT_PIN 0 // GPIO 0 — confirmed from 03_button_example

// PWR button is managed by the AXP2101 PMU chip via I2C (no direct GPIO pin).
// It is accessed by polling power.getIrqStatus() in loop().

// TODO: If you wire external buttons to the 2.54 mm GPIO header, define their
//       pin numbers here and add the corresponding polling logic in loop().
//       Suggested assignments (fill in actual GPIOs once wired):
// #define BTN_EXT_A_PIN  ??   // TODO: fill in GPIO for external start/stop button
// #define BTN_EXT_B_PIN  ??   // TODO: fill in GPIO for external scroll button

static constexpr unsigned long DEBOUNCE_MS = 50;

// ── GFX display objects ───────────────────────────────────────────────────────
// TCA9554 at I2C address 0x20 drives the LCD hardware-reset line via Wire.
// RST is passed as -1 to Arduino_AXS15231B; the TCA handles it in setup().
TCA9554 TCA(0x20);

Arduino_DataBus *bus = new Arduino_ESP32QSPI(
    LCD_QSPI_CS, LCD_QSPI_CLK,
    LCD_QSPI_D0, LCD_QSPI_D1, LCD_QSPI_D2, LCD_QSPI_D3);

// Direct-write (no canvas): each draw call updates the display immediately,
// avoiding the full-screen flush overhead of Arduino_Canvas.  Suitable for
// the text-heavy, partial-update style of this application.
Arduino_GFX *gfx = new Arduino_AXS15231B(
    bus, -1 /* RST via TCA */, 0 /* rotation: portrait */, false, 320, 480);

// ── AXP2101 power management ──────────────────────────────────────────────────
XPowersPMU power;
static bool s_pmuAvailable = false;

// ── Screen dimensions ─────────────────────────────────────────────────────────
static constexpr int SCR_W = 320;
static constexpr int SCR_H = 480;

// ── Layout Y-coordinates (portrait 320 × 480) ────────────────────────────────
//
// Text sizes used:
//   size 3  →  character cell 18 × 24 px  (header / section / task / list rows)
//   size 5  →  character cell 30 × 40 px  (stopwatch)
//
//   Y_STATUS  =   4   "3.8V R1 GA"         size 3, 24 px tall
//   Y_SECTION =  32   "WORK      02:30"     size 3, 24 px tall
//   Y_TASK    =  60   task name marquee     size 3, 24 px tall
//
//   Stopwatch region: Y_SW_TOP(90) .. Y_DIVIDER(268) = 178 px
//     "MM:SS.t" = 7 chars × 30 px = 210 px wide; x = (320-210)/2 = 55
//     Text centred vertically: Y_SW_TEXT = 90 + (178-40)/2 = 159
//
//   Y_DIVIDER = 268  horizontal rule
//   Y_HDR     = 274  "# Time (N)"           size 3, 24 px tall
//   Y_LIST    = 302  first flight row, pitch 28 px
//                    rows visible = (480 - 302) / 28 = 6

static constexpr int Y_STATUS = 4;
static constexpr int Y_SECTION = 32;
static constexpr int Y_TASK = 60;
static constexpr int Y_SW_TOP = 90;
static constexpr int Y_SW_TEXT = 159;
static constexpr int Y_DIVIDER = 268;
static constexpr int Y_HDR = 274;
static constexpr int Y_LIST = 302;
static constexpr int LIST_PITCH = 28;
static constexpr int LIST_ROWS = (SCR_H - Y_LIST) / LIST_PITCH; // 6

// ── Touch thresholds and zones ────────────────────────────────────────────────
static constexpr unsigned long TOUCH_LONG_PRESS_MS = 800; // ms to trigger long-press
// [CLR] button: 3-char label at size 3 = 54 px; box starts at BTN_CLR_X - 4.
// Touch target: x >= BTN_CLR_X - 4  AND  y in [Y_HDR, Y_LIST).
static constexpr int BTN_CLR_X = 252;

// ── Confirm-clear dialog geometry ─────────────────────────────────────────────
// Dialog: centred on x-axis (40…280), sits in the list area (182…312).
static constexpr int DLG_X = 40;             // left edge
static constexpr int DLG_Y = 182;            // top edge
static constexpr int DLG_W = 240;            // width
static constexpr int DLG_H = 130;            // height → bottom = 312
static constexpr int DLG_BTN_Y = DLG_Y + 78; // 260 — top of YES/NO buttons
static constexpr int DLG_BTN_H = 34;         // button height
static constexpr int DLG_BTN_W = 88;         // button width (both)
static constexpr int DLG_YES_X = DLG_X + 16; // 56  — left edge of YES
static constexpr int DLG_NO_X = DLG_X + 136; // 176 — left edge of NO

// ── Task-name marquee (size-3: 18 px per character) ──────────────────────────
static constexpr int TASK_VIS_CHARS = 17;           // (320-4)/18 = 17 chars visible
static constexpr int TASK_CHAR_W = 18;              // px per char at size 3
static constexpr int TASK_SCROLL_PX = 4;            // px per tick
static constexpr unsigned long TASK_SCROLL_MS = 40; // ms between ticks (~100 px/s)

// ── ESP-NOW receive queue ─────────────────────────────────────────────────────
static constexpr int RECV_QUEUE_LEN = 8;
static constexpr int MAX_PACKET_LEN = 251; // ESP-NOW max payload is 250 bytes

struct RecvPacket
{
  uint8_t data[MAX_PACKET_LEN];
  int len;
};

static QueueHandle_t s_recvQueue = nullptr;

// ── Remote event state (populated from ESP-NOW "time" messages) ───────────────
static char s_evtTime[8] = "--:--"; // event countdown "MM:SS"
static char s_sect[32] = "";        // section description
static int s_round = 0;
static char s_group[4] = "-";
static char s_taskName[32] = "";

// ── Task-name marquee state ───────────────────────────────────────────────────
static int s_taskPixelOff = 0;
static unsigned long s_lastTaskScrollMs = 0;

// ── Stopwatch state ───────────────────────────────────────────────────────────
static bool sw_running = false;
static uint32_t sw_start_ms = 0; // millis() at last Start press
static uint32_t sw_base_ms = 0;  // accumulated ms before current Start

static uint32_t swElapsed()
{
  return sw_running ? sw_base_ms + (millis() - sw_start_ms) : sw_base_ms;
}

// Tracks which 100 ms bucket was last drawn; avoids redundant LCD writes.
static uint32_t s_lastDisplayTenth = 0xFFFFFFFFUL;

// ── Saved flight times ────────────────────────────────────────────────────────
static constexpr int MAX_SAVED = 20;
static uint32_t s_saved[MAX_SAVED];
static bool s_invalid[MAX_SAVED]; // true = time marked invalid by user
static int s_savedCount = 0;
static int s_listOff = 0;             // scroll offset into saved list
static int s_selectedIdx = -1;        // list cursor; -1 = nothing saved yet
static bool s_confirmPending = false; // true while "Clear all?" dialog is showing

// ── Time formatter: "MM:SS.t" ─────────────────────────────────────────────────
static void fmtTime(char *buf, size_t len, uint32_t ms)
{
  unsigned t = (unsigned)(ms / 100); // total tenths
  unsigned s = t / 10;               // total seconds
  unsigned m = s / 60;               // minutes
  snprintf(buf, len, "%02u:%02u.%u", m, s % 60, t % 10);
}

// ── Section abbreviation ──────────────────────────────────────────────────────
static const char *abbrevSection(const char *sect)
{
  if (strstr(sect, "Working"))
    return "WORK";
  if (strstr(sect, "Landing"))
    return "LAND";
  if (strstr(sect, "Preparation"))
    return "PREP";
  if (strstr(sect, "Test Flying"))
    return "TEST";
  if (strstr(sect, "No Fly"))
    return "NOFLY";
  if (strstr(sect, "Announcement"))
    return "----";
  if (strstr(sect, "Waiting"))
    return "WAIT";
  return sect[0] ? sect : "----";
}

// ── Display helpers ───────────────────────────────────────────────────────────

static void drawTaskNameLine()
{
  int taskLen = (int)strlen(s_taskName);
  gfx->setTextSize(3);
  gfx->setTextColor(CYAN, BLACK);

  if (taskLen <= TASK_VIS_CHARS)
  {
    // Clear the full row before drawing a short/static name.
    gfx->fillRect(0, Y_TASK, SCR_W, 25, BLACK);
    gfx->setCursor(2, Y_TASK);
    gfx->print(taskLen ? s_taskName : "---");
    return;
  }

  // Pixel-smooth marquee.
  // Each character cell redraws its own background (CYAN on BLACK), so no
  // fillRect is needed — skipping it eliminates the per-tick black flash.
  // Text wrap must be off (set in setup()).
  int period_px = (taskLen + 3) * TASK_CHAR_W; // full-cycle width in pixels
  int pix_off = s_taskPixelOff % period_px;
  int char_start = pix_off / TASK_CHAR_W; // first (partially visible) char
  int sub_px = pix_off % TASK_CHAR_W;     // pixels of that char scrolled off

  // Enough chars to fill the visible area from the offset start position.
  int chars_needed = (SCR_W - 2 + sub_px) / TASK_CHAR_W + 2;
  if (chars_needed > 20)
    chars_needed = 20;
  int period_ch = taskLen + 3;
  char buf[22];
  for (int i = 0; i < chars_needed; i++)
  {
    int idx = (char_start + i) % period_ch;
    buf[i] = (idx < taskLen) ? s_taskName[idx] : ' ';
  }
  buf[chars_needed] = '\0';

  gfx->setCursor(2 - sub_px, Y_TASK); // start slightly left so sub_px pixels clip
  gfx->print(buf);
}

static void drawStatusLine()
{
  // Battery voltage from AXP2101 (returns mV as uint16_t).
  // Shows "--.-V" when PMU is not available.
  char buf[28];
  if (s_pmuAvailable)
  {
    uint16_t vbat_mv = power.getBattVoltage();
    snprintf(buf, sizeof(buf), "%.1fV R%d G%s",
             vbat_mv / 1000.0f, s_round, s_group);
  }
  else
  {
    snprintf(buf, sizeof(buf), "--.-V R%d G%s", s_round, s_group);
  }

  gfx->fillRect(0, Y_STATUS - 1, SCR_W, 28, BLACK);
  gfx->setTextSize(3);
  gfx->setTextColor(WHITE, BLACK);
  gfx->setCursor(2, Y_STATUS);
  gfx->print(buf);
}

static void drawSectionLine()
{
  gfx->fillRect(0, Y_SECTION, SCR_W, 25, BLACK);

  gfx->setTextSize(3);
  gfx->setTextColor(YELLOW, BLACK);
  gfx->setCursor(2, Y_SECTION);
  gfx->print(abbrevSection(s_sect));

  // Event time right-aligned: 5 chars × 18 px = 90 px  →  x = 320 - 90 - 4 = 226
  gfx->setTextColor(WHITE, BLACK);
  gfx->setCursor(SCR_W - 5 * 18 - 4, Y_SECTION);
  gfx->print(s_evtTime);
}

static void redrawStopwatch()
{
  // "MM:SS.t" = 7 chars × 30 px = 210 px wide; centred on 320 px  →  x = 55
  char buf[10];
  fmtTime(buf, sizeof(buf), swElapsed());

  gfx->fillRect(0, Y_SW_TOP, SCR_W, Y_DIVIDER - Y_SW_TOP, BLACK);
  gfx->setTextSize(5);
  gfx->setTextColor(sw_running ? GREEN : CYAN, BLACK);
  gfx->setCursor(55, Y_SW_TEXT);
  gfx->print(buf);
}

static void updateStopwatchDigits()
{
  // Partial update: redraw only the digits to avoid filling the SW region.
  // setTextColor(fg, bg) fills each character cell background; no fillRect needed.
  char buf[10];
  fmtTime(buf, sizeof(buf), swElapsed());

  gfx->setTextSize(5);
  gfx->setTextColor(sw_running ? GREEN : CYAN, BLACK);
  gfx->setCursor(55, Y_SW_TEXT);
  gfx->print(buf);
}

static void redrawListArea()
{
  gfx->fillRect(0, Y_DIVIDER, SCR_W, SCR_H - Y_DIVIDER, BLACK);
  gfx->drawFastHLine(0, Y_DIVIDER, SCR_W, DARKGREY);

  char hbuf[24];
  snprintf(hbuf, sizeof(hbuf), "# Time (%d)", s_savedCount);
  gfx->setTextSize(3);
  gfx->setTextColor(DARKGREY, BLACK);
  gfx->setCursor(2, Y_HDR);
  gfx->print(hbuf);

  // [CLR] button — touch target on right side of header row.
  // Box outline in dark grey; label in red to signal destructive action.
  gfx->drawRect(BTN_CLR_X - 4, Y_HDR - 1, 62, 26, DARKGREY);
  gfx->setTextColor(RED, BLACK);
  gfx->setCursor(BTN_CLR_X, Y_HDR);
  gfx->print("CLR");

  for (int i = 0; i < LIST_ROWS; i++)
  {
    int idx = s_listOff + i;
    if (idx >= s_savedCount)
      break;

    bool sel = (idx == s_selectedIdx);
    bool inv = s_invalid[idx];

    char tbuf[10];
    fmtTime(tbuf, sizeof(tbuf), s_saved[idx]);

    // Row number + selection marker (always white on black)
    char rbuf[5];
    snprintf(rbuf, sizeof(rbuf), "%-2d%c", idx + 1, sel ? '>' : ' ');
    gfx->setTextColor(WHITE, BLACK);
    gfx->setCursor(2, Y_LIST + i * LIST_PITCH);
    gfx->print(rbuf);

    // Time: colour reflects selected and / or invalid state
    uint16_t fg = WHITE, bg = BLACK;
    if (sel && inv)
    {
      fg = BLACK;
      bg = RED;
    } // selected invalid
    else if (inv)
    {
      fg = RED;
      bg = BLACK;
    } // invalid
    else if (sel)
    {
      fg = BLACK;
      bg = WHITE;
    } // selected valid
    gfx->setTextColor(fg, bg);
    gfx->print(tbuf);
  }
}

static void drawConfirmDialog()
{
  // Black fill behind dialog (within list area)
  gfx->fillRect(0, Y_DIVIDER + 1, SCR_W, SCR_H - Y_DIVIDER - 1, BLACK);

  // Dialog box border
  gfx->fillRect(DLG_X, DLG_Y, DLG_W, DLG_H, BLACK);
  gfx->drawRect(DLG_X, DLG_Y, DLG_W, DLG_H, WHITE);

  // Prompt text — "Clear all?" (10 chars × 18 px = 180 px; centred in DLG_W)
  gfx->setTextSize(3);
  gfx->setTextColor(WHITE, BLACK);
  gfx->setCursor(DLG_X + (DLG_W - 10 * 18) / 2, DLG_Y + 12);
  gfx->print("Clear all?");

  // [YES] button — red fill, white text ("YES" = 54 px, centred in DLG_BTN_W)
  gfx->fillRect(DLG_YES_X, DLG_BTN_Y, DLG_BTN_W, DLG_BTN_H, RED);
  gfx->setTextColor(WHITE, RED);
  gfx->setCursor(DLG_YES_X + (DLG_BTN_W - 3 * 18) / 2, DLG_BTN_Y + 5);
  gfx->print("YES");

  // [NO] button — dark grey fill, white text ("NO" = 36 px, centred in DLG_BTN_W)
  gfx->fillRect(DLG_NO_X, DLG_BTN_Y, DLG_BTN_W, DLG_BTN_H, DARKGREY);
  gfx->setTextColor(WHITE, DARKGREY);
  gfx->setCursor(DLG_NO_X + (DLG_BTN_W - 2 * 18) / 2, DLG_BTN_Y + 5);
  gfx->print("NO");
}

static void drawFullScreen()
{
  gfx->fillScreen(BLACK);
  drawStatusLine();
  drawSectionLine();
  drawTaskNameLine();
  redrawStopwatch();
  redrawListArea();
}

// ── Start / Stop ──────────────────────────────────────────────────────────────

static void beepStart();
static void beepStop();

static void doStartStop()
{
  if (!sw_running)
  {
    // ── Start ────────────────────────────────────────────────────────────────
    sw_start_ms = millis();
    sw_running = true;
    s_lastDisplayTenth = 0xFFFFFFFFUL; // force immediate digit refresh
  }
  else
  {
    // ── Stop: accumulate elapsed, save to list, reset for next flight ─────────
    sw_base_ms += millis() - sw_start_ms;
    sw_running = false;

    if (s_savedCount < MAX_SAVED)
    {
      s_invalid[s_savedCount] = false;
      s_saved[s_savedCount++] = sw_base_ms;
    }
    else
    {
      // Ring-buffer: drop oldest entry, append newest.
      memmove(s_saved, s_saved + 1, (MAX_SAVED - 1) * sizeof(uint32_t));
      memmove(s_invalid, s_invalid + 1, (MAX_SAVED - 1) * sizeof(bool));
      s_saved[MAX_SAVED - 1] = sw_base_ms;
      s_invalid[MAX_SAVED - 1] = false;
      if (s_selectedIdx > 0)
        s_selectedIdx--; // compensate for shift
    }

    s_selectedIdx = s_savedCount - 1; // always select the newly saved entry

    // Auto-scroll list to show the latest saved entry.
    if (s_savedCount > LIST_ROWS)
      s_listOff = s_savedCount - LIST_ROWS;

    // Reset stopwatch to zero, ready for the next flight.
    sw_base_ms = 0;

    redrawListArea();
  }

  sw_running ? beepStart() : beepStop();
  redrawStopwatch(); // colour: CYAN (stopped) ↔ GREEN (running)
}

// ── Move selection cursor through saved list ──────────────────────────────────

static void doSelectMove()
{
  if (s_savedCount == 0)
    return;

  if (--s_selectedIdx < 0)
    s_selectedIdx = s_savedCount - 1; // wrap from oldest back to newest

  // Keep selected entry within the visible window.
  if (s_selectedIdx < s_listOff)
    s_listOff = s_selectedIdx;
  else if (s_selectedIdx >= s_listOff + LIST_ROWS)
    s_listOff = s_selectedIdx - LIST_ROWS + 1;

  redrawListArea();
}

// ── Toggle selected entry valid / invalid ─────────────────────────────────────

static void beepInvalid();

static void doToggleInvalid()
{
  if (s_selectedIdx < 0 || s_selectedIdx >= s_savedCount)
    return;
  s_invalid[s_selectedIdx] = !s_invalid[s_selectedIdx];
  beepInvalid();
  redrawListArea();
}

// ── Clear all saved times ─────────────────────────────────────────────────────

static void beepClear();

static void doClearSaved()
{
  s_savedCount = 0;
  s_listOff = 0;
  s_selectedIdx = -1;
  memset(s_invalid, 0, sizeof(s_invalid));
  beepClear();
  redrawListArea();
}

// ── Touch gesture handlers ───────────────────────────────────────────────────

/**
 * Tap: select a list row directly, or trigger the [CLR] button.
 * Called on finger-up when held < TOUCH_LONG_PRESS_MS.
 */
static void handleTap(int16_t x, int16_t y)
{
  // While confirm dialog is showing, only its YES/NO buttons respond.
  if (s_confirmPending)
  {
    if (y >= DLG_BTN_Y && y < DLG_BTN_Y + DLG_BTN_H)
    {
      if (x >= DLG_YES_X && x < DLG_YES_X + DLG_BTN_W)
      {
        s_confirmPending = false;
        doClearSaved();
      }
      else if (x >= DLG_NO_X && x < DLG_NO_X + DLG_BTN_W)
      {
        s_confirmPending = false;
        redrawListArea();
      }
      // else: tap between buttons — keep dialog open
    }
    else
    {
      // Tap outside button row → dismiss (treat as NO)
      s_confirmPending = false;
      redrawListArea();
    }
    return;
  }

  // [CLR] button in list header row → show confirm dialog
  if (y >= Y_HDR && y < Y_LIST && x >= (BTN_CLR_X - 4))
  {
    s_confirmPending = true;
    drawConfirmDialog();
    return;
  }

  // List row: tap = select that entry directly
  if (y >= Y_LIST && y < SCR_H)
  {
    int row = (y - Y_LIST) / LIST_PITCH;
    if (row >= 0 && row < LIST_ROWS)
    {
      int idx = s_listOff + row;
      if (idx >= 0 && idx < s_savedCount)
      {
        s_selectedIdx = idx;
        redrawListArea();
      }
    }
  }
}

/**
 * Long press: select a list row and toggle its invalid flag.
 * Called after TOUCH_LONG_PRESS_MS ms of continuous contact.
 */
static void handleLongPress(int16_t x, int16_t y)
{
  if (s_confirmPending)
    return; // physical input suppressed while confirm dialog is showing

  if (y >= Y_LIST && y < SCR_H)
  {
    int row = (y - Y_LIST) / LIST_PITCH;
    if (row >= 0 && row < LIST_ROWS)
    {
      int idx = s_listOff + row;
      if (idx >= 0 && idx < s_savedCount)
      {
        s_selectedIdx = idx;
        doToggleInvalid(); // beep + redrawListArea()
      }
    }
  }
}

// ── Audio feedback ────────────────────────────────────────────────────────────
// TODO: Implement audio via the onboard ES8311 I2S codec.
//       See Waveshare example 04_es8311_example for setup.
//       For now the functions log to Serial only.

static void beepStart() { Serial.println(F("[beep] start")); }
static void beepStop() { Serial.println(F("[beep] stop")); }
static void beepInvalid() { Serial.println(F("[beep] invalid")); }
static void beepClear() { Serial.println(F("[beep] clear")); }

// ── ESP-NOW receive callback (ESP32 Arduino core 3.x / esp-idf 5.x) ──────────

void onDataRecv(const esp_now_recv_info_t *recv_info,
                const uint8_t *incomingData, int len)
{
  // Discard exact duplicates before they reach the queue.
  static uint8_t lastData[MAX_PACKET_LEN];
  static int lastLen = 0;
  int copyLen = min(len, MAX_PACKET_LEN - 1);
  if (copyLen == lastLen && memcmp(incomingData, lastData, copyLen) == 0)
    return;
  lastLen = copyLen;
  memcpy(lastData, incomingData, copyLen);

  if (!s_recvQueue)
    return;

  RecvPacket pkt;
  pkt.len = copyLen;
  memcpy(pkt.data, incomingData, pkt.len);
  pkt.data[pkt.len] = '\0';
  xQueueSend(s_recvQueue, &pkt, 0); // non-blocking; drop if queue is full
}

// ── ESP-NOW message handler ───────────────────────────────────────────────────

static void handleTime(JsonObjectConst data)
{
  const char *timeStr = data["time_s"] | "--:--";
  int roundNum = data["r_num"] | 0;
  const char *groupLet = data["g_let"] | "-";
  const char *sect = data["sect"] | "";
  const char *taskName = data["task_name"] | "";

  bool statusChanged = (strcmp(groupLet, s_group) != 0) || (roundNum != s_round);
  bool taskChanged = (strcmp(taskName, s_taskName) != 0);

  strncpy(s_evtTime, timeStr, sizeof(s_evtTime) - 1);
  strncpy(s_sect, sect, sizeof(s_sect) - 1);
  strncpy(s_group, groupLet, sizeof(s_group) - 1);
  strncpy(s_taskName, taskName, sizeof(s_taskName) - 1);
  s_round = roundNum;

  if (statusChanged)
    drawStatusLine();

  if (taskChanged)
  {
    s_taskPixelOff = 0;
    s_lastTaskScrollMs = 0;
    drawTaskNameLine();
  }

  drawSectionLine(); // event time changes every second
}

// ── Arduino lifecycle ─────────────────────────────────────────────────────────

void setup()
{
  Serial.begin(115200);
  Serial.println(F("\n[F3K] ESP32-S3-Touch-LCD-3.5B stopwatch starting"));

  // ── TCA9554 + LCD hardware reset ──────────────────────────────────────────
  Wire.begin(TCA_I2C_SDA, TCA_I2C_SCL);
  TCA.begin();
  TCA.pinMode1(1, OUTPUT);
  TCA.write1(1, 1); // reset HIGH
  delay(10);
  TCA.write1(1, 0); // reset LOW
  delay(10);
  TCA.write1(1, 1); // reset HIGH — hold ≥ 120 ms before init
  delay(200);

  // ── Display init ──────────────────────────────────────────────────────────
  gfx->setTextWrap(false); // prevent marquee overflow wrapping onto next line
  if (!gfx->begin())
    Serial.println(F("[GFX] begin() failed!"));

  pinMode(GFX_BL, OUTPUT);
  digitalWrite(GFX_BL, HIGH); // backlight on

  gfx->fillScreen(BLACK);

  // ── Touch init ────────────────────────────────────────────────────────────
  // AXS15231B touch shares Wire(8, 7) with TCA9554 and AXP2101.
  // irq = -1: no interrupt pin; polling used instead.
  // rst = 0:  hardware reset was already performed by TCA above.
  bsp_touch_init(&Wire, -1 /* no IRQ pin */, 0 /* rst via TCA */, SCR_W, SCR_H);

  // ── AXP2101 power management init ─────────────────────────────────────────
  // Uses the shared Wire bus (SDA=8, SCL=7) — same instance as TCA and touch.
  s_pmuAvailable = power.begin(Wire, AXP2101_SLAVE_ADDRESS,
                               PMU_I2C_SDA, PMU_I2C_SCL);
  if (s_pmuAvailable)
  {
    power.enableBattDetection();
    power.enableBattVoltageMeasure();
    power.disableTSPinMeasure(); // no battery-temperature sensor on this board

    // Arm PKEY interrupt detection (polled in loop; no IRQ pin needed).
    power.disableIRQ(XPOWERS_AXP2101_ALL_IRQ);
    power.clearIrqStatus();
    power.enableIRQ(XPOWERS_AXP2101_PKEY_SHORT_IRQ |
                    XPOWERS_AXP2101_PKEY_LONG_IRQ);
  }
  else
  {
    Serial.println(F("[AXP] PMU not found — battery voltage and PWR button unavailable"));
  }

  // ── BOOT button ───────────────────────────────────────────────────────────
  pinMode(BTN_BOOT_PIN, INPUT_PULLUP);

  // ── ESP-NOW ───────────────────────────────────────────────────────────────
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  // Channel must match the f3k-timer sender (broadcasts on channel 4).
  esp_wifi_set_channel(4, WIFI_SECOND_CHAN_NONE);

  s_recvQueue = xQueueCreate(RECV_QUEUE_LEN, sizeof(RecvPacket));

  if (esp_now_init() != ESP_OK)
  {
    Serial.println(F("[ESPNow] Initialisation failed"));
    // "ESP-NOW INIT FAIL" centred on screen
    gfx->setTextSize(3);
    gfx->setTextColor(RED, BLACK);
    gfx->setCursor(97, 210); // "ESP-NOW" = 7 × 18 = 126 px  →  x = (320-126)/2
    gfx->print("ESP-NOW");
    gfx->setCursor(79, 244); // "INIT FAIL" = 9 × 18 = 162 px  →  x = (320-162)/2
    gfx->print("INIT FAIL");
    return;
  }

  esp_now_register_recv_cb(onDataRecv);

  Serial.print(F("[ESPNow] Receiver ready. MAC: "));
  Serial.println(WiFi.macAddress());

  // ── Splash screen ─────────────────────────────────────────────────────────
  gfx->setTextSize(5);
  gfx->setTextColor(CYAN, BLACK);
  gfx->setCursor(115, 190); // "F3K" = 3 × 30 = 90 px  →  x = (320-90)/2 = 115
  gfx->print("F3K");
  gfx->setTextSize(3);
  gfx->setTextColor(DARKGREY, BLACK);
  gfx->setCursor(79, 240); // "Stopwatch" = 9 × 18 = 162 px  →  x = (320-162)/2 = 79
  gfx->print("Stopwatch");
  delay(800);

  drawFullScreen();
}

void loop()
{
  unsigned long now = millis();

  // ── BOOT button (GPIO 0): short press = start/stop; hold 1.5 s = toggle invalid ──
  {
    static bool lastState = HIGH;
    static unsigned long edgeMs = 0;
    static bool longFired = false;

    bool cur = (bool)digitalRead(BTN_BOOT_PIN);

    if (cur != lastState && (now - edgeMs) > DEBOUNCE_MS)
    {
      edgeMs = now;
      lastState = cur;
      if (cur == LOW)
      {
        longFired = false; // arm for new press
      }
      else
      {
        if (!longFired) // rising edge before long-press threshold
          if (!s_confirmPending)
            doStartStop();
      }
    }
    // Long-press threshold: 1.5 s
    if (lastState == LOW && !longFired && (now - edgeMs) >= 1500UL)
    {
      longFired = true;
      if (!s_confirmPending)
        doToggleInvalid();
    }
  }

  // ── PWR button via AXP2101: short press = scroll list; long press = clear all ──
  if (s_pmuAvailable)
  {
    static unsigned long lastAxpPoll = 0;
    if (now - lastAxpPoll >= 50) // poll at 20 Hz — fast enough for button response
    {
      lastAxpPoll = now;
      uint32_t status = power.getIrqStatus();
      if (status)
      {
        if (power.isPekeyShortPressIrq() && !s_confirmPending)
          doSelectMove();
        if (power.isPekeyLongPressIrq() && !s_confirmPending)
        {
          s_confirmPending = true;
          drawConfirmDialog();
        }
        power.clearIrqStatus();
      }
    }
  }

  // ── Touch input (50 Hz poll) ────────────────────────────────────────────────
  {
    static bool touchDown = false;
    static int16_t touchX = 0;
    static int16_t touchY = 0;
    static unsigned long touchDownMs = 0;
    static bool longFired = false;
    static unsigned long lastTouchMs = 0;

    if (now - lastTouchMs >= 20)
    {
      lastTouchMs = now;
      bsp_touch_read();
      touch_data_t td;
      bool pressing = (bool)bsp_touch_get_coordinates(&td);

      if (pressing && !touchDown)
      {
        // Finger down: record position and time
        touchDown = true;
        touchX = (int16_t)td.coords[0].x;
        touchY = (int16_t)td.coords[0].y;
        touchDownMs = now;
        longFired = false;
      }
      else if (!pressing && touchDown)
      {
        // Finger up: fire tap if long-press did not already fire
        touchDown = false;
        if (!longFired)
          handleTap(touchX, touchY);
      }
      // Long-press threshold: still down after TOUCH_LONG_PRESS_MS
      if (touchDown && !longFired && (now - touchDownMs) >= TOUCH_LONG_PRESS_MS)
      {
        longFired = true;
        handleLongPress(touchX, touchY);
      }
    }
  }

  // ── Stopwatch digit refresh at 10 Hz ──────────────────────────────────────
  if (sw_running)
  {
    uint32_t tenth = swElapsed() / 100;
    if (tenth != s_lastDisplayTenth)
    {
      s_lastDisplayTenth = tenth;
      updateStopwatchDigits();
    }
  }

  // ── Task-name marquee tick ────────────────────────────────────────────────
  if ((int)strlen(s_taskName) > TASK_VIS_CHARS &&
      (now - s_lastTaskScrollMs) >= TASK_SCROLL_MS)
  {
    s_lastTaskScrollMs = now;
    s_taskPixelOff += TASK_SCROLL_PX;
    if (s_taskPixelOff >= ((int)strlen(s_taskName) + 3) * TASK_CHAR_W)
      s_taskPixelOff = 0;
    drawTaskNameLine();
  }

  // ── Drain the ESP-NOW receive queue ───────────────────────────────────────
  RecvPacket pkt;
  while (s_recvQueue && xQueueReceive(s_recvQueue, &pkt, 0) == pdTRUE)
  {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, pkt.data, pkt.len);
    if (err)
      continue;

    Serial.printf("%.*s\r\n", pkt.len, (const char *)pkt.data);

    const char *msgType = doc["t"] | "";
    JsonVariant payload = doc["d"];

    if (strcmp(msgType, "time") == 0)
      handleTime(payload.as<JsonObjectConst>());

    yield(); // allow FreeRTOS scheduler to run between packets
  }

  // ── Periodic battery voltage refresh (every 10 s) ─────────────────────────
  if (s_pmuAvailable)
  {
    static unsigned long lastVoltMs = 0;
    if (now - lastVoltMs >= 10000UL)
    {
      lastVoltMs = now;
      drawStatusLine();
    }
  }
}
