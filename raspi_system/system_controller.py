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
import os
import queue
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading

# import tkinter as tk
import time

# from tkinter import scrolledtext
import pyttsx3
from bleak import BleakClient, BleakScanner

from raspi_system.arduino_config import get_all_rack_numbers, get_arduino_config
from raspi_system.motion_handler import motion_listener
from raspi_system.nlp_parser import find_keyword

# from bleak import BleakClient
# DEVICE_ADDRESS = "C6:10:17:BD:9F:7F"  # your Nordic_LBS MAC
# LBS_LED_CHAR_UUID = "00001525-1212-efde-1523-785feabcd123"
# from app import socketio
from raspi_system.rack_database_adapter import load_database_from_sqlite
from raspi_system.speech_to_text import listen_and_transcribe
from raspi_system.vosk_wake_word import wake_word_listener

# from socketio_instance import socketio


def build_26bit_payload(slot_number=None, start_flag=False):
    """Build 26-bit payload: bits 0-23 slots 1-24, bit 24 unused, bit 25 start.

    Returns 4 bytes (32 bits) in little-endian format.
    """
    bit_pattern = 0

    if slot_number is not None and 1 <= slot_number <= 24:
        bit_pattern |= 1 << (slot_number - 1)

    if start_flag:
        bit_pattern |= 1 << 25

    # Mask to keep only lower 26 bits
    bit_pattern &= 0x03FFFFFF

    return bit_pattern.to_bytes(4, byteorder="little")


engine = pyttsx3.init()
voice_trigger = threading.Event()
pause_event = threading.Event()
shutdown_flag = threading.Event()
wake_stream_active = threading.Event()
wake_stream_active.set()

# Create per-rack BLE queues and ready events
ble_event_queues = {}  # maps rack number to queue
ble_event_ready_events = {}  # maps rack number to ready event

for rack_num in get_all_rack_numbers():
    ble_event_queues[rack_num] = queue.Queue()
    ble_event_ready_events[rack_num] = threading.Event()


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


