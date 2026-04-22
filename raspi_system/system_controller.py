# Coordinates all modules and threads
# class SystemController

# Each class above can be run in its own thread, coordinated by SystemController. Use Queue for inter-thread communication:
# MotionDetectionHandler → triggers WakeWordDetector
# WakeWordDetector → triggers SpeechToTextProcessor
# SpeechToTextProcessor → sends text to NLPParser
# NLPParser → queries DatabaseManager
# DatabaseManager → sends location to BLECommunicationManager

# system_controler.py
# import socket
import asyncio
import concurrent.futures
import json
import os
import queue
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading

# import tkinter as tk
import time

# from tkinter import scrolledtext
import pyttsx3
from bleak import BleakClient, BleakScanner

try:
    from raspi_system.arduino_config import get_all_rack_numbers, get_arduino_config
    from raspi_system.keyword_matcher import build_keyword_matcher
    from raspi_system.motion_handler import motion_listener
    from raspi_system.nlp_parser import find_keyword
except ModuleNotFoundError:
    # Fallback for direct execution from raspi_system directory on Pi.
    from arduino_config import get_all_rack_numbers, get_arduino_config
    from keyword_matcher import build_keyword_matcher
    from motion_handler import motion_listener
    from nlp_parser import find_keyword

# from bleak import BleakClient
# DEVICE_ADDRESS = "C6:10:17:BD:9F:7F"  # your Nordic_LBS MAC
# LBS_LED_CHAR_UUID = "00001525-1212-efde-1523-785feabcd123"
# from app import socketio
try:
    from raspi_system.rack_database_adapter import (
        DB_PATH,
        load_database_from_sqlite,
        mark_item_as_most_recent,
    )
    from raspi_system.speech_to_text import listen_and_transcribe
    from raspi_system.vosk_wake_word import wake_word_listener
except ModuleNotFoundError:
    from rack_database_adapter import (
        DB_PATH,
        load_database_from_sqlite,
        mark_item_as_most_recent,
    )
    from speech_to_text import listen_and_transcribe
    from vosk_wake_word import wake_word_listener

# from socketio_instance import socketio


def _ble_write_with_response():
    """Use write-with-response by default for reliability."""
    raw = str(os.environ.get("HRS_BLE_WRITE_WITH_RESPONSE", "1")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def _write_gatt_with_fallback(client, char_uuid, payload):
    """Write to BLE characteristic and retry with opposite response mode on failure."""
    preferred = _ble_write_with_response()
    try:
        await client.write_gatt_char(char_uuid, payload, response=preferred)
        return
    except Exception as first_error:
        try:
            await client.write_gatt_char(char_uuid, payload, response=not preferred)
            print(
                f"⚠️ BLE write fallback succeeded (response={not preferred}) after: {first_error}"
            )
            return
        except Exception:
            raise first_error


def _timestamp_ms(epoch_seconds=None):
    """Return local wall-clock timestamp with millisecond precision."""
    t = time.time() if epoch_seconds is None else float(epoch_seconds)
    base = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    ms = int((t % 1) * 1000)
    return f"{base}.{ms:03d}"


def _safe_db_mtime():
    """Best-effort DB mtime lookup for live matcher refresh."""
    try:
        return os.path.getmtime(DB_PATH)
    except Exception:
        return None


def build_arduino_payload(
    slot_number=None, slot_numbers=None, timed_flag=False, start_flag=False
):
    """Build the 11-byte payload expected by the Arduino sketch.

    Layout:
        - bits 0-79: index bits 1-80
        - bit 80: timed flag (Arduino auto-off timer when set)
        - bit 81: start flag (Arduino checks this as data[10] == 2)

    Args:
        slot_number: single index to activate (1-80), optional
        slot_numbers: iterable of indexes to activate (1-80), optional
        timed_flag: if True, set bit 80 (timed auto-off mode)
        start_flag: if True, set bit 81 (start signal)

    Returns 11 bytes in little-endian format.
    """
    bit_pattern = 0

    slots = []
    if slot_numbers is not None:
        slots.extend(slot_numbers)
    if slot_number is not None:
        slots.append(slot_number)

    for slot in slots:
        try:
            slot_i = int(slot)
        except (TypeError, ValueError):
            continue
        if 1 <= slot_i <= 80:
            bit_pattern |= 1 << (slot_i - 1)

    if timed_flag:
        bit_pattern |= 1 << 80

    if start_flag:
        bit_pattern |= 1 << 81

    return bit_pattern.to_bytes(11, byteorder="little")


def get_rack_cols(rack_number):
    """Get the number of columns configured for a rack (defaults to 20)."""
    try:
        try:
            from raspi_system.rack_database_adapter import get_conn
        except ModuleNotFoundError:
            from rack_database_adapter import get_conn

        conn = get_conn()
        rack = conn.execute(
            "SELECT cols FROM racks WHERE id=?", (rack_number,)
        ).fetchone()
        conn.close()
        if rack and rack["cols"]:
            return int(rack["cols"])
    except Exception as e:
        print(f"Error fetching rack cols for rack {rack_number}: {e}")
    return 20


def slot_id_to_ble_slot(slot_id, rack_number):
    """Resolve a global rack_slots.id to rack-local BLE slot index (1-80)."""
    try:
        slot_i = int(slot_id)
        rack_i = int(rack_number)
    except (TypeError, ValueError):
        return None

    try:
        try:
            from raspi_system.rack_database_adapter import get_conn
        except ModuleNotFoundError:
            from rack_database_adapter import get_conn

        conn = get_conn()
        row = conn.execute(
            "SELECT row, col FROM rack_slots WHERE id=? AND rack_id=?",
            (slot_i, rack_i),
        ).fetchone()
        conn.close()
        if row is None:
            return None

        row_i = int(row["row"])
        col_i = int(row["col"])
        cols = get_rack_cols(rack_i)
        slot = (row_i * cols) + col_i + 1
        if 1 <= slot <= 80:
            return slot
    except Exception:
        return None

    return None


def entry_to_ble_slot(entry):
    """Convert DB entry fields to rack-local BLE slot index (1-80)."""
    try:
        row = entry.get("row")
        col = entry.get("col")
        rack = entry.get("rack")
        if row is not None and col is not None and rack is not None:
            row_i = int(row)
            col_i = int(col)
            cols = get_rack_cols(int(rack))
            slot = (row_i * cols) + col_i + 1
            if 1 <= slot <= 80:
                return slot
    except Exception:
        pass

    # Primary fallback for rack.db where `location` is global rack_slots.id.
    try:
        rack = entry.get("rack")
        loc = entry.get("location")
        slot = slot_id_to_ble_slot(loc, rack)
        if slot is not None:
            return slot
    except Exception:
        pass

    # Fallback for legacy datasets where location may already be rack-local.
    try:
        loc = int(entry.get("location"))
        if 1 <= loc <= 80:
            return loc
    except Exception:
        pass

    return None


def get_rack_config(rack_number):
    """Get rack configuration (4x4 or 6x4) for a specific rack."""
    try:
        try:
            from raspi_system.rack_database_adapter import get_conn
        except ModuleNotFoundError:
            from rack_database_adapter import get_conn

        conn = get_conn()
        has_racks_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='racks' LIMIT 1"
        ).fetchone()
        if not has_racks_table:
            conn.close()
            return "4x4"

        rack = conn.execute(
            "SELECT cols FROM racks WHERE id=?", (rack_number,)
        ).fetchone()
        conn.close()
        if rack:
            cols = rack["cols"]
            return "6x4" if cols == 6 else "4x4"
    except Exception as e:
        print(f"Error fetching rack config: {e}")
    return "4x4"  # default to 4x4


