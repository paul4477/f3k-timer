"""
ESP32 ESP-NOW Receiver — F3K Timer Reference Implementation (MicroPython)

Receives JSON broadcasts from the f3k-timer ESPNow plugin and dispatches
them to typed stub handler functions.

Packet format (all messages):
    {"t": "<type>", "d": <data>}

Message types:
    "time"   — current timer state, broadcast every tick (rate-limited by plugin)
    "p_def"  — pilot definition, sent during prep section
    "p_list" — list of pilot IDs in the current group

Tested with MicroPython >= 1.20 on ESP32.
The built-in `espnow` module is available from MicroPython 1.19+.
"""

import network
import espnow
import ujson


# ---------------------------------------------------------------------------
# Pilot cache — populated from p_def messages
# ---------------------------------------------------------------------------

# Maps pilot_id (int) -> display name (str).
# Populated by handle_pilot_def; consumed by handle_pilot_list.
# Cleared on each group change so stale data from previous groups is removed.
_pilots: dict = {}
_last_group_let: str = ""


# ---------------------------------------------------------------------------
# Stub handlers — implement your display / storage logic here
# ---------------------------------------------------------------------------

# Last seen slot_time — used to discard duplicate time messages at ~6 Hz.
_last_slot_time: int = -1


def handle_time(data: dict) -> None:
    """Handle a 'time' message (fired every tick, rate-limited by plugin).

    Args:
        data: dict with keys:
            slot_time  (int)   Seconds remaining in the current section window.
            no_fly     (bool)  True when the current section is a no-fly period.
            time_s     (str)   Human-readable time, e.g. "02:30" (MM:SS).
            r_num      (int)   Round number (or "-" when not started).
            g_let      (str)   Group letter, e.g. "A" (or "-" when not started).
            f_num      (int)   Flight / sub-section index within the section type.
            sect       (str)   Section description, e.g. "Working Time".
            task_name  (str)   Task name, e.g. "Task F".
    """
    global _last_slot_time, _last_group_let, _pilots
    slot_time = data.get("slot_time", -1)
    # Discard messages where slot_time hasn't changed — display is 1-second resolution.
    if slot_time == _last_slot_time:
        return
    _last_slot_time = slot_time

    # Reset pilot cache on group change — the plugin sends a full p_def
    # broadcast for every pilot in the new group during its prep section.
    g_let = data.get("g_let", "-")
    if g_let != _last_group_let:
        _last_group_let = g_let
        _pilots = {}

    # TODO: update display, drive outputs, etc.
    print("[time]", data.get("time_s"), "| round:", data.get("r_num"),
          "group:", data.get("g_let"), "no_fly:", data.get("no_fly"),
          "sect:", data.get("sect"))


def handle_pilot_def(data: dict) -> None:
    """Handle a 'p_def' (pilot definition) message.

    Sent once per pilot at the start of a prep section and again every ~60 s.

    Args:
        data: dict with keys:
            id    (str)  Pilot ID (matches IDs in p_list messages).
            name  (str)  Full display name, e.g. "Jane Smith".
    """
    _pilots[data.get("id", "")] = data.get("name", "")
    print("[p_def] id={id}  name={name}".format(**data))


def handle_pilot_list(data: list) -> None:
    """Handle a 'p_list' (pilot list) message.

    Sent shortly after the p_def messages during a prep section.

    Args:
        data: list of pilot ID strings for the current group, in flying order.
    """
    # Resolve each pilot ID to its cached display name (falls back to the raw
    # ID if the corresponding p_def message has not yet been received).
    print("[p_list] group order:")
    for i, pilot_id in enumerate(data, 1):
        print(f"  {i}. {_pilots.get(pilot_id, pilot_id)}")

    # TODO: store ordered list and render to display


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_HANDLERS = {
    "time":   handle_time,
    "p_def":  handle_pilot_def,
    "p_list": handle_pilot_list,
}


def _on_recv(e: espnow.ESPNow) -> None:
    """ESP-NOW receive IRQ callback.  `e` is the ESPNow instance."""
    while True:
        # drain all queued packets in one IRQ invocation
        host, msg = e.irecv(0)
        if host is None:
            break
        try:
            packet = ujson.loads(msg)
            msg_type = packet.get("t")
            data = packet.get("d")
            handler = _HANDLERS.get(msg_type)
            if handler:
                handler(data)
            else:
                print("[ESPNow] Unknown message type:", msg_type)
        except Exception as ex:
            print("[ESPNow] Error processing message:", ex)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # ESP-NOW requires Wi-Fi in station mode; no AP association is needed.
    # Channel must match the sender (f3k-timer broadcasts on channel 4).
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    wlan.config(channel=4)

    e = espnow.ESPNow()
    e.active(True)
    # Register the broadcast MAC so that broadcast ESP-NOW packets are delivered.
    # Without this, broadcast messages (FF:FF:FF:FF:FF:FF) are silently dropped
    # by the espnow module even when irq is configured.
    e.add_peer(b'\xff\xff\xff\xff\xff\xff')
    # irq() delivers received packets via callback rather than requiring polling.
    e.irq(_on_recv)

    print("[F3K] ESP32 ESP-NOW receiver ready")
    print("[F3K] MAC:", wlan.config("mac").hex(":"))

    # Keep the interpreter alive; all work is done in the IRQ callback.
    while True:
        pass


if __name__ == "__main__":
    main()
