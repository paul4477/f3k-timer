# Serial JSON Protocol — Decoder Reference

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

Every message is a single line of ASCII JSON terminated by a carriage-return (`\r`):

```
[ ASCII JSON ][ \r ]
```

There is no length prefix. Read bytes until you receive `\r`, then parse the accumulated buffer as JSON.

---

## Arduino read loop

```c
#include <Arduino.h>
#include <ArduinoJson.h>   // https://arduinojson.org/ — v6 or v7

#define SERIAL_BAUD  19200
#define JSON_BUF_SIZE 512

char buf[JSON_BUF_SIZE];

void setup() {
    Serial.begin(SERIAL_BAUD);
    // If using a second hardware UART for the timer, replace Serial with Serial1 etc.
}

void loop() {
    // readBytesUntil blocks until '\r' received or buffer full.
    // Returns the number of bytes placed in buf (the '\r' itself is NOT included).
    int len = Serial.readBytesUntil('\r', buf, JSON_BUF_SIZE - 1);
    if (len <= 0) return;
    buf[len] = '\0';   // null-terminate for ArduinoJson

    // ── Parse the envelope ────────────────────────────────────────────────
    StaticJsonDocument<JSON_BUF_SIZE> doc;
    DeserializationError err = deserializeJson(doc, buf);
    if (err) return;

    const char* msgType = doc["t"];   // message type string
    JsonObject  data    = doc["d"];   // payload object

    // ── Dispatch by message type ──────────────────────────────────────────
    if (strcmp(msgType, "time") == 0) {
        handleTime(data);
    } else if (strcmp(msgType, "p_def") == 0) {
        handlePilotDef(data);
    } else if (strcmp(msgType, "p_list") == 0) {
        handlePilotList(doc["d"]);   // array, not object
    }
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

- **Resync:** if `deserializeJson` returns an error, the frame was corrupt or you fell behind. Simply discard the buffer and call `readBytesUntil` again — the timer sends a new `time` message every second so recovery is automatic.
- **`time_s` vs `slot_time`:** `slot_time` is always a plain integer (seconds remaining); `time_s` is the formatted string ready for display and already handles the special cases (`--:--` during announcements, wall clock during idle).
- **No-fly indicator:** use `no_fly` to drive a red/green LED or buzzer lockout — it is `true` during prep, no-fly, landing, gap, and announcement sections, and `false` only during test and working sections.
