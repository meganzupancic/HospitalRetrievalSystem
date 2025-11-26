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
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading

# import tkinter as tk
import time

# from tkinter import scrolledtext
import pyttsx3

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
                    if shutdown_flag.is_set():
                        break

                    db = load_database_from_sqlite()
                    # print(f"Heard: {phrase}")
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
                            print(f"Item '{keyword}' found in multiple locations:")
                            for m in matches:
                                location_text = f"  • Rack #{m.get('rack')} Location {m.get('location')}"
                                print(location_text)
                        else:
                            print(f'Item found: "{keyword}"')
                            location_text = f"  • Rack #{result.get('rack')} Location {result.get('location')}"
                        # socketio.emit("highlight_keyword", {"keyword": keyword})

                        # Trigger LED light on Nordic board
                        # asyncio.run(light_led_for_seconds(5))

                        if "thank you" in phrase.lower():
                            response = "You're welcome!"
                            print(response)

            except GeneratorExit:
                break
            except Exception as e:
                print(f"Error in voice thread: {e}")

            pause_event.clear()
            wake_stream_active.set()
            time.sleep(0.5)


def run_system():
    # ui = SystemUI()
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
