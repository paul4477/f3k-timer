# F3K Timer — ESP-NOW Receiver Reference Implementations

This directory contains reference implementations for microcontrollers that
receive ESP-NOW broadcasts from the f3k-timer `ESPNow` plugin
(`plugin_espnow.py`).

---

## Implementations

### `esp8266_arduino/` — ESP8266 (Arduino C++)

**Toolchain:** Arduino IDE or PlatformIO with the ESP8266 Arduino core.

**Required libraries:**

| Library           | Source                                                  |
| ----------------- | ------------------------------------------------------- |
| ArduinoJson ≥ 6.x | `bblanchon/ArduinoJson` (Library Manager or PlatformIO) |
| ESP8266WiFi       | Bundled with ESP8266 Arduino core                       |
| espnow            | Bundled with ESP8266 Arduino core ≥ 2.5.0               |

**Key file:** [esp8266_arduino/main.cpp](esp8266_arduino/main.cpp)

Fill in the three stub functions:

- `handleTime(JsonObjectConst data)`
- `handlePilotDef(JsonObjectConst data)`
- `handlePilotList(JsonArrayConst data)`

---

### `esp32_arduino/` — ESP32 (Arduino C++)

**Toolchain:** Arduino IDE or PlatformIO with the ESP32 Arduino core ≥ 3.x (esp-idf 5.x).

**Required libraries:**

| Library           | Source                                                  |
| ----------------- | ------------------------------------------------------- |
| ArduinoJson ≥ 6.x | `bblanchon/ArduinoJson` (Library Manager or PlatformIO) |
| WiFi              | Bundled with ESP32 Arduino core                         |
| esp_now           | Bundled with ESP32 Arduino core / esp-idf               |
| esp_wifi          | Bundled with ESP32 Arduino core / esp-idf               |

**Key file:** [esp32_arduino/main.cpp](esp32_arduino/main.cpp)

> **Arduino core 2.x users:** the receive callback signature differs. Replace:
>
> ```cpp
> void onDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len)
> ```
>
> with:
>
> ```cpp
> void onDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len)
> ```

Fill in the three stub functions:

- `handleTime(JsonObjectConst data)`
- `handlePilotDef(JsonObjectConst data)`
- `handlePilotList(JsonArrayConst data)`

---

### `esp32_micropython/` — ESP32 (MicroPython)