def push_rack_status(rack_number, status):
    """Push rack BLE status to Flask UI backend (best-effort)."""
    if status not in ("connected", "disconnected", "reconnecting"):
        return

    base_url = os.environ.get("HRS_STATUS_API_BASE", "http://127.0.0.1:5000")
    url = f"{base_url.rstrip('/')}/api/rack-status"
    payload = json.dumps({"rack_id": rack_number, "status": status}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status >= 400:
                print(
                    f"BLE Worker (Rack {rack_number}): Status push failed with HTTP {resp.status}"
                )
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"BLE Worker (Rack {rack_number}): Status push skipped ({e})")
    except Exception as e:
        print(f"BLE Worker (Rack {rack_number}): Status push error: {e}")


engine = pyttsx3.init()
voice_trigger = threading.Event()
pause_event = threading.Event()
shutdown_flag = threading.Event()
wake_stream_active = threading.Event()
wake_stream_active.set()
wake_stream_released = threading.Event()
wake_stream_released.set()

recent_mark_queue = queue.Queue(maxsize=64)

# Active BLE connection metadata for immediate (non-queued) sends.
active_ble_lock = threading.Lock()
active_ble_connections = {}

manual_connect_lock = threading.Lock()
manual_connect_state = {
    "requests": {},
}
manual_reconnect_requests = set()


def get_trigger_mode():
    """Return trigger mode: 'always_on' (default) or 'triggered'."""
    raw = str(os.environ.get("HRS_TRIGGER_MODE", "always_on")).strip().lower()
    if raw in {"triggered", "wake", "wake_motion", "gated"}:
        return "triggered"
    return "always_on"


def use_triggered_voice_session():
    return get_trigger_mode() == "triggered"


def queue_recent_match_update(term):
    """Queue non-blocking DB updates for latest matched term."""
    normalized = str(term or "").strip()
    if not normalized:
        return
    try:
        recent_mark_queue.put_nowait(normalized)
    except queue.Full:
        # Drop oldest pending update in favor of the newest term.
        try:
            recent_mark_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            recent_mark_queue.put_nowait(normalized)
        except queue.Full:
            pass


def recent_match_update_worker():
    """Persist recent-match marker off the voice critical path."""
    while not shutdown_flag.is_set():
        try:
            pending = recent_mark_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        latest = pending
        # Coalesce bursts; only newest term needs to win.
        while True:
            try:
                latest = recent_mark_queue.get_nowait()
            except queue.Empty:
                break

        try:
            mark_item_as_most_recent(latest)
        except Exception as e:
            print(f"Warning: failed to persist recent match '{latest}': {e}")


def _set_active_ble_connection(rack_number, client, char_uuid, loop, device_name):
    with active_ble_lock:
        active_ble_connections[rack_number] = {
            "rack_number": rack_number,
            "client": client,
            "char_uuid": char_uuid,
            "loop": loop,
            "device_name": device_name,
        }


def _clear_active_ble_connection(rack_number):
    with active_ble_lock:
        active_ble_connections.pop(rack_number, None)


def _get_active_ble_connection(rack_number):
    with active_ble_lock:
        conn = active_ble_connections.get(rack_number)
        return dict(conn) if conn else None


def _request_manual_reconnect(rack_number):
    with manual_connect_lock:
        manual_reconnect_requests.add(rack_number)


def _consume_manual_reconnect(rack_number):
    with manual_connect_lock:
        if rack_number in manual_reconnect_requests:
            manual_reconnect_requests.discard(rack_number)
            return True
        return False


def _complete_manual_connect(rack_number, ok, message):
    with manual_connect_lock:
        request = manual_connect_state["requests"].get(rack_number)
        if not request:
            return
        request["result"] = {
            "ok": bool(ok),
            "message": message,
            "rack_id": rack_number,
        }
        evt = request.get("event")
        if evt:
            evt.set()