def ble_worker_thread(rack_number):
    """BLE Worker thread for a specific rack/Arduino.

    Args:
        rack_number: The rack number (1-4) this worker handles
    """
    config = get_arduino_config(rack_number)
    if not config:
        print(f"BLE Worker (Rack {rack_number}): No config found")
        return

    arduino_name = config["name"]
    arduino_address = config["address"]
    char_uuid = config["char_uuid"]

    print(f"BLE Worker (Rack {rack_number}): Starting for {arduino_name}...")

    async def find_and_connect():
        """Scan for Arduino by name and connect."""
        print(f"BLE Worker (Rack {rack_number}): Scanning for '{arduino_name}'...")
        try:
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
                return None

            # Small delay to let BlueZ stabilize after scan
            await asyncio.sleep(0.5)

            # Use the device object directly for better connection reliability
            client = BleakClient(target)
            await client.connect(timeout=15.0)
            print(
                f"BLE Worker (Rack {rack_number}): ✅ Connected to {target.name or target.address}"
            )

            # Allow connection to fully stabilize
            await asyncio.sleep(1.0)
            return client

        except Exception as e:
            print(f"BLE Worker (Rack {rack_number}): Connection error: {e}")
            return None

    async def process_events(client):
        """Process events from queue and write to Arduino."""
        loop = asyncio.get_event_loop()
        event_queue = ble_event_queues[rack_number]
        event_ready = ble_event_ready_events[rack_number]

        while not shutdown_flag.is_set():
            try:
                # Check if still connected
                if not client.is_connected:
                    print(f"BLE Worker (Rack {rack_number}): ❌ Connection lost")
                    return False

                # Wait efficiently for queue items using threading.Event
                await loop.run_in_executor(None, lambda: event_ready.wait(timeout=0.1))

                # Process all queued events
                while not event_queue.empty():
                    try:
                        event = event_queue.get_nowait()
                        event_queue.task_done()

                        recv_time = time.time()
                        queue_latency = recv_time - event.get("queued_at", recv_time)
                        keyword = event.get("keyword", "unknown")
                        slot_number = event.get("slot")
                        print(
                            f"BLE Worker (Rack {rack_number}): ⚡ Event received for '{keyword}' slot {slot_number} (queue latency: {queue_latency*1000:.1f}ms)"
                        )

                        # Process the event - write to Arduino
                        try:
                            write_start = time.time()

                            # Check if this is a wake word event or keyword event
                            if keyword == "wake_word_start":
                                # Wake word event - set start bit (bit 25)
                                payload = build_26bit_payload(start_flag=True)
                                print(
                                    f"BLE Worker (Rack {rack_number}): Sending wake word payload: {payload.hex()}"
                                )
                                await client.write_gatt_char(
                                    char_uuid, payload, response=True
                                )
                                write_time = (time.time() - write_start) * 1000
                                print(
                                    f"BLE Worker (Rack {rack_number}): ✅ Wake word payload sent (write took {write_time:.1f}ms)"
                                )
                            else:
                                # Keyword event - set slot bit (0-23)
                                payload = build_26bit_payload(slot_number=slot_number)
                                print(
                                    f"BLE Worker (Rack {rack_number}): Sending slot payload: {payload.hex()}"
                                )
                                await client.write_gatt_char(
                                    char_uuid, payload, response=True
                                )
                                write_time = (time.time() - write_start) * 1000
                                print(
                                    f"BLE Worker (Rack {rack_number}): ✅ Slot {slot_number} payload sent: {payload.hex()} (write took {write_time:.1f}ms)"
                                )
                        except Exception as e:
                            print(f"BLE Worker (Rack {rack_number}): Write failed: {e}")
                            return False
                    except queue.Empty:
                        break

                # Clear the event after processing
                event_ready.clear()

            except Exception as e:
                print(f"BLE Worker (Rack {rack_number}): Event processing error: {e}")
                return False

        return True

    async def run_ble_worker():
        """Main BLE worker loop with reconnection."""
        while not shutdown_flag.is_set():
            client = await find_and_connect()

            if client:
                # Stay connected and process events
                try:
                    await process_events(client)
                except Exception as e:
                    print(f"BLE Worker (Rack {rack_number}): Event loop error: {e}")
                finally:
                    try:
                        if client.is_connected:
                            await client.disconnect()
                            print(f"BLE Worker (Rack {rack_number}): Disconnected")
                    except:
                        pass

            # Wait before reconnecting
            if not shutdown_flag.is_set():
                print(f"BLE Worker (Rack {rack_number}): Reconnecting in 3 seconds...")
                await asyncio.sleep(3)

        print(f"BLE Worker (Rack {rack_number}): Shutting down")

    # Run the async worker
    try:
        asyncio.run(run_ble_worker())
    except Exception as e:
        print(f"BLE Worker (Rack {rack_number}): Fatal error: {e}")


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
    print("Voice thread started. Waiting for trigger...")
    # try:
    #     db = load_database_from_sqlite()
    #     print("Database loaded in voice thread.")
    # except Exception as e:
    #     print(f"Error loading database: {e}")

    INACTIVITY_TIMEOUT = 30  # seconds

    while not shutdown_flag.is_set():
        if voice_trigger.wait(timeout=1):
            voice_trigger.clear()
            pause_event.set()

            # Give wake word listener time to release the audio device
            time.sleep(0.5)

            # Send wake word notification to all racks
            print("🎤 Wake word detected! Sending notification to all racks...")
            queue_time = time.time()
            for rack_num in ble_event_queues.keys():
                try:
                    ble_event_queues[rack_num].put(
                        {
                            "keyword": "wake_word_start",
                            "rack": rack_num,
                            "slot": None,
                            "queued_at": queue_time,
                        }
                    )
                    ble_event_ready_events[rack_num].set()
                    print(f"✅ Wake word event queued for Rack {rack_num}")
                except Exception as e:
                    print(f"❌ Error queuing wake word event for Rack {rack_num}: {e}")

            try:
                last_activity_time = time.time()
                last_status_print = time.time()
                print("⏱️  Listening for keywords (30s timeout)...")

                for phrase in listen_and_transcribe(shutdown_flag):
                    # Check for timeout
                    current_time = time.time()
                    elapsed = current_time - last_activity_time

                    # Print periodic status (every 10 seconds)
                    if current_time - last_status_print >= 10:
                        remaining = max(0, INACTIVITY_TIMEOUT - elapsed)
                        print(f"⏱️  Still listening... ({remaining:.0f}s until timeout)")
                        last_status_print = current_time

                    if elapsed > INACTIVITY_TIMEOUT:
                        print(
                            f"\n⏰ Timeout: No activity for {INACTIVITY_TIMEOUT} seconds"
                        )
                        print("🔄 Resetting to wake word/motion detection mode...")
                        break

                    if phrase is None or not isinstance(phrase, str):
                        continue

                    if shutdown_flag.is_set():
                        break

                    # Update activity time when we receive a phrase
                    last_activity_time = time.time()
                    last_status_print = time.time()  # Reset status print timer too
                    print("⏱️  Activity detected, timeout reset")

                    db = load_database_from_sqlite()

                    print(f"Heard: {phrase}")
                    result = find_keyword(phrase, db)
                    print(f"Keyword match result: {result}")

                    if result:
                        keyword = result.get("item")
                        # Load full DB and find all instances of this item so we can report every rack/location
                        try:
                            full_db = load_database_from_sqlite()
                            matches = [
                                e
                                for e in full_db
                                if e.get("item", "").lower() == keyword.lower()
                            ]
                        except Exception:
                            matches = []

                        if matches:
                            # Aggregate locations by rack for clearer output
                            racks = {}
                            for m in matches:
                                rack = m.get("rack")
                                loc = m.get("location")
                                racks.setdefault(rack, []).append(loc)

                            print(f"Found item: '{keyword}'")
                            for rack, locs in sorted(racks.items()):
                                locs_sorted = sorted(locs)
                                locs_str = ", ".join(str(loc) for loc in locs_sorted)
                                print(f"  • Rack #{rack} locations: {locs_str}")

                        else:
                            # Single result from NLP; print the reported rack/location
                            print(f"Found item: '{keyword}'")
                            print(
                                f"  • Rack #{result.get('rack')} Location {result.get('location')}"
                            )
                        # socketio.emit("highlight_keyword", {"keyword": keyword})

                        # Trigger LED light on Nordic board
                        # asyncio.run(light_led_for_seconds(5))

                        # Send BLE signal to the Arduino for the specific rack
                        try:
                            rack_num = result.get("rack")
                            slot_num = result.get(
                                "location"
                            )  # location is the slot number
                            if rack_num and rack_num in ble_event_queues:
                                queue_time = time.time()
                                ble_event_queues[rack_num].put(
                                    {
                                        "keyword": keyword,
                                        "rack": rack_num,
                                        "slot": slot_num,
                                        "queued_at": queue_time,
                                    }
                                )
                                ble_event_ready_events[
                                    rack_num
                                ].set()  # Signal immediately
                                print(
                                    f"✅ Event queued for Rack {rack_num}, Slot {slot_num} at {queue_time:.3f}"
                                )
                            else:
                                print(
                                    f"❌ Invalid or unconfigured rack number: {rack_num}"
                                )
                        except Exception as e:
                            print(f"Error queuing BLE event: {e}")

            except GeneratorExit:
                print("🛑 Voice listening stopped (generator exit)")
            except Exception as e:
                print(f"❌ Error in voice thread: {e}")
                import traceback

                traceback.print_exc()
            finally:
                # Always reset to wake word mode after listening session ends
                pause_event.clear()
                wake_stream_active.set()
                print(
                    "✅ System reset complete - now listening for wake word or motion"
                )
                time.sleep(0.5)


def run_system():
    # ui = SystemUI()
    # BLE Worker threads now handle all BLE communication (one per rack)

    t1 = threading.Thread(target=voice_thread, args=(), daemon=True)
    t2 = threading.Thread(
        target=motion_listener,
        args=(voice_trigger, shutdown_flag, pause_event, wake_stream_active),
        daemon=True,
    )
    t3 = threading.Thread(
        target=wake_word_listener,
        args=(voice_trigger, shutdown_flag, pause_event, wake_stream_active),
        daemon=True,
    )

    t1.start()
    t2.start()
    t3.start()

    # Start a BLE worker thread for each rack
    threads = [t1, t2, t3]
    for rack_num in get_all_rack_numbers():
        t_ble = threading.Thread(
            target=ble_worker_thread, args=(rack_num,), daemon=True
        )
        t_ble.start()
        threads.append(t_ble)

    print(
        f"All threads started: voice, motion, wake word, and BLE workers for {len(get_all_rack_numbers())} racks"
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
