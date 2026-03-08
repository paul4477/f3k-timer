# Serial JSON Protocol — Decoder Reference

# This is no longer accurate

This document describes the serial protocol emitted by `plugin_serialjson.py` and provides C code for decoding it on an Arduino platform.

---

## Connection parameters

| Parameter | Value                                          |
| --------- | ---------------------------------------------- |
| Baud rate | 19200 (default; check `config.yml` `baud` key) |
| Data bits | 8                                              |
| Parity    | None                                           |
| Stop bits | 1                                              |

---

## Wire format

Every message is framed identically:

```
[ 2 bytes: uint16 big-endian length ][ <length> bytes: ASCII JSON ]
```

The length prefix counts only the JSON payload bytes, not itself.

```c
// Example framing structure
struct Message {
    uint16_t length;   // big-endian, MSB first
    char     json[];   // ASCII, NOT null-terminated — add your own '\0'
};
```

---

## Arduino read loop

```c
#include <Arduino.h>
#include <ArduinoJson.h>   // https://arduinojson.org/ — v6 or v7

#define SERIAL_BAUD 19200
#define JSON_BUF_SIZE 512

void setup() {
    Serial.begin(SERIAL_BAUD);
    // If using a second hardware UART for the timer, replace Serial with Serial1 etc.
}

void loop() {
    if (readMessage()) {
        // message was parsed — handle in readMessage()
    }
}

bool readMessage() {
    // ── 1. Wait for the 2-byte length prefix ──────────────────────────────
    if (Serial.available() < 2) return false;

    uint8_t hi = Serial.read();
    uint8_t lo = Serial.read();
    uint16_t msgLen = ((uint16_t)hi << 8) | lo;   // big-endian reassembly

    if (msgLen == 0 || msgLen >= JSON_BUF_SIZE) {
        // Corrupt frame — discard and resync
        while (Serial.available()) Serial.read();
        return false;
    }

    // ── 2. Read exactly msgLen bytes of JSON ──────────────────────────────
    char buf[JSON_BUF_SIZE];
    uint16_t received = 0;
    unsigned long deadline = millis() + 500;   // 500 ms timeout

    while (received < msgLen && millis() < deadline) {
        if (Serial.available()) {
            buf[received++] = Serial.read();
        }
    }
    if (received < msgLen) return false;   // timeout
    buf[received] = '\0';                  // null-terminate for ArduinoJson

    // ── 3. Parse the envelope ─────────────────────────────────────────────
    StaticJsonDocument<JSON_BUF_SIZE> doc;
    DeserializationError err = deserializeJson(doc, buf);
    if (err) return false;

    const char* msgType = doc["t"];   // message type string
    JsonObject  data    = doc["d"];   // payload object

    // ── 4. Dispatch by message type ───────────────────────────────────────
    if (strcmp(msgType, "time") == 0) {
        handleTime(data);
    } else if (strcmp(msgType, "p_def") == 0) {
        handlePilotDef(data);
    } else if (strcmp(msgType, "p_list") == 0) {
        handlePilotList(doc["d"]);   // array, not object
    }

    return true;
}
```

---

## Message types and payload fields

### `"time"` — sent every second

```c
void handleTime(JsonObject d) {
    int      slotTime  = d["slot_time"];  // int  — seconds remaining in current section
    bool     noFly     = d["no_fly"];     // bool — true = no-fly period active
    // time_s: "MM:SS" countdown, "--:--" during announcement,
    //         or "HH:MM" wall clock during ShowTime/idle sections
    const char* timeStr  = d["time_s"];
    int      roundNum  = d["r_num"];      // int or "-" when not running
    // g_let: group letter A/B/C... or "-"
    const char* groupLet = d["g_let"];
    int      flightNum = d["f_num"];      // int — index of this flight within the group
    const char* section  = d["sect"];     // human-readable section name, e.g. "Working Time"
    const char* taskName = d["task_name"];// e.g. "Last Flight"

    // Example: drive a 4-digit 7-segment display
    // time_s is always exactly 5 chars ("MM:SS") or 5 chars ("--:--") or 5 chars ("HH:MM")
}
```

**`sect` values** (from section class `get_description()`):

| `sect` string                | Meaning                                       |
| ---------------------------- | --------------------------------------------- |
| `"Preparation Time"`         | Pre-flight prep window                        |
| `"Test Time"`                | Test flight allowed                           |
| `"No Fly"`                   | No-fly enforced                               |
| `"Working Time"`             | Score-able flight window                      |
| `"Landing Time"`             | Landing window                                |
| `"Waiting for next group"`   | Gap between groups                            |
| `"Announcement in progress"` | Group pilot list being read out               |
| `"Actual Time HH:MM"`        | Pre-competition idle — `time_s` is wall clock |

---

### `"p_def"` — pilot definition

Sent at the start of each prep section and then every 60 s during prep.

```c
void handlePilotDef(JsonObject d) {
    int         id   = d["id"];    // int — pilot ID number
    const char* name = d["name"];  // string — "First Last"
    // Store in a local lookup table keyed by id
}
```

---

### `"p_list"` — ordered pilot list for the current group

Sent alongside each `p_def` batch.

```c
void handlePilotList(JsonVariant d) {
    // d is a JSON array of pilot ID integers, in slot order
    JsonArray arr = d.as<JsonArray>();
    int slotIndex = 0;
    for (JsonVariant v : arr) {
        int pilotId = v.as<int>();
        // map slotIndex → pilotId; look up name from your p_def table
        slotIndex++;
    }
}
```

---

## Notes

- **Resync:** if the length prefix looks implausible (> buffer size, or you fall behind), flush `Serial` and wait for the next clean frame — the timer sends a new `time` message every second.
- **`time_s` vs `slot_time`:** `slot_time` is always a plain integer (seconds remaining); `time_s` is the formatted string ready for display and already handles the special cases (`--:--` during announcements, wall clock during idle).
- **No-fly indicator:** use `no_fly` to drive a red/green LED or buzzer lockout — it is `true` during prep, no-fly, landing, gap, and announcement sections, and `false` only during test and working sections.
