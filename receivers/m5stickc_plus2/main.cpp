/**
 * M5StickC Plus2 ESP-NOW Receiver — F3K Timer Reference Implementation
 *
 * Target: M5StickC Plus2 (ESP32-PICO-V3-02, 240×135 LCD, landscape)
 *
 * Receives JSON broadcasts from the f3k-timer ESPNow plugin and renders
 * live timer state on the built-in LCD. All events are also logged to Serial
 * (accessible via the onboard CH9102F USB-UART bridge at 115200 baud).
 *
 * Display layout (landscape 240×135):
 *
 *   ┌──────────────────────────────────────┐
 *   │ Task F                               │  ← task name  (size 1, grey)
 *   │ R1  GA  F1                           │  ← round/group/flight (size 2)
 *   │ Prep / Working Time                  │  ← section name (size 1, yellow)
 *   │                                      │
 *   │       02:30          [NO-FLY]        │  ← big time   (size 5, green/red)
 *   │                                      │
 *   │ NO-FLY                               │  ← banner when in no-fly period
 *   └──────────────────────────────────────┘
 *
 * During prep sections the pilot roster replaces the main area:
 *
 *   ┌──────────────────────────────────────┐
 *   │ PREP  R1 GA                          │
 *   │ 1. Jane Smith                        │
 *   │ 2. Bob Jones                         │
 *   │ 3. Alice Brown                       │  ← up to MAX_PILOTS rows
 *   │ ...                          02:30   │  ← countdown in corner
 *   └──────────────────────────────────────┘
 *
 * Dependencies (Library Manager / PlatformIO):
 *   - M5StickCPlus2  (M5Stack)              — provides M5.Lcd (TFT_eSPI)
 *   - ArduinoJson >= 6.x  (bblanchon/ArduinoJson)
 *   - esp_now, esp_wifi  (bundled with ESP32 Arduino core / esp-idf)
 *
 * Note: receive callback uses ESP32 Arduino core 3.x (esp-idf 5.x) signature.
 * For core 2.x replace:
 *   void onDataRecv(const esp_now_recv_info_t *recv_info, ...)
 * with:
 *   void onDataRecv(const uint8_t *mac, ...)
 */

#include <M5StickCPlus2.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <ArduinoJson.h>

// Screen dimensions when rotation = 3 (landscape, USB-C on left)
static constexpr int SCR_W = 240;
static constexpr int SCR_H = 135;

// ---------------------------------------------------------------------------
// Pilot cache — populated from p_def / p_list messages
// ---------------------------------------------------------------------------

#define MAX_PILOTS 8

struct PilotEntry {
    char id[16];
    char name[32];
};

static PilotEntry s_pilots[MAX_PILOTS];
static int        s_pilotCount = 0;

// Ordered pilot IDs for the current group (from p_list)
static char s_groupOrder[MAX_PILOTS][16];
static int  s_groupSize = 0;

/** Return cached display name for a pilot id, or the id itself as fallback. */
static const char *pilotName(const char *id) {
    for (int i = 0; i < s_pilotCount; i++) {
        if (strcmp(s_pilots[i].id, id) == 0) return s_pilots[i].name;
    }
    return id;
}

// ---------------------------------------------------------------------------
// Display state
// ---------------------------------------------------------------------------

static char s_timeStr[8]   = "--:--";
static bool s_noFly        = false;
static int  s_roundNum     = 0;
static char s_groupLet[4]  = "-";
static int  s_flightNum    = 1;
static char s_sect[40]     = "";
static char s_taskName[32] = "";
static bool s_inPrep       = false;
static bool s_needRedraw   = true;

// ---------------------------------------------------------------------------
// LCD rendering
// ---------------------------------------------------------------------------

static void drawTimerScreen() {
    M5.Lcd.fillScreen(BLACK);

    // Task name — top row, small grey text
    M5.Lcd.setTextSize(1);
    M5.Lcd.setTextColor(DARKGREY, BLACK);
    M5.Lcd.setCursor(2, 2);
    M5.Lcd.print(s_taskName);

    // Round / Group / Flight
    M5.Lcd.setTextSize(2);
    M5.Lcd.setTextColor(WHITE, BLACK);
    M5.Lcd.setCursor(2, 14);
    M5.Lcd.printf("R%-2d G%s F%d", s_roundNum, s_groupLet, s_flightNum);

    // Section description
    M5.Lcd.setTextSize(1);
    M5.Lcd.setTextColor(YELLOW, BLACK);
    M5.Lcd.setCursor(2, 34);
    M5.Lcd.print(s_sect);

    // Time — large, colour-coded green (fly) / red (no-fly)
    M5.Lcd.setTextSize(5);
    M5.Lcd.setTextColor(s_noFly ? RED : GREEN, BLACK);
    M5.Lcd.setCursor(20, 50);
    M5.Lcd.print(s_timeStr);

    // No-fly banner at bottom
    if (s_noFly) {
        M5.Lcd.setTextSize(2);
        M5.Lcd.setTextColor(RED, BLACK);
        M5.Lcd.setCursor(2, 115);
        M5.Lcd.print("NO-FLY");
    }
}

