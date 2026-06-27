/**
 * ESP8266 ESP-NOW Receiver — F3K Timer Reference Implementation
 *
 * Receives JSON broadcasts from the f3k-timer ESPNow plugin and dispatches
 * them to typed stub handler functions.
 *
 * Packet format (all messages):
 *   {"t": "<type>", "d": <data>}
 *
 * Message types:
 *   "time"  — current timer state, broadcast every tick (rate-limited by plugin)
 *   "p_def" — pilot definition, sent during prep section
 *   "p_list"— list of pilot IDs in the current group
 *
 * Dependencies (PlatformIO / Arduino Library Manager):
 *   - ArduinoJson  >= 6.x  (bblanchon/ArduinoJson)
 *   - ESP8266WiFi          (bundled with ESP8266 Arduino core)
 *   - espnow               (bundled with ESP8266 Arduino core >= 2.5.0)
 */

#include <ESP8266WiFi.h>
#include <espnow.h>
#include <ArduinoJson.h>
extern "C"
{
#include "user_interface.h" // for wifi_set_channel()
}

// ---------------------------------------------------------------------------
// Pilot cache — populated from p_def messages
// ---------------------------------------------------------------------------

#define MAX_PILOTS 8

struct PilotEntry
{
  int id;
  char name[32];
};

static PilotEntry s_pilots[MAX_PILOTS];
static int s_pilotCount = 0;

/** Return the cached display name for a pilot ID, or the numeric ID as fallback. */
static const char *pilotName(int id)
{
  for (int i = 0; i < s_pilotCount; i++)
  {
    if (s_pilots[i].id == id)
      return s_pilots[i].name;
  }
  static char fallback[16];
  snprintf(fallback, sizeof(fallback), "%d", id);
  return fallback;
}

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------

/**
 * Handle a "time" message.
 *
 * @param data  JSON object with the following fields:
 *   slot_time  int     Seconds remaining in the current section window.
 *   no_fly     bool    True when the current section is a no-fly period.
 *   time_s     string  Human-readable time, e.g. "02:30" (MM:SS).
 *   r_num      int     Round number (or "-" when not started).
 *   g_let      string  Group letter, e.g. "A" (or "-" when not started).
 *   f_num      int     Flight / sub-section index within the section type.
 *   sect       string  Section description, e.g. "Working Time".
 *   task_name  string  Task name, e.g. "Task F".
 */
void handleTime(JsonObjectConst data);

/**
 * Handle a "p_def" (pilot definition) message.
 * Sent once per pilot at the start of a prep section and every ~60 s.
 *
 * @param data  JSON object with the following fields:
 *   id    string  Pilot ID (matches IDs in p_list).
 *   name  string  Full display name, e.g. "Jane Smith".
 */
void handlePilotDef(JsonObjectConst data);

/**
 * Handle a "p_list" (pilot list) message.
 * Sent shortly after p_def messages during the prep section.
 *
 * @param data  JSON array of pilot ID strings for the current group,
 *              in flying order.
 */
void handlePilotList(JsonArrayConst data);

// ---------------------------------------------------------------------------
// ESP-NOW receive callback
// ---------------------------------------------------------------------------

void onDataRecv(uint8_t *mac, uint8_t *incomingData, uint8_t len)
{
  // Packets are always < 250 bytes (asserted by the plugin).
  StaticJsonDocument<512> doc;

  DeserializationError err = deserializeJson(doc, incomingData, len);
  if (err)
  {
    Serial.print(F("[ESPNow] JSON parse error: "));
    Serial.println(err.c_str());
    return;
  }

  const char *msgType = doc["t"] | "";
  JsonVariant data = doc["d"];

  if (strcmp(msgType, "time") == 0)
  {
    handleTime(data.as<JsonObjectConst>());
  }
  else if (strcmp(msgType, "p_def") == 0)
  {
    handlePilotDef(data.as<JsonObjectConst>());
  }
  else if (strcmp(msgType, "p_list") == 0)
  {
    handlePilotList(data.as<JsonArrayConst>());
  }
  else
  {
    Serial.printf("[ESPNow] Unknown message type: %s  raw (%d bytes): %.*s\n",
                  msgType, len, len, (const char *)incomingData);
  }
}

// ---------------------------------------------------------------------------
// Stub handlers — implement your display / storage logic here
// ---------------------------------------------------------------------------

void handleTime(JsonObjectConst data)
{
  int slotTime = data["slot_time"] | 0;

  // Discard messages where slot_time hasn't changed — display is 1-second resolution.
  static int lastSlotTime = -1;
  if (slotTime == lastSlotTime)
    return;
  lastSlotTime = slotTime;

  bool noFly = data["no_fly"] | false;
  const char *timeStr = data["time_s"] | "--:--";
  int roundNum = data["r_num"] | 0;
  const char *groupLet = data["g_let"] | "-";
  int flightNum = data["f_num"] | 1;
  const char *sect = data["sect"] | "";
  const char *taskName = data["task_name"] | "";

  // TODO: update display, drive outputs, etc.
  Serial.printf("[time] %s  R%d G%s F%d  no_fly=%d  sect=%s\n",
                timeStr, roundNum, groupLet, flightNum, noFly, sect);
}

void handlePilotDef(JsonObjectConst data)
{
  int id = data["id"] | 0;
  const char *name = data["name"] | "";

  Serial.printf("[p_def] id=%d  name=%s\n", id, name);

  // Update existing cache entry or append a new one
  for (int i = 0; i < s_pilotCount; i++)
  {
    if (s_pilots[i].id == id)
    {
      strncpy(s_pilots[i].name, name, sizeof(s_pilots[i].name) - 1);
      return;
    }
  }
  if (s_pilotCount < MAX_PILOTS)
  {
    s_pilots[s_pilotCount].id = id;
    strncpy(s_pilots[s_pilotCount].name, name, sizeof(s_pilots[0].name) - 1);
    s_pilotCount++;
  }
}

void handlePilotList(JsonArrayConst data)
{
  // data is an ordered array of pilot IDs (integers) for the current group.
  // pilotName() resolves each ID to the name received in earlier p_def messages.
  Serial.print(F("[p_list] group order: "));
  int pos = 1;
  for (JsonVariantConst v : data)
  {
    int id = v.as<int>();
    Serial.printf("%d. %s  ", pos++, pilotName(id));
  }
  Serial.println();

  // TODO: store ordered list and render to display
}

// ---------------------------------------------------------------------------
// Arduino lifecycle
// ---------------------------------------------------------------------------

void setup()
{
  Serial.begin(115200);
  Serial.println(F("\n[F3K] ESP8266 ESP-NOW receiver starting"));

  // ESP-NOW requires Wi-Fi in station mode; no AP association needed.
  // Channel must match the sender (f3k-timer broadcasts on channel 4).
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  wifi_set_channel(4);

  if (esp_now_init() != 0)
  {
    Serial.println(F("[ESPNow] Initialisation failed"));
    return;
  }

  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(onDataRecv);

  Serial.print(F("[ESPNow] Receiver ready. MAC: "));
  Serial.println(WiFi.macAddress());
}

void loop()
{
  // ESP-NOW receive callbacks are delivered on the Arduino background task;
  // add any periodic work (display refresh, etc.) here.
}
