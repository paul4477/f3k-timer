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
// Receive ring buffer — decouples Serial writes from the ESP-NOW callback
// so that a full TX buffer never blocks onDataRecv.
//
// On ESP8266 the callback runs in the SDK WiFi task and can preempt loop();
// volatile head/tail indices are sufficient for this single-producer /
// single-consumer arrangement.
// ---------------------------------------------------------------------------

#define RECV_RING_LEN 8
#define MAX_PACKET_LEN 251 // ESP-NOW max payload is 250 bytes

struct RecvPacket
{
  uint8_t data[MAX_PACKET_LEN];
  uint8_t len;
};

static RecvPacket s_recvRing[RECV_RING_LEN];
static volatile uint8_t s_ringHead = 0; // written by callback
static volatile uint8_t s_ringTail = 0; // read by loop()

// ---------------------------------------------------------------------------
// Pilot cache — populated from p_def messages
// ---------------------------------------------------------------------------

#define MAX_PILOTS 32

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
  // Copy into the ring buffer and return immediately — never block in this
  // callback.  If the buffer is full the packet is silently dropped
  // (preferable to stalling the SDK task while Serial drains its TX buffer).
  uint8_t nextHead = (s_ringHead + 1) % RECV_RING_LEN;
  if (nextHead == s_ringTail)
    return; // buffer full, drop packet

  RecvPacket &pkt = s_recvRing[s_ringHead];
  pkt.len = (len < MAX_PACKET_LEN) ? len : MAX_PACKET_LEN - 1;
  memcpy(pkt.data, incomingData, pkt.len);
  pkt.data[pkt.len] = '\0';
  s_ringHead = nextHead;
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

  // Reset pilot cache on group change — the plugin sends a full p_def
  // broadcast for every pilot in the new group during its prep section.
  static char lastGroupLet[4] = "";
  if (strcmp(groupLet, lastGroupLet) != 0)
  {
    strncpy(lastGroupLet, groupLet, sizeof(lastGroupLet) - 1);
    s_pilotCount = 0;
  }

  // TODO: update display, drive outputs, etc.
}

void handlePilotDef(JsonObjectConst data)
{
  int id = data["id"] | 0;
  const char *name = data["name"] | "";

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
  int pos = 1;
  for (JsonVariantConst v : data)
  {
    int id = v.as<int>();
    (void)pilotName(id);
    pos++;
  }

  // TODO: store ordered list and render to display
}

// ---------------------------------------------------------------------------
// Arduino lifecycle
// ---------------------------------------------------------------------------

void setup()
{
  Serial.begin(19200);

  // ESP-NOW requires Wi-Fi in station mode; no AP association needed.
  // Channel must match the sender (f3k-timer broadcasts on channel 4).
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  wifi_set_channel(4);

  if (esp_now_init() != 0)
  {
    return;
  }

  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(onDataRecv);
}

void loop()
{
  // Drain the receive ring buffer — Serial writes happen here, safely in loop().
  while (s_ringTail != s_ringHead)
  {
    RecvPacket &pkt = s_recvRing[s_ringTail];

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, pkt.data, pkt.len);
    if (!err)
    {
      // Write out the received packet verbatim
      Serial.printf("%.*s\r\n", pkt.len, (const char *)pkt.data);

      /*const char *msgType = doc["t"] | "";
      JsonVariant data = doc["d"];

      if (strcmp(msgType, "time") == 0)
        handleTime(data.as<JsonObjectConst>());
      else if (strcmp(msgType, "p_def") == 0)
        handlePilotDef(data.as<JsonObjectConst>());
      else if (strcmp(msgType, "p_list") == 0)
        handlePilotList(data.as<JsonArrayConst>());
      else
        Serial.printf("[ESPNow] Unknown message type: %s  raw (%d bytes): %.*s\n",
                      msgType, pkt.len, pkt.len, (const char *)pkt.data);*/
    }

    s_ringTail = (s_ringTail + 1) % RECV_RING_LEN;
  }
}