def request_manual_connect(rack_number, timeout=20):
    """Request BLE worker to connect to a specific rack and wait for result."""
    if rack_number not in get_all_rack_numbers():
        return {
            "ok": False,
            "message": f"Rack {rack_number} is not configured",
            "rack_id": rack_number,
        }

    active_conn = _get_active_ble_connection(rack_number)
    if active_conn and active_conn.get("client") and active_conn["client"].is_connected:
        return {
            "ok": True,
            "message": f"Rack {rack_number} is already connected",
            "rack_id": rack_number,
        }

    evt = threading.Event()
    with manual_connect_lock:
        manual_connect_state["requests"][rack_number] = {
            "event": evt,
            "result": None,
        }

    _request_manual_reconnect(rack_number)
    push_rack_status(rack_number, "reconnecting")

    if not evt.wait(timeout=timeout):
        with manual_connect_lock:
            request = manual_connect_state["requests"].pop(rack_number, None)
            if request and request.get("result"):
                return request["result"]
        return {
            "ok": False,
            "message": f"Timeout connecting to rack {rack_number}",
            "rack_id": rack_number,
        }

    with manual_connect_lock:
        request = manual_connect_state["requests"].pop(rack_number, None)
        result = request.get("result") if request else None
    return result or {
        "ok": False,
        "message": f"Failed connecting to rack {rack_number}",
        "rack_id": rack_number,
    }


class ManualConnectHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # The client disconnected before the response could be written.
            # This is normal for short-lived HTTP clients, so suppress it.
            return

    def do_POST(self):
        path = self.path.rstrip("/")

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send_json(400, {"ok": False, "error": "Invalid request payload"})
            return

        if path == "/manual-connect":
            try:
                rack_number = int(data.get("rack_id"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "Invalid rack_id"})
                return

            result = request_manual_connect(rack_number, timeout=20)
            status_code = 200 if result.get("ok") else 500
            self._send_json(status_code, result)
            return

        if path == "/highlight-slots":
            try:
                rack_number = int(data.get("rack_id"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "Invalid rack_id"})
                return

            clear_requested = bool(data.get("clear", False))

            if clear_requested:
                ok = send_ble_command_now(rack_number, "clear_slots")
                if ok:
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "rack_id": rack_number,
                            "slot_ids": [],
                            "clear": True,
                        },
                    )
                else:
                    self._send_json(
                        500,
                        {
                            "ok": False,
                            "rack_id": rack_number,
                            "error": "Failed to send BLE clear command",
                        },
                    )
                return

            raw_slots = data.get("slot_ids") or []
            if not isinstance(raw_slots, list):
                self._send_json(400, {"ok": False, "error": "slot_ids must be a list"})
                return

            slot_numbers = []
            for s in raw_slots:
                try:
                    si = int(s)
                except Exception:
                    continue
                if 1 <= si <= 80:
                    slot_numbers.append(si)

            # Preserve order while removing duplicates.
            slot_numbers = list(dict.fromkeys(slot_numbers))

            if not slot_numbers:
                self._send_json(400, {"ok": False, "error": "No valid slot_ids"})
                return

            ok = send_ble_command_now(
                rack_number,
                "highlight_slots",
                slot_numbers=slot_numbers,
            )

            if ok:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "rack_id": rack_number,
                        "slot_ids": slot_numbers,
                    },
                )
            else:
                self._send_json(
                    500,
                    {
                        "ok": False,
                        "rack_id": rack_number,
                        "error": "Failed to send BLE highlight command",
                    },
                )
            return

        self._send_json(404, {"ok": False, "error": "Not found"})

    def log_message(self, format, *args):
        return


def start_manual_connect_server():
    host = os.environ.get("HRS_BLE_CONTROL_HOST", "0.0.0.0")
    port = int(os.environ.get("HRS_BLE_CONTROL_PORT", "8765"))
    server = HTTPServer((host, port), ManualConnectHandler)

    def _serve():
        print(f"BLE Control API listening on {host}:{port}")
        server.serve_forever()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    return server


async def _write_payload_now(client, char_uuid, payload):
    if not client or not client.is_connected:
        raise RuntimeError("Arduino is not connected")
    await _write_gatt_with_fallback(client, char_uuid, payload)


async def _send_payload_direct(rack_number, payload):
    """Best-effort one-off BLE send when the rack is not already connected."""
    config = get_arduino_config(rack_number)
    if not config:
        print(f"❌ BLE send failed for Rack {rack_number}: no Arduino config")
        return False

    address = config["address"]
    char_uuid = config["char_uuid"]

    try:
        async with BleakClient(address) as client:
            await _write_gatt_with_fallback(client, char_uuid, payload)
        return True
    except Exception as e:
        print(f"❌ Direct BLE send failed for Rack {rack_number}: {e}")
        return False


def send_ble_commands_parallel(commands, max_workers=4, reference_start=None):
    """Send BLE commands concurrently; commands are (rack, keyword, slots)."""
    normalized = []
    for command in commands or []:
        if not isinstance(command, (tuple, list)) or len(command) < 3:
            continue
        rack_num, keyword, slot_numbers = command[0], command[1], command[2]
        normalized.append((rack_num, keyword, slot_numbers))

    if not normalized:
        return []

    workers = max(1, min(int(max_workers), len(normalized)))
    results = []
    ref_start = float(reference_start) if reference_start is not None else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_cmd = {
            executor.submit(
                send_ble_command_now,
                rack_num,
                keyword,
                None,
                slot_numbers,
            ): (rack_num, keyword, slot_numbers, time.perf_counter())
            for rack_num, keyword, slot_numbers in normalized
        }
        for future in concurrent.futures.as_completed(future_to_cmd):
            rack_num, keyword, slot_numbers, submit_perf = future_to_cmd[future]
            try:
                ok = bool(future.result())
            except Exception:
                ok = False
            done_perf = time.perf_counter()
            send_latency_ms = (done_perf - submit_perf) * 1000
            heard_to_done_ms = (
                ((done_perf - ref_start) * 1000) if ref_start is not None else None
            )
            results.append(
                (
                    rack_num,
                    keyword,
                    slot_numbers,
                    ok,
                    send_latency_ms,
                    heard_to_done_ms,
                )
            )

    return results


