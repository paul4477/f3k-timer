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

#define RECV_RING_LEN 16
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
// ESP-NOW receive callback
// ---------------------------------------------------------------------------

void onDataRecv(uint8_t *mac, uint8_t *incomingData, uint8_t len)
{
  // Discard duplicate packets — ESP-NOW can re-deliver the same frame.
  // Exception: if no packet has been forwarded for 5 s, allow a duplicate
  // through anyway to prevent the downstream device treating the link as down.
  static uint8_t lastData[MAX_PACKET_LEN];
  static uint8_t lastLen = 0;
  static unsigned long lastSentMs = 0;
  bool isDuplicate = (len == lastLen && memcmp(incomingData, lastData, len) == 0);
  if (isDuplicate && (millis() - lastSentMs < 5000))
    return;
  lastLen = (len < MAX_PACKET_LEN) ? len : MAX_PACKET_LEN - 1;
  memcpy(lastData, incomingData, lastLen);

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
  lastSentMs = millis();
  asm volatile("" ::: "memory"); // ensure data is written before head advances
  s_ringHead = nextHead;
}

// ---------------------------------------------------------------------------
// Arduino lifecycle
// ---------------------------------------------------------------------------

void setup()
{
  Serial.begin(115200);

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
    // Write out the received packet verbatim
    Serial.printf("%.*s\r\n", pkt.len, (const char *)pkt.data);
    s_ringTail = (s_ringTail + 1) % RECV_RING_LEN;
    yield(); // allow SDK background tasks (WiFi, watchdog) to run
  }
}