static void updateTimeRegion() {
    // Redraw only the time digits — avoids full-screen flicker at ~6 Hz.
    // setTextColor(fg, bg) fills the character cell background, so no
    // separate fillRect is needed.
    M5.Lcd.setTextSize(5);
    M5.Lcd.setTextColor(s_noFly ? RED : GREEN, BLACK);
    M5.Lcd.setCursor(20, 50);
    M5.Lcd.print(s_timeStr);

    // Keep no-fly banner in sync without clearing the rest of the screen
    M5.Lcd.setTextSize(2);
    if (s_noFly) {
        M5.Lcd.setTextColor(RED, BLACK);
        M5.Lcd.setCursor(2, 115);
        M5.Lcd.print("NO-FLY");
    } else {
        M5.Lcd.setTextColor(BLACK, BLACK);  // erase if no longer in no-fly
        M5.Lcd.setCursor(2, 115);
        M5.Lcd.print("NO-FLY");
    }
}

static void drawPrepScreen() {
    M5.Lcd.fillScreen(BLACK);

    // Header
    M5.Lcd.setTextSize(2);
    M5.Lcd.setTextColor(CYAN, BLACK);
    M5.Lcd.setCursor(2, 2);
    M5.Lcd.printf("PREP  R%d G%s", s_roundNum, s_groupLet);

    // Pilot roster — one row per pilot, 14 px apart at size 1
    M5.Lcd.setTextSize(1);
    M5.Lcd.setTextColor(WHITE, BLACK);
    for (int i = 0; i < s_groupSize && i < MAX_PILOTS; i++) {
        M5.Lcd.setCursor(2, 26 + i * 13);
        M5.Lcd.printf("%d. %s", i + 1, pilotName(s_groupOrder[i]));
    }

    // Countdown in bottom-right corner
    M5.Lcd.setTextSize(3);
    M5.Lcd.setTextColor(YELLOW, BLACK);
    M5.Lcd.setCursor(152, 102);
    M5.Lcd.print(s_timeStr);
}

static void updatePrepCountdown() {
    M5.Lcd.setTextSize(3);
    M5.Lcd.setTextColor(YELLOW, BLACK);
    M5.Lcd.setCursor(152, 102);
    M5.Lcd.print(s_timeStr);
}

// ---------------------------------------------------------------------------
// Message handlers
// ---------------------------------------------------------------------------

void handleTime(JsonObjectConst data) {
    int        slotTime  = data["slot_time"] | 0;
    bool       noFly     = data["no_fly"]    | false;
    const char *timeStr  = data["time_s"]    | "--:--";
    int        roundNum  = data["r_num"]     | 0;
    const char *groupLet = data["g_let"]     | "-";
    int        flightNum = data["f_num"]     | 1;
    const char *sect     = data["sect"]      | "";
    const char *taskName = data["task_name"] | "";

    Serial.printf("[time] %s  R%d G%s F%d  no_fly=%d  sect=%s\n",
                  timeStr, roundNum, groupLet, flightNum, noFly, sect);

    bool sectionChanged = (strcmp(sect, s_sect) != 0);
    bool noFlyChanged   = (noFly != s_noFly);
    bool nowInPrep      = (strstr(sect, "rep") != nullptr);  // "Prep"

    strncpy(s_timeStr,  timeStr,  sizeof(s_timeStr)  - 1);
    strncpy(s_sect,     sect,     sizeof(s_sect)     - 1);
    strncpy(s_taskName, taskName, sizeof(s_taskName) - 1);
    strncpy(s_groupLet, groupLet, sizeof(s_groupLet) - 1);
    s_noFly     = noFly;
    s_roundNum  = roundNum;
    s_flightNum = flightNum;

    if (sectionChanged || noFlyChanged || (nowInPrep != s_inPrep) || s_needRedraw) {
        s_inPrep     = nowInPrep;
        s_needRedraw = false;
        if (s_inPrep) drawPrepScreen(); else drawTimerScreen();
    } else {
        if (s_inPrep) updatePrepCountdown(); else updateTimeRegion();
    }
}

