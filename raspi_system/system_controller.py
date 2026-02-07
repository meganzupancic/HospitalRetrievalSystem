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
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading

# import tkinter as tk
import time

# from tkinter import scrolledtext
import pyttsx3
from bleak import BleakClient, BleakScanner
from raspi_to_arduino.send_slots import send_slot_string

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


SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
ARDUINO_ADDRESS = "8D:3E:F7:D1:4E:34"


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


# Create and start the BLE manager AFTER class definition
ble_manager = BLEManager()
ble_manager.start()


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

                            # Send slot occupancy string for all matched locations (once)
                            try:
                                all_locs = []
                                for locs in racks.values():
                                    all_locs.extend(locs)
                                # de-duplicate and send
                                unique_locs = sorted({int(x) for x in all_locs if x})
                                if unique_locs:
                                    send_slot_string(unique_locs)
                            except Exception as e:
                                print(f"Error sending multi-location slot string: {e}")

                        else:
                            # Single result from NLP; print the reported rack/location
                            print(f"Found item: '{keyword}'")
                            print(
                                f"  • Rack #{result.get('rack')} Location {result.get('location')}"
                            )
                            # Send slot occupancy string for the single reported location
                            try:
                                loc = int(result.get("location", 0))
                                if loc > 0:
                                    send_slot_string([loc])
                            except Exception as e:
                                print(f"Error sending single-location slot string: {e}")
                        # socketio.emit("highlight_keyword", {"keyword": keyword})

                        # Trigger LED light on Nordic board
                        # asyncio.run(light_led_for_seconds(5))

                        # Send BLE signal to Arduino when keyword is found
                        try:
                            ble_manager.send_signal()

                        except Exception as e:
                            print(f"Error sending BLE alert: {e}")

            except GeneratorExit:
                break
            except Exception as e:
                print(f"Error in voice thread: {e}")

            pause_event.clear()
            wake_stream_active.set()
            time.sleep(0.5)


def run_system():
    # ui = SystemUI()
    # Start BLE manager so Arduino is connected once at startup
    global ble_manager
    ble_manager = BLEManager()
    try:
        ble_manager.start()
    except Exception as e:
        print(f"Failed to start BLE manager: {e}")
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