def send_ble_command_now(rack_number, keyword, slot_number=None, slot_numbers=None):
    """Send BLE command immediately. No queueing; fails if rack not connected."""
    conn = _get_active_ble_connection(rack_number)

    if keyword == "wake_word_start":
        payload = build_arduino_payload(start_flag=True)
        message_label = "wake word"
    elif keyword == "clear_slots":
        payload = build_arduino_payload(slot_numbers=[])
        message_label = "clear"
    else:
        slots_to_send = []

        if slot_numbers is not None:
            try:
                for s in slot_numbers:
                    si = int(s)
                    if 1 <= si <= 80:
                        slots_to_send.append(si)
            except Exception:
                pass

        if slot_number is not None:
            try:
                si = int(slot_number)
                if 1 <= si <= 80:
                    slots_to_send.append(si)
            except (TypeError, ValueError):
                pass

        slots_to_send = sorted(set(slots_to_send))
        if not slots_to_send:
            print(f"❌ BLE send failed for Rack {rack_number}: no valid slots (1-80)")
            return False
        # Voice keyword lookups should be timed; UI/edit highlights remain persistent.
        timed_mode = keyword not in ("highlight_slots",)
        payload = build_arduino_payload(
            slot_numbers=slots_to_send,
            timed_flag=timed_mode,
        )
        message_label = f"slots {','.join(str(s) for s in slots_to_send)}"

    if conn and conn.get("client") and conn.get("loop") and conn.get("char_uuid"):
        try:
            write_start = time.time()
            future = asyncio.run_coroutine_threadsafe(
                _write_payload_now(conn["client"], conn["char_uuid"], payload),
                conn["loop"],
            )
            future.result(timeout=5)
            write_time = (time.time() - write_start) * 1000
            print(
                f"✅ BLE {message_label} command sent to Rack {rack_number}: {payload.hex()} (write took {write_time:.1f}ms)"
            )
            return True
        except Exception as e:
            print(
                f"⚠️ BLE send via active connection failed for Rack {rack_number}: {e}"
            )
    else:
        print(
            f"⚠️ Rack {rack_number} not currently active; trying direct BLE send for {message_label}"
        )

    if asyncio.run(_send_payload_direct(rack_number, payload)):
        print(
            f"✅ BLE {message_label} command sent directly to Rack {rack_number}: {payload.hex()}"
        )
        return True

    print(f"❌ BLE send failed for Rack {rack_number}: not queued")
    return False


class BLEManager:
    """Manages BLE connection to a single Arduino."""

    def __init__(self, rack_number, char_uuid):
        self.rack_number = rack_number
        self.char_uuid = char_uuid
        self.loop = None
        self.thread = None
        self.client = None
        self.connected_event = threading.Event()
        self._lock = asyncio.Lock()  # prevents overlapping writes

    def start(self):
        self.loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=_run_loop, daemon=True)
        self.thread.start()

        # Start the persistent connection loop
        asyncio.run_coroutine_threadsafe(self._connection_loop(), self.loop)

    async def _connection_loop(self):
        """Persistent connection manager that reconnects safely."""
        config = get_arduino_config(self.rack_number)
        if not config:
            print(f"BLEManager: No config found for rack {self.rack_number}")
            return

        arduino_address = config["address"]
        arduino_name = config["name"]

        while True:
            try:
                if not self.client or not self.client.is_connected:
                    print(
                        f"BLEManager (Rack {self.rack_number}): attempting connection to {arduino_name} ({arduino_address})"
                    )
                    self.client = BleakClient(arduino_address)

                    try:
                        await self.client.connect()
                        print(
                            f"BLEManager (Rack {self.rack_number}): ✅ Connected to {arduino_name}"
                        )
                        self.connected_event.set()

                        # Allow BlueZ to stabilize
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(
                            f"BLEManager (Rack {self.rack_number}): connection failed: {e}"
                        )
                        await asyncio.sleep(2)
                        continue

                # Stay connected until it drops
                while self.client.is_connected:
                    await asyncio.sleep(0.5)

                print(
                    f"BLEManager (Rack {self.rack_number}): connection lost, retrying..."
                )
                self.connected_event.clear()

            except Exception as e:
                print(
                    f"BLEManager (Rack {self.rack_number}): connection loop error: {e}"
                )

            await asyncio.sleep(1)

    def send_signal(self, data: bytes = b"1"):
        """Thread-safe write entry point."""
        if not self.loop:
            print(f"BLEManager (Rack {self.rack_number}): loop not started")
            return

        fut = asyncio.run_coroutine_threadsafe(self._write(data), self.loop)
        try:
            fut.result(timeout=5)
        except Exception as e:
            print(f"BLEManager (Rack {self.rack_number}): write timeout/error: {e}")

    async def _write(self, data: bytes):
        """Safe BLE write that never races with reconnect."""
        async with self._lock:
            try:
                if not self.client or not self.client.is_connected:
                    print(
                        f"BLEManager (Rack {self.rack_number}): not connected, cannot write"
                    )
                    return

                await self.client.write_gatt_char(self.char_uuid, data, response=False)
                print(f"BLEManager (Rack {self.rack_number}): ✅ Signal sent")

            except Exception as e:
                print(f"BLEManager (Rack {self.rack_number}): write failed: {e}")


async def send_alert_to_rack(rack_number):
    """Scan for Arduino and send alert signal to a specific rack."""
    config = get_arduino_config(rack_number)
    if not config:
        print(f"No Arduino config found for rack {rack_number}")
        return

    arduino_name = config["name"]
    arduino_address = config["address"]
    char_uuid = config["char_uuid"]

    print(f"Scanning for {arduino_name} (Rack {rack_number})...")
    try:
        devices = await BleakScanner.discover()
        target = None

        # Try to find by name first
        for d in devices:
            if d.name and arduino_name in d.name:
                target = d
                print(f"Found {arduino_name} by name at {d.address}")
                break

        # Fallback to address
        if not target:
            for d in devices:
                if d.address == arduino_address:
                    target = d
                    print(f"Found {arduino_name} by address")
                    break

        if not target:
            print(f"Arduino {arduino_name} not found for rack {rack_number}")
            return

        async with BleakClient(target.address) as client:
            print(f"Connected to {arduino_name}. Sending alert...")
            await client.write_gatt_char(char_uuid, b"1")
            print(f"Alert sent to rack {rack_number}")
    except Exception as e:
        print(f"Error sending alert to rack {rack_number}: {e}")


