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
from datetime import time

# from tkinter import scrolledtext
import pyttsx3

# from app import socketio
from raspi_system.database_manager import load_database_from_sqlite
from raspi_system.motion_handler import motion_listener
from raspi_system.nlp_parser import find_keyword
from raspi_system.speech_to_text import listen_and_transcribe
from raspi_system.wake_word import wake_word_listener

# from socketio_instance import socketio

engine = pyttsx3.init()
voice_trigger = threading.Event()
pause_event = threading.Event()
shutdown_flag = threading.Event()
wake_stream_active = threading.Event()
wake_stream_active.set()

# init_db()
# db = load_database_from_sqlite("medical_supplies.db")


# def send_location_to_frontend(location_id):
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.connect(("localhost", 5050))
#         message = f"HIGHLIGHT:{location_id}"
#         sock.sendall(message.encode())
#         sock.close()
#     except Exception as e:
#         print(f"Error sending to frontend: {e}")


# class SystemUI:
#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title("System Controller Monitor")

#         self.output_text = scrolledtext.ScrolledText(
#             self.root, width=80, height=25, font=("Courier", 12)
#         )
#         self.output_text.pack(padx=10, pady=10)

#         # Configure text colors for different message types
#         self.output_text.tag_config("green", foreground="green")
#         self.output_text.tag_config("blue", foreground="#0066cc")
#         self.output_text.tag_config("purple", foreground="#6600cc")
#         self.output_text.tag_config("orange", foreground="#ff6600")
#         self.output_text.tag_config("bold", font=("Courier", 12, "bold"))

#         self.root.protocol("WM_DELETE_WINDOW", self.on_close)

#         # Initial welcome message
#         self.log(
#             "Welcome to the Hospital Retrieval System (prototype). \n"
#             "Please say the wake word to begin..."
#         )

#     def log(self, message, tag=None):
#         self.output_text.insert(tk.END, message + "\n", tag)
#         self.output_text.see(tk.END)
#         self.root.update()

#     def run(self):
#         self.root.mainloop()

#     def on_close(self):
#         shutdown_flag.set()
#         self.root.destroy()


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
                            # Create header for multiple instances with highlighting
                            # ui.log(f"Item found: ", tag="bold")
                            # ui.log(f"\"{keyword}\"", tag="blue")
                            # ui.log("\nLocations:", tag="orange")
                            # # Log each instance on a new line with highlighting
                            # for m in matches:
                            #     location_text = f"  • Rack #{m.get('rack')} Location {m.get('location')}"
                            #     ui.log(location_text, tag="purple")
                            # ui.log("") # Empty line for spacing
                            print(f"Item '{keyword}' found in multiple locations:")
                            for m in matches:
                                location_text = f"  • Rack #{m.get('rack')} Location {m.get('location')}"
                                print(location_text)
                        else:
                            # Fallback to the single result returned by the NLP parser
                            # ui.log(f"Item found: ", tag="bold")
                            # ui.log(f"\"{keyword}\"", tag="blue")
                            # location_text = f"\n  • Rack #{result.get('rack')} Location {result.get('location')}"
                            # ui.log(location_text, tag="purple")
                            # ui.log("")  # Empty line for spacing
                            print(f'Item found: "{keyword}"')
                            location_text = f"  • Rack #{result.get('rack')} Location {result.get('location')}"
                        # socketio.emit("highlight_keyword", {"keyword": keyword})

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
