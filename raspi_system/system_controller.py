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

# from bleak import BleakClient
# DEVICE_ADDRESS = "C6:10:17:BD:9F:7F"  # your Nordic_LBS MAC
# LBS_LED_CHAR_UUID = "00001525-1212-efde-1523-785feabcd123"
# from app import socketio
from raspi_system.database_manager import load_database_from_sqlite
from raspi_system.motion_handler import motion_listener
from raspi_system.nlp_parser import find_keyword
from raspi_system.speech_to_text import listen_and_transcribe

# from raspi_system.wake_word import wake_word_listener
from raspi_system.vosk_wake_word import wake_word_listener

# from socketio_instance import socketio

engine = pyttsx3.init()
voice_trigger = threading.Event()
pause_event = threading.Event()
shutdown_flag = threading.Event()
wake_stream_active = threading.Event()
wake_stream_active.set()
ble_event_queue = queue.Queue()
ble_event_ready = threading.Event()  # Signals when queue has items


SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
ARDUINO_ADDRESS = "8D:3E:F7:D1:4E:34"
ARDUINO_NAME = "Nano33BLE-Light"


class BLEManager:
    def __init__(self, char_uuid=CHAR_UUID):
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
        while True:
            try:
                if not self.client or not self.client.is_connected:
                    print(f"BLEManager: attempting connection to {ARDUINO_ADDRESS}")
                    self.client = BleakClient(ARDUINO_ADDRESS)

                    try:
                        await self.client.connect()
                        print("BLEManager: Connected to Arduino")
                        self.connected_event.set()

                        # Allow BlueZ to stabilize
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"BLEManager: connection failed: {e}")
                        await asyncio.sleep(2)
                        continue

                # Stay connected until it drops
                while self.client.is_connected:
                    await asyncio.sleep(0.5)

                print("BLEManager: connection lost, retrying...")
                self.connected_event.clear()

            except Exception as e:
                print(f"BLEManager: connection loop error: {e}")

            await asyncio.sleep(1)

    def send_signal(self, data: bytes = b"1"):
        """Thread-safe write entry point."""
        if not self.loop:
            print("BLEManager: loop not started")
            return

        fut = asyncio.run_coroutine_threadsafe(self._write(data), self.loop)
        try:
            fut.result(timeout=5)
        except Exception as e:
            print(f"BLEManager: write timeout/error: {e}")

    async def _write(self, data: bytes):
        """Safe BLE write that never races with reconnect."""
        async with self._lock:
            try:
                if not self.client or not self.client.is_connected:
                    print("BLEManager: not connected, cannot write")
                    return

                await self.client.write_gatt_char(self.char_uuid, data, response=False)
                print("BLEManager: signal sent")

            except Exception as e:
                print(f"BLEManager write failed: {e}")


async def send_alert():
    print("Scanning for Arduino...")
    devices = await BleakScanner.discover()
    for d in devices:
        print(d)

    target = None
    for d in devices:
        if "Nano33BLE" in d.name:
            target = d
            break

    if not target:
        print("Arduino not found")
        return

    async with BleakClient(target.address) as client:
        print("Connected. Sending alert...")
        await client.write_gatt_char(CHAR_UUID, b"1")
        print("Alert sent")


# Call this when keyword is found:
# asyncio.run(send_alert())