# Call when keyword is found to a specific rack:
# asyncio.run(send_alert_to_rack(rack_number))


def ble_worker_thread(start_rack_number=1, fixed_rack_number=None, startup_delay=0):
    """BLE worker for persistent rack connectivity.

    In single-rack mode (fixed_rack_number set), this worker keeps one rack
    connected and continuously reconnects that same rack on drops.
    In round-robin mode, it can cycle through configured racks.

    Args:
        start_rack_number: Rack number to try first.
        fixed_rack_number: If set, pins this worker to one rack.
        startup_delay: Seconds to wait before the first connect attempt.
    """
    if fixed_rack_number is not None:
        rack_numbers = [fixed_rack_number]
    else:
        rack_numbers = get_all_rack_numbers()
    if not rack_numbers:
        print("BLE Worker: No rack configs found")
        return

    if start_rack_number in rack_numbers:
        scan_index = rack_numbers.index(start_rack_number)
    else:
        scan_index = 0

    mode = "single-rack" if len(rack_numbers) == 1 else "round-robin"
    print(f"BLE Worker ({mode}): Starting with rack {rack_numbers[scan_index]}...")

    if startup_delay > 0:
        print(
            f"BLE Worker ({mode}): delaying initial connect by {startup_delay:.1f}s to reduce BlueZ contention"
        )
        time.sleep(startup_delay)

    status_interval = 15  # seconds between status heartbeats while connected

    async def find_and_connect(rack_number):
        """Scan for a specific rack Arduino and connect."""
        config = get_arduino_config(rack_number)
        if not config:
            print(f"BLE Worker (Rack {rack_number}): No config found")
            return None, None

        arduino_name = config["name"]
        arduino_address = config["address"]
        # Try direct MAC connections a few times first. This is more stable than
        # scanning on BlueZ, especially when several peripherals are advertising.
        for attempt in range(1, 4):
            print(
                f"BLE Worker (Rack {rack_number}): Direct connect attempt {attempt}/3 to {arduino_name} ({arduino_address})..."
            )
            try:
                direct_client = BleakClient(arduino_address)
                await direct_client.connect(timeout=15.0)
                print(
                    f"BLE Worker (Rack {rack_number}): ✅ Connected directly to {arduino_name} ({arduino_address})"
                )
                push_rack_status(rack_number, "connected")
                await asyncio.sleep(0.5)
                return direct_client, config
            except Exception as direct_error:
                print(
                    f"BLE Worker (Rack {rack_number}): Direct connect failed on attempt {attempt}: {direct_error}"
                )
                await asyncio.sleep(1.5 * attempt)

        print(
            f"BLE Worker (Rack {rack_number}): Direct connect exhausted, falling back to scan..."
        )

        try:
            print(f"BLE Worker (Rack {rack_number}): Scanning for '{arduino_name}'...")
            devices = await BleakScanner.discover(timeout=10.0)
            target = None

            # First try to find by name
            for device in devices:
                if device.name and arduino_name in device.name:
                    target = device
                    print(
                        f"BLE Worker (Rack {rack_number}): Found Arduino by name at {device.address}"
                    )
                    break

            # Fallback: try to find by known address
            if not target:
                print(
                    f"BLE Worker (Rack {rack_number}): Name not found, trying address {arduino_address}"
                )
                for device in devices:
                    if device.address == arduino_address:
                        target = device
                        print(
                            f"BLE Worker (Rack {rack_number}): Found Arduino by address"
                        )
                        break

            if not target:
                print(
                    f"BLE Worker (Rack {rack_number}): Arduino not found in scan (scanned {len(devices)} devices)"
                )
                return None, None

            # Small delay to let BlueZ stabilize after scan
            await asyncio.sleep(0.5)

            # Use the device object directly for better connection reliability
            client = BleakClient(target)
            await client.connect(timeout=15.0)
            print(
                f"BLE Worker (Rack {rack_number}): ✅ Connected to {target.name or target.address}"
            )
            push_rack_status(rack_number, "connected")

            # Allow connection to fully stabilize
            await asyncio.sleep(1.0)
            return client, config

        except Exception as e:
            print(f"BLE Worker (Rack {rack_number}): Connection error: {e}")
            return None, None

    async def maintain_connection(client, rack_number, fallback_device_name):
        """Keep an active BLE link alive and emit periodic status logs.

        Returns:
            "manual_reconnect" when current rack is explicitly reconnected,
            "connection_lost" on disconnect/errors,
            "shutdown" when system is shutting down.
        """
        last_status_log = time.time()

        while not shutdown_flag.is_set():
            try:
                # Check if still connected
                if not client.is_connected:
                    print(f"BLE Worker (Rack {rack_number}): ❌ Connection lost")
                    push_rack_status(rack_number, "disconnected")
                    return "connection_lost"

                current_time = time.time()
                if current_time - last_status_log >= status_interval:
                    try:
                        device_name = client.device.name or client.device.address
                    except Exception:
                        device_name = fallback_device_name
                    print(
                        f"BLE Worker (Rack {rack_number}): 🔵 Connected and waiting for commands ({device_name})"
                    )
                    last_status_log = current_time

                if _consume_manual_reconnect(rack_number):
                    print(
                        f"BLE Worker (Rack {rack_number}): Manual reconnect requested, reconnecting..."
                    )
                    return "manual_reconnect"
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"BLE Worker (Rack {rack_number}): Connection loop error: {e}")
                return "connection_lost"

        return "shutdown"

    async def run_ble_worker():
        """Main BLE worker loop with reconnection."""
        nonlocal scan_index
        while not shutdown_flag.is_set():
            rack_number = rack_numbers[scan_index]
            config = get_arduino_config(rack_number)
            if not config:
                print(f"BLE Worker (Rack {rack_number}): Missing config, skipping")
                scan_index = (scan_index + 1) % len(rack_numbers)
                await asyncio.sleep(1)
                continue

            arduino_name = config["name"]
            arduino_address = config["address"]
            char_uuid = config["char_uuid"]
            print(
                f"BLE Worker (Rack {rack_number}): status=connecting, attempting {arduino_name} ({arduino_address})"
            )
            push_rack_status(rack_number, "reconnecting")
            client, _ = await find_and_connect(rack_number)
            disconnect_reason = "connection_lost"

            if client:
                _complete_manual_connect(
                    rack_number,
                    True,
                    f"Connected to rack {rack_number}",
                )
                # Stay connected and process events
                try:
                    _set_active_ble_connection(
                        rack_number,
                        client,
                        char_uuid,
                        asyncio.get_running_loop(),
                        arduino_name,
                    )
                    disconnect_reason = await maintain_connection(
                        client, rack_number, arduino_name
                    )
                except Exception as e:
                    print(f"BLE Worker (Rack {rack_number}): Event loop error: {e}")
                    disconnect_reason = "connection_lost"
                finally:
                    _clear_active_ble_connection(rack_number)
                    try:
                        if client.is_connected:
                            await client.disconnect()
                            print(f"BLE Worker (Rack {rack_number}): Disconnected")
                        push_rack_status(rack_number, "disconnected")
                    except Exception:
                        pass
            else:
                _complete_manual_connect(
                    rack_number,
                    False,
                    f"Failed connecting to rack {rack_number}",
                )

            # Reconnect strategy
            if not shutdown_flag.is_set():
                if disconnect_reason == "manual_reconnect":
                    print(
                        f"BLE Worker (Rack {rack_number}): status=manual-reconnect, reconnecting now..."
                    )
                    push_rack_status(rack_number, "reconnecting")
                    await asyncio.sleep(0.2)
                    continue

                if disconnect_reason == "connection_lost" and client:
                    # If a connected rack drops, prioritize reconnecting the same rack first.
                    print(
                        f"BLE Worker (Rack {rack_number}): status=retrying, reconnecting same rack in 1 second..."
                    )
                    push_rack_status(rack_number, "reconnecting")
                    await asyncio.sleep(1)
                    continue

                if len(rack_numbers) == 1:
                    print(
                        f"BLE Worker (Rack {rack_number}): status=retrying, reconnecting in 1 second..."
                    )
                    push_rack_status(rack_number, "reconnecting")
                    await asyncio.sleep(1)
                else:
                    print(
                        f"BLE Worker (Rack {rack_number}): status=retrying, switching to next rack in 3 seconds..."
                    )
                    push_rack_status(rack_number, "reconnecting")
                    scan_index = (scan_index + 1) % len(rack_numbers)
                    await asyncio.sleep(3)

        print(f"BLE Worker (Rack {rack_number}): Shutting down")

    # Run the async worker
    current_rack = rack_numbers[scan_index]
    try:
        asyncio.run(run_ble_worker())
    except Exception as e:
        print(f"BLE Worker (Rack {current_rack}): Fatal error: {e}")