**Toolchain:** MicroPython ≥ 1.19 (built-in `espnow` module required).
Flash with [esptool](https://github.com/espressif/esptool) or Thonny.

> **ESP8266 + MicroPython is not supported.** The `espnow` module does not exist
> in the ESP8266 MicroPython port. Use `esp8266_arduino/` for that hardware.

**Key file:** [esp32_micropython/main.py](esp32_micropython/main.py)

Fill in the three stub functions:

- `handle_time(data: dict)`
- `handle_pilot_def(data: dict)`
- `handle_pilot_list(data: list)`

Copy `main.py` to the device root so MicroPython runs it automatically on boot.

---

### `m5stickc_plus2/` — M5StickC Plus2 (Arduino C++)

**Toolchain:** Arduino IDE or PlatformIO with the ESP32 Arduino core ≥ 3.x (esp-idf 5.x).

**Required libraries:**

| Library           | Source                                                  |
| ----------------- | ------------------------------------------------------- |
| M5StickCPlus2     | M5Stack (Library Manager or PlatformIO)                 |
| ArduinoJson ≥ 6.x | `bblanchon/ArduinoJson` (Library Manager or PlatformIO) |
| esp_now, esp_wifi | Bundled with ESP32 Arduino core / esp-idf               |

**Key file:** [m5stickc_plus2/main.cpp](m5stickc_plus2/main.cpp)

This is a fully functional example rather than a stub — it drives the built-in
135×240 LCD (landscape) as well as Serial (CH9102F USB-UART, 115200 baud):

- **Timer screen** — large colour-coded countdown (green = fly, red = no-fly),
  round/group/flight, section name, and a NO-FLY banner when applicable.
- **Prep screen** — pilot roster in flying order with a small countdown in the
  corner. Populated automatically from incoming `p_def`/`p_list` messages.
- Partial redraws on tick updates to avoid flicker; full redraw only on section
  or no-fly state changes.

`M5.update()` is called each loop iteration for button polling — add
`M5.BtnA.wasPressed()` / `M5.BtnB.wasPressed()` checks there as needed.

> **Arduino core 2.x users:** replace the callback signature as noted in the
> file header comment.

---

## Implementation comparison

|                             | ESP8266 Arduino                             | ESP32 Arduino                                    | ESP32 MicroPython                                        | M5StickC Plus2                                   |
| --------------------------- | ------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------- | ------------------------------------------------ |
| Wi-Fi header                | `<ESP8266WiFi.h>`                           | `<WiFi.h>`                                       | `network` module                                         | via `<M5StickCPlus2.h>`                          |
| ESP-NOW header              | `<espnow.h>`                                | `<esp_now.h>` + `<esp_wifi.h>`                   | `espnow` module                                          | `<esp_now.h>` + `<esp_wifi.h>`                   |
| Channel setting             | `wifi_set_channel(4)` (SDK)                 | `esp_wifi_set_channel(4, WIFI_SECOND_CHAN_NONE)` | `wlan.config(channel=4)`                                 | `esp_wifi_set_channel(4, WIFI_SECOND_CHAN_NONE)` |
| Role setup                  | `esp_now_set_self_role(ESP_NOW_ROLE_SLAVE)` | Not needed                                       | Not needed                                               | Not needed                                       |
| Callback style              | `esp_now_register_recv_cb()`                | `esp_now_register_recv_cb()`                     | `e.irq()`                                                | `esp_now_register_recv_cb()`                     |
| Broadcast peer registration | Not needed                                  | Not needed                                       | **Required** — `e.add_peer(b'\xff\xff\xff\xff\xff\xff')` | Not needed                                       |
| LCD output                  | —                                           | —                                                | —                                                        | Yes — timer + prep roster                        |
| Serial output               | `Serial` via CH9102F                        | `Serial` (UART0)                                 | `print()`                                                | `Serial` via CH9102F                             |

---

## Notes

- All receivers use channel 4, which must match the sender. The channel is set in
  `config.yml` on the f3k-timer host (not yet configurable in the plugin; currently
  hardcoded via the Wi-Fi interface channel at startup).
- The sender broadcasts to `FF:FF:FF:FF:FF:FF`; no receiver pairing is required on
  the sender side.
- All implementations use an interrupt/callback model. The `loop()` / `while True`
  body is intentionally empty — add periodic work (display refresh, etc.) there.
- The plugin only sends `p_def`/`p_list` during prep sections. Receivers should
  cache pilot data for use during working time.
- `p_def` messages arrive one per pilot. Wait for `p_list` to know the full group
  composition and flying order before rendering a pilot roster.

---

## Message protocol

All packets are JSON objects of the form:

```json
{"t": "<type>", "d": <data>}
```

| `t` value  | Trigger                                            | `d` payload                    |
| ---------- | -------------------------------------------------- | ------------------------------ |
| `"time"`   | Every plugin tick (rate-limited, ~6 Hz by default) | Timer state object (see below) |
| `"p_def"`  | Prep section start and every ~60 s                 | Single pilot definition object |
| `"p_list"` | Prep section start, ~5 s after `p_def` messages    | Array of pilot IDs (integers)  |

Maximum packet size is 250 bytes (enforced by the plugin).

### `"time"` data fields

| Field       | Type            | Description                                     |
| ----------- | --------------- | ----------------------------------------------- |
| `slot_time` | int             | Seconds remaining in the current section window |
| `no_fly`    | bool            | `true` during no-fly periods                    |
| `time_s`    | string          | Display time `"MM:SS"`                          |
| `r_num`     | int \| `"-"`    | Round number                                    |
| `g_let`     | string \| `"-"` | Group letter (e.g. `"A"`)                       |
| `f_num`     | int \| `"-"`    | Flight index within section type                |
| `sect`      | string          | Section description (e.g. `"Working Time"`)     |
| `task_name` | string          | Task name (e.g. `"Task F"`)                     |

### `"p_def"` data fields

| Field  | Type   | Description                            |
| ------ | ------ | -------------------------------------- |
| `id`   | int    | Pilot ID (matches entries in `p_list`) |
| `name` | string | Full display name                      |

### `"p_list"` data

A JSON array of pilot IDs (integers) in flying order for the current group.