def ble_worker_thread():
    """BLE Worker thread that connects to Nano 33 BLE and processes keyword events."""
    print("BLE Worker: Starting...")

    async def find_and_connect():
        """Scan for Arduino by name and connect."""
        print(f"BLE Worker: Scanning for '{ARDUINO_NAME}'...")
        try:
            devices = await BleakScanner.discover(timeout=10.0)
            target = None

            # First try to find by name
            for device in devices:
                if device.name and ARDUINO_NAME in device.name:
                    target = device
                    print(f"BLE Worker: Found Arduino by name at {device.address}")
                    break

            # Fallback: try to find by known address
            if not target:
                print(f"BLE Worker: Name not found, trying address {ARDUINO_ADDRESS}")
                for device in devices:
                    if device.address == ARDUINO_ADDRESS:
                        target = device
                        print("BLE Worker: Found Arduino by address")
                        break

            if not target:
                print(
                    f"BLE Worker: Arduino not found in scan (scanned {len(devices)} devices)"
                )
                return None

            # Small delay to let BlueZ stabilize after scan
            await asyncio.sleep(0.5)

            # Use the device object directly for better connection reliability
            client = BleakClient(target)
            await client.connect(timeout=15.0)
            print(f"BLE Worker: ✅ Connected to {target.name or target.address}")

            # Allow connection to fully stabilize
            await asyncio.sleep(1.0)
            return client

        except Exception as e:
            print(f"BLE Worker: Connection error: {e}")
            return None

    async def process_events(client):
        """Process events from queue and write to Arduino."""
        loop = asyncio.get_event_loop()

        while not shutdown_flag.is_set():
            try:
                # Check if still connected
                if not client.is_connected:
                    print("BLE Worker: ❌ Connection lost")
                    return False

                # Wait efficiently for queue items using threading.Event
                await loop.run_in_executor(
                    None, lambda: ble_event_ready.wait(timeout=0.1)
                )

                # Process all queued events
                while not ble_event_queue.empty():
                    try:
                        event = ble_event_queue.get_nowait()
                        ble_event_queue.task_done()

                        recv_time = time.time()
                        queue_latency = recv_time - event.get("queued_at", recv_time)
                        print(
                            f"BLE Worker: ⚡ Event received (queue latency: {queue_latency*1000:.1f}ms)"
                        )

                        # Process the event - write to Arduino
                        try:
                            write_start = time.time()
                            # Write "1" to trigger LED - fire and forget for minimum latency
                            await client.write_gatt_char(
                                CHAR_UUID, b"1", response=False
                            )
                            write_time = (time.time() - write_start) * 1000
                            print(
                                f"BLE Worker: ✅ Signal sent (write took {write_time:.1f}ms)"
                            )
                        except Exception as e:
                            print(f"BLE Worker: Write failed: {e}")
                            return False
                    except queue.Empty:
                        break

                # Clear the event after processing
                ble_event_ready.clear()

            except Exception as e:
                print(f"BLE Worker: Event processing error: {e}")
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
                    print(f"BLE Worker: Event loop error: {e}")
                finally:
                    try:
                        if client.is_connected:
                            await client.disconnect()
                            print("BLE Worker: Disconnected")
                    except:
                        pass

            # Wait before reconnecting
            if not shutdown_flag.is_set():
                print("BLE Worker: Reconnecting in 3 seconds...")
                await asyncio.sleep(3)

        print("BLE Worker: Shutting down")

    # Run the async worker
    try:
        asyncio.run(run_ble_worker())
    except Exception as e:
        print(f"BLE Worker: Fatal error: {e}")


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

    while not shutdown_flag.is_set():
        if voice_trigger.wait(timeout=1):
            voice_trigger.clear()
            pause_event.set()

            try:
                for phrase in listen_and_transcribe(shutdown_flag):

                    if phrase is None or not isinstance(phrase, str):
                        continue

                    if shutdown_flag.is_set():
                        break

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

                        # Send BLE signal to Arduino when keyword is found
                        try:
                            # Put event in queue for BLE worker thread
                            queue_time = time.time()
                            ble_event_queue.put(
                                {"keyword": keyword, "queued_at": queue_time}
                            )
                            ble_event_ready.set()  # Signal immediately
                            print(f"✅ Event queued at {queue_time:.3f}")
                        except Exception as e:
                            print(f"Error queuing BLE event: {e}")

            except GeneratorExit:
                break
            except Exception as e:
                print(f"Error in voice thread: {e}")

            pause_event.clear()
            wake_stream_active.set()
            time.sleep(0.5)


def run_system():
    # ui = SystemUI()
    # BLE Worker thread now handles all BLE communication

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
    t4 = threading.Thread(target=ble_worker_thread, args=(), daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    print("All threads started: voice, motion, wake word, BLE worker")

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
    while True:
        text = listen_and_transcribe()
        # print(f"Heard: {text}")
        # Respond to conversational phrases
        if "thank you" in text.lower():
            response = "You're welcome!"
            print(response)
            # speak(response)
        result = find_keyword(text, db)
        print(result)