# async def light_led_for_seconds(seconds=5):
#     client = BleakClient(DEVICE_ADDRESS)
#     try:
#         await client.connect()
#         print("Connected to Nordic board.")
#         # Turn LED ON
#         await client.write_gatt_char(LBS_LED_CHAR_UUID, bytearray([0x01]), response=True)
#         print("LED ON")
#         await asyncio.sleep(seconds)
#         # Turn LED OFF
#         await client.write_gatt_char(LBS_LED_CHAR_UUID, bytearray([0x00]), response=True)
#         print("LED OFF")
#     finally:
#         try:
#             await client.disconnect()
#         except Exception:
#             pass


def voice_thread():
    mode = get_trigger_mode()
    if mode == "triggered":
        print(
            "Voice thread started in TRIGGERED mode. Waiting for wake/motion trigger..."
        )
    else:
        print("Voice thread started in ALWAYS_ON mode. Listening immediately...")
    # try:
    #     db = load_database_from_sqlite()
    #     print("Database loaded in voice thread.")
    # except Exception as e:
    #     print(f"Error loading database: {e}")

    INACTIVITY_TIMEOUT = None  # shared for wake-word and motion-triggered sessions
    dedupe_window_sec = float(os.environ.get("HRS_COMMAND_DEDUPE_WINDOW_SEC", "1.2"))
    last_dispatched_phrase = ""
    last_dispatch_time = 0.0

    while not shutdown_flag.is_set():
        triggered_session = use_triggered_voice_session()
        if triggered_session:
            if not voice_trigger.wait(timeout=1):
                continue
            voice_trigger.clear()
            pause_event.set()

            # Wait for wake stream to close instead of using a fixed sleep.
            if not wake_stream_released.wait(timeout=0.4):
                print("⚠️  Wake stream release wait timed out; continuing")
        else:
            pause_event.clear()

        # Wake-word BLE notification is sent by wake_word_listener.
        # Avoid double-send here.
        try:
            last_keyword_time = time.time()
            last_status_print = time.time()
            db_refresh_interval_sec = float(
                os.environ.get("HRS_DB_REFRESH_INTERVAL_SEC", "0.5")
            )
            db = load_database_from_sqlite()
            matcher = build_keyword_matcher(db)
            cached_db_mtime = _safe_db_mtime()
            next_db_refresh_check = time.time() + db_refresh_interval_sec
            configured_racks = set(get_all_rack_numbers())
            print("⏱️  Listening for keywords...")

            for phrase_payload in listen_and_transcribe(shutdown_flag):
                if INACTIVITY_TIMEOUT is not None:
                    current_time = time.time()
                    elapsed = current_time - last_keyword_time

                    # Print periodic status (every 10 seconds)
                    if current_time - last_status_print >= 10:
                        remaining = max(0, INACTIVITY_TIMEOUT - elapsed)
                        print(
                            f"⏱️  Still listening... ({remaining:.0f}s until no-keyword timeout)"
                        )
                        last_status_print = current_time

                    if elapsed > INACTIVITY_TIMEOUT:
                        print(
                            f"\n⏰ Timeout: No keyword matched for {INACTIVITY_TIMEOUT} seconds"
                        )
                        print("🔄 Resetting to wake word/motion detection mode...")
                        break

                phrase = phrase_payload
                stt_first_partial_ts = None
                stt_final_ts = None
                stt_endpoint_ms = None
                stt_early_fire = False
                if isinstance(phrase_payload, dict):
                    phrase = phrase_payload.get("text")
                    stt_first_partial_ts = phrase_payload.get("stt_first_partial_ts")
                    stt_final_ts = phrase_payload.get("stt_final_ts")
                    stt_endpoint_ms = phrase_payload.get("stt_endpoint_ms")
                    stt_early_fire = bool(phrase_payload.get("stt_early_fire", False))

                if phrase is None or not isinstance(phrase, str):
                    continue

                if shutdown_flag.is_set():
                    break

                now_loop = time.time()
                if now_loop >= next_db_refresh_check:
                    next_db_refresh_check = now_loop + db_refresh_interval_sec
                    live_mtime = _safe_db_mtime()
                    if live_mtime is not None and live_mtime != cached_db_mtime:
                        try:
                            db = load_database_from_sqlite()
                            matcher = build_keyword_matcher(db)
                            cached_db_mtime = live_mtime
                            print(
                                "🔄 Database changed, matcher refreshed (live update applied)"
                            )
                        except Exception as refresh_error:
                            print(f"⚠️  Live DB refresh failed: {refresh_error}")

                normalized_phrase = " ".join(str(phrase).lower().split())
                now_for_dedupe = time.time()
                if (
                    normalized_phrase
                    and normalized_phrase == last_dispatched_phrase
                    and (now_for_dedupe - last_dispatch_time) <= dedupe_window_sec
                ):
                    print(
                        f"⏭️  Duplicate phrase suppressed: '{phrase}' within {dedupe_window_sec:.1f}s"
                    )
                    continue

                heard_wall = stt_final_ts if stt_final_ts is not None else time.time()
                heard_perf = time.perf_counter()
                print(f"Heard [{_timestamp_ms(heard_wall)}]: {phrase}")
                if stt_early_fire:
                    print("⚡ Early partial dispatch used before final endpoint")
                if stt_endpoint_ms is not None:
                    print(
                        f"⏱️  STT endpoint latency (first partial->final): {stt_endpoint_ms:.1f}ms"
                    )
                result = find_keyword(phrase, db, matcher=matcher, mark_recent=False)
                if not result:
                    live_mtime = _safe_db_mtime()
                    if live_mtime is not None and live_mtime != cached_db_mtime:
                        try:
                            db = load_database_from_sqlite()
                            matcher = build_keyword_matcher(db)
                            cached_db_mtime = live_mtime
                            print(
                                "🔄 Database changed since last check, retrying match with refreshed data"
                            )
                            result = find_keyword(
                                phrase,
                                db,
                                matcher=matcher,
                                mark_recent=False,
                            )
                        except Exception as retry_refresh_error:
                            print(
                                f"⚠️  On-demand DB refresh failed: {retry_refresh_error}"
                            )
                print(f"Keyword match result: {result}")

                if result:
                    # Keep the session alive only when a keyword is matched.
                    last_keyword_time = time.time()
                    last_status_print = last_keyword_time
                    match_latency_ms = (time.perf_counter() - heard_perf) * 1000
                    print("⏱️  Keyword matched, no-keyword timeout reset")
                    print(f"⏱️  Latency: heard->keyword_match {match_latency_ms:.1f}ms")

                    keyword = result.get("item")
                    matched_term = result.get("matched_term", keyword)
                    queue_recent_match_update(matched_term)
                    matches = result.get("matches") or []
                    match_type = result.get("match_type", "exact")
                    confidence = result.get("confidence", 0.0)
                    print(
                        f"🔎 Match details: type={match_type}, confidence={confidence:.3f}, term='{matched_term}'"
                    )

                    # Prefer the matcher-provided rows so tag terms can fan out to
                    # every matching item. Fall back to the matched item if needed.
                    if not matches:
                        item_id = result.get("id")
                        if item_id is not None:
                            matches = [e for e in db if e.get("id") == item_id]
                        else:
                            matches = [
                                e
                                for e in db
                                if e.get("item", "").lower() == keyword.lower()
                            ]

                    racks = {}
                    if matches:
                        # Aggregate locations by rack for clearer output and BLE payloads.
                        for m in matches:
                            rack = m.get("rack")
                            ble_slot = entry_to_ble_slot(m)
                            if rack is None or ble_slot is None:
                                continue
                            racks.setdefault(rack, []).append(ble_slot)

                        display_term = matched_term or keyword
                        if (
                            len(
                                {
                                    m.get("id")
                                    for m in matches
                                    if m.get("id") is not None
                                }
                            )
                            > 1
                        ):
                            print(f"Found items for tag: '{display_term}'")
                        else:
                            print(f"Found item: '{display_term}'")
                        for rack, locs in sorted(racks.items()):
                            locs_sorted = sorted(set(locs))
                            locs_str = ", ".join(str(loc) for loc in locs_sorted)
                            print(f"  • Rack #{rack} locations: {locs_str}")

                    else:
                        # Single result from NLP; print the reported rack/location
                        print(f"Found item: '{matched_term or keyword}'")
                        print(
                            f"  • Rack #{result.get('rack')} Location {result.get('location')}"
                        )
                    # socketio.emit("highlight_keyword", {"keyword": keyword})

                    # Trigger LED light on Nordic board
                    # asyncio.run(light_led_for_seconds(5))

                    # Send BLE signal(s) with all matched slots per rack.
                    try:
                        command_sent_ok = False
                        if racks:
                            commands = []
                            for rack_num, slot_list in sorted(racks.items()):
                                if rack_num in configured_racks:
                                    commands.append(
                                        (
                                            rack_num,
                                            keyword,
                                            sorted(set(slot_list)),
                                        )
                                    )
                                else:
                                    print(
                                        f"❌ Invalid or unconfigured rack number: {rack_num}"
                                    )

                            for (
                                rack_num,
                                _,
                                slots_sorted,
                                ok,
                                send_latency_ms,
                                heard_to_done_ms,
                            ) in send_ble_commands_parallel(
                                commands,
                                reference_start=heard_perf,
                            ):
                                if ok:
                                    command_sent_ok = True
                                    print(
                                        f"✅ Command sent for Rack {rack_num}, Slots {slots_sorted}"
                                    )
                                else:
                                    print(
                                        f"❌ Command failed for Rack {rack_num}, Slots {slots_sorted} (not queued)"
                                    )
                                print(
                                    f"Attempted BLE send for Rack {rack_num}, Slots {slots_sorted}"
                                )
                                # Per-rack latency line for dashboard/log parsing.
                                total_ms_text = (
                                    f"{heard_to_done_ms:.1f}"
                                    if heard_to_done_ms is not None
                                    else "n/a"
                                )
                                print(
                                    f"⏱️  Latency: heard->ble_sent rack={rack_num} slots={slots_sorted}"
                                    f" total_ms={total_ms_text} send_ms={send_latency_ms:.1f}"
                                )
                        else:
                            rack_num = result.get("rack")
                            slot_num = entry_to_ble_slot(result)
                            if rack_num and rack_num in configured_racks:
                                single_send_start = time.perf_counter()
                                ok = send_ble_command_now(rack_num, keyword, slot_num)
                                send_latency_ms = (
                                    time.perf_counter() - single_send_start
                                ) * 1000
                                heard_to_done_ms = (
                                    time.perf_counter() - heard_perf
                                ) * 1000
                                if ok:
                                    command_sent_ok = True
                                    print(
                                        f"✅ Command sent immediately for Rack {rack_num}, Slot {slot_num}"
                                    )
                                else:
                                    print(
                                        f"❌ Command failed for Rack {rack_num}, Slot {slot_num} (not queued)"
                                    )
                                print(
                                    f"Attempted BLE send for Rack {rack_num}, Slot {slot_num}"
                                )
                                print(
                                    f"⏱️  Latency: heard->ble_sent rack={rack_num} slot={slot_num}"
                                    f" total_ms={heard_to_done_ms:.1f} send_ms={send_latency_ms:.1f}"
                                )
                            else:
                                print(
                                    f"❌ Invalid or unconfigured rack number: {rack_num}"
                                )

                        if command_sent_ok and normalized_phrase:
                            last_dispatched_phrase = normalized_phrase
                            last_dispatch_time = time.time()
                    except Exception as e:
                        print(f"Error sending BLE event: {e}")

        except GeneratorExit:
            print("🛑 Voice listening stopped (generator exit)")
        except Exception as e:
            print(f"❌ Error in voice thread: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if triggered_session:
                # Reset to wake word mode after each triggered listening session.
                pause_event.clear()
                wake_stream_active.set()
                print(
                    "✅ System reset complete - now listening for wake word or motion"
                )
                time.sleep(0.2)


def run_system():
    # ui = SystemUI()
    # BLE Worker threads now handle all BLE communication (one per rack)

    start_manual_connect_server()
    triggered_mode = use_triggered_voice_session()

    t1 = threading.Thread(target=voice_thread, args=(), daemon=True)
    t4 = threading.Thread(target=recent_match_update_worker, args=(), daemon=True)

    t1.start()
    t4.start()

    # Motion/wake trigger threads are optional behind HRS_TRIGGER_MODE.
    threads = [t1, t4]
    if triggered_mode:
        t2 = threading.Thread(
            target=motion_listener,
            args=(
                voice_trigger,
                shutdown_flag,
                pause_event,
                wake_stream_active,
                send_ble_command_now,
                get_all_rack_numbers,
            ),
            daemon=True,
        )
        t3 = threading.Thread(
            target=wake_word_listener,
            args=(
                voice_trigger,
                shutdown_flag,
                pause_event,
                wake_stream_active,
                wake_stream_released,
                send_ble_command_now,
                get_all_rack_numbers,
            ),
            daemon=True,
        )
        t2.start()
        t3.start()
        threads.extend([t2, t3])
        print("Voice trigger mode enabled: wake word and motion listener started")
    else:
        print("Always-on mode enabled: wake word and motion listener are disabled")

    # Start one persistent BLE worker thread per rack.
    for rack_num in get_all_rack_numbers():
        # Stagger initial connects so the adapter doesn't get hammered by four
        # simultaneous discovery/connect attempts.
        t_ble = threading.Thread(
            target=ble_worker_thread,
            args=(rack_num, rack_num, (rack_num - 1) * 3),
            daemon=True,
        )
        t_ble.start()
        threads.append(t_ble)

    if triggered_mode:
        print(
            "All threads started: voice, motion, wake word, recent-match worker, and per-rack BLE workers"
        )
    else:
        print(
            "All threads started: always-on voice, recent-match worker, and per-rack BLE workers"
        )

    # ui.run()


# def speak(text):
#     engine.say(text)
#     engine.runAndWait()


def run_transcriber():
    print("Starting voice query...")
    # db = load_database_from_sqlite("medical_supplies.db")
    try:
        db = load_database_from_sqlite()
        print("Database loaded in transcriber.")
    except Exception as e:
        print(f"Error loading database: {e}")
    print("Loaded database:", db)

    # Create a shutdown flag for the transcriber
    transcriber_shutdown = threading.Event()

    print("\n🎤 Listening... Speak now! (Press Ctrl+C to exit)\n")

    try:
        while not transcriber_shutdown.is_set():
            text = listen_and_transcribe(transcriber_shutdown)
            if not text:
                continue

            print(f"\n🗣️  Heard: '{text}'")

            # Respond to conversational phrases
            if "thank you" in text.lower():
                response = "You're welcome!"
                print(f"💬 {response}")
                # speak(response)

            result = find_keyword(text, db)
            if result:
                print(
                    f"✅ Found: {result['item']} at Rack {result['rack']}, Location {result['location']}"
                )
            else:
                print("❌ No matching item found")

            print("\n🎤 Listening...\n")
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down voice control...")
        transcriber_shutdown.set()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Hospital Retrieval System - Voice Control")
    print("=" * 60 + "\n")

    # Choose which mode to run
    # run_system()        # Full system with motion, wake word, BLE
    run_transcriber()  # Simple voice transcription mode for testing
