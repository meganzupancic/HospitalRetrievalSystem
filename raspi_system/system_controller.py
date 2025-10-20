# Coordinates all modules and threads
# class SystemController

# Each class above can be run in its own thread, coordinated by SystemController. Use Queue for inter-thread communication:
# MotionDetectionHandler → triggers WakeWordDetector
# WakeWordDetector → triggers SpeechToTextProcessor
# SpeechToTextProcessor → sends text to NLPParser
# NLPParser → queries DatabaseManager
# DatabaseManager → sends location to BLECommunicationManager

# system_controler.py

import threading
from datetime import time

import pyttsx3
from database_manager import load_database_from_json
from motion_handler import motion_listener
from nlp_parser import find_keyword
from speech_to_text import listen_and_transcribe
from wake_word import wake_word_listener

engine = pyttsx3.init()
voice_trigger = threading.Event()
pause_event = threading.Event()
shutdown_flag = threading.Event()
wake_stream_active = threading.Event()
wake_stream_active.set()

# import socket


# def send_location_to_frontend(location_id):
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.connect(("localhost", 5050))
#         message = f"HIGHLIGHT:{location_id}"
#         sock.sendall(message.encode())
#         sock.close()
#     except Exception as e:
#         print(f"Error sending to frontend: {e}")


def voice_thread():
    print("Voice thread started. Waiting for trigger...")
    db = load_database_from_json("database\\medical_supplies.json")

    while not shutdown_flag.is_set():
        if voice_trigger.wait(timeout=1):
            voice_trigger.clear()
            pause_event.set()

            try:
                # Start a new transcription session
                for phrase in listen_and_transcribe(shutdown_flag):
                    if shutdown_flag.is_set():
                        break
                    # print(f"Heard: {phrase}")
                    result = find_keyword(phrase, db)
                    print("Keyword match result:", result)

                    if "Rack" in result:
                        continue
                    if "thank you" in phrase.lower():
                        response = "You're welcome!"
                        print(response)
                        # speak(response)
                        continue
            except GeneratorExit:
                break
            except Exception as e:
                print(f"Error in voice thread: {e}")

            # print("Keyword match result:", result)
            # print(result)

            pause_event.clear()
            wake_stream_active.set()  # Reactivate Porcupine stream
            time.sleep(0.5)  # Brief pause before next listening session


def run_system():
    t1 = threading.Thread(target=voice_thread, daemon=True)
    t2 = threading.Thread(
        target=motion_listener,
        args=(voice_trigger, shutdown_flag, pause_event),
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


# def speak(text):
#     engine.say(text)
#     engine.runAndWait()


def run_transcriber():
    print("Starting voice query...")
    db = load_database_from_json("database\\medical_supplies.json")
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