void handlePilotDef(JsonObjectConst data) {
    const char *id   = data["id"]   | "";
    const char *name = data["name"] | "";

    Serial.printf("[p_def] id=%s  name=%s\n", id, name);

    // Update existing entry or append
    for (int i = 0; i < s_pilotCount; i++) {
        if (strcmp(s_pilots[i].id, id) == 0) {
            strncpy(s_pilots[i].name, name, sizeof(s_pilots[i].name) - 1);
            return;
        }
    }
    if (s_pilotCount < MAX_PILOTS) {
        strncpy(s_pilots[s_pilotCount].id,   id,   sizeof(s_pilots[0].id)   - 1);
        strncpy(s_pilots[s_pilotCount].name, name, sizeof(s_pilots[0].name) - 1);
        s_pilotCount++;
    }
}

void handlePilotList(JsonArrayConst data) {
    s_groupSize = 0;
    Serial.print("[p_list] pilots:");
    for (JsonVariantConst v : data) {
        const char *id = v.as<const char *>();
        if (id && s_groupSize < MAX_PILOTS) {
            strncpy(s_groupOrder[s_groupSize++], id, sizeof(s_groupOrder[0]) - 1);
            Serial.printf(" %s", id);
        }
    }
    Serial.println();
    s_needRedraw = true;  // force roster redraw on next tick
}

// ---------------------------------------------------------------------------
// ESP-NOW receive callback (ESP32 Arduino core 3.x / esp-idf 5.x)
// ---------------------------------------------------------------------------

void onDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, incomingData, len);
    if (err) {
        Serial.printf("[ESPNow] JSON parse error: %s\n", err.c_str());
        return;
    }

    const char *msgType = doc["t"] | "";
    JsonVariant data    = doc["d"];

    if      (strcmp(msgType, "time")   == 0) handleTime(data.as<JsonObjectConst>());
    else if (strcmp(msgType, "p_def")  == 0) handlePilotDef(data.as<JsonObjectConst>());
    else if (strcmp(msgType, "p_list") == 0) handlePilotList(data.as<JsonArrayConst>());
    else Serial.printf("[ESPNow] Unknown message type: %s\n", msgType);
}

// ---------------------------------------------------------------------------
// Arduino lifecycle
// ---------------------------------------------------------------------------

void setup() {
    M5.begin();
    M5.Lcd.setRotation(3);        // landscape: 240 × 135, USB-C on left
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextColor(WHITE, BLACK);

    Serial.begin(115200);
    Serial.println("\n[F3K] M5StickC Plus2 ESP-NOW receiver starting");

    // ESP-NOW requires Wi-Fi in station mode; no AP association needed.
    // Channel must match the sender (f3k-timer broadcasts on channel 4).
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    esp_wifi_set_channel(4, WIFI_SECOND_CHAN_NONE);

    if (esp_now_init() != ESP_OK) {
        Serial.println("[ESPNow] Initialisation failed");
        M5.Lcd.setTextSize(2);
        M5.Lcd.setTextColor(RED, BLACK);
        M5.Lcd.setCursor(10, 55);
        M5.Lcd.print("ESP-NOW INIT FAIL");
        return;
    }

    // No peer registration required to receive broadcast packets on ESP32.
    esp_now_register_recv_cb(onDataRecv);

    Serial.printf("[ESPNow] Ready. MAC: %s\n", WiFi.macAddress().c_str());

    // Splash screen — replaced by first incoming packet
    M5.Lcd.setTextSize(3);
    M5.Lcd.setTextColor(CYAN, BLACK);
    M5.Lcd.setCursor(30, 40);
    M5.Lcd.print("F3K TIMER");
    M5.Lcd.setTextSize(1);
    M5.Lcd.setTextColor(DARKGREY, BLACK);
    M5.Lcd.setCursor(10, 90);
    M5.Lcd.print("Waiting for broadcast...");
    M5.Lcd.setCursor(10, 105);
    M5.Lcd.printf("MAC: %s", WiFi.macAddress().c_str());
}

void loop() {
    M5.update();  // poll buttons and power management — required by M5 library
    // Add button-driven actions here, e.g.:
    // if (M5.BtnA.wasPressed()) { ... }
}
