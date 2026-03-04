# wake_word.py
import json
import queue
import time

import sounddevice as sd
import vosk

WAKE_WORD = "hospital system"
model_path = "vosk_model/vosk-model-small-en-us-0.15"
model = vosk.Model(model_path)
q = queue.Queue()

# test to see if sound device is working
print(sd.query_devices())


def callback(indata, frames, time, status):
    if status:
        pass
    q.put(bytes(indata))


def wake_word_listener(voice_trigger, shutdown_flag, pause_event, wake_stream_active):
    print("Wake word listener started.")
    rec = vosk.KaldiRecognizer(model, 16000)

    # Import BLE queues from system_controller (lazy import to avoid circular dependency)
    try:
        from raspi_system.arduino_config import get_all_rack_numbers
        from raspi_system.system_controller import (
            ble_event_queues,
            ble_event_ready_events,
        )

        ble_available = True
    except Exception as e:
        print(f"BLE communication not available: {e}")
        ble_available = False

def wake_word_listener(voice_trigger, shutdown_flag, pause_event, wake_stream_active):
    print("Wake word listener started.")
    rec = vosk.KaldiRecognizer(model, 16000)

    # Import BLE queues from system_controller (lazy import to avoid circular dependency)
    try:
        from raspi_system.arduino_config import get_all_rack_numbers
        from raspi_system.system_controller import (
            ble_event_queues,
            ble_event_ready_events,
        )

        ble_available = True
    except Exception as e:
        print(f"BLE communication not available: {e}")
        ble_available = False

    while not shutdown_flag.is_set():
        # Wait for voice stream to be available (not in use by transcriber)
        if not wake_stream_active.is_set():
            time.sleep(0.2)
            continue
        
        # Open stream only when needed
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback,
            ):
                print("Wake word stream opened")
                
                # Listen only while wake_stream_active is set and shutdown not requested
                while wake_stream_active.is_set() and not shutdown_flag.is_set():
                    try:
                        data = q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if WAKE_WORD in text.lower():
                            print(f"Wake word '{WAKE_WORD}' detected.")

                            # Send 'start' to all connected Arduino devices via BLE
                            if ble_available:
                                try:
                                    rack_numbers = get_all_rack_numbers()
                                    queue_time = time.time()

                                    for rack_num in rack_numbers:
                                        if rack_num in ble_event_queues:
                                            ble_event_queues[rack_num].put(
                                                {
                                                    "keyword": "wake_word_start",
                                                    "rack": rack_num,
                                                    "slot": None,  # No specific slot for wake word
                                                    "queued_at": queue_time,
                                                }
                                            )
                                            ble_event_ready_events[rack_num].set()
                                            print(
                                                f"✅ 'start' queued for Arduino on Rack {rack_num}"
                                            )

                                    print(
                                        f"Sent 'start' to {len(rack_numbers)} Arduino device(s)"
                                    )
                                except Exception as e:
                                    print(f"Error sending 'start' to Arduino devices: {e}")

                            voice_trigger.set()
                            wake_stream_active.clear()
                            print("⏸️  Wake word stream paused for voice transcription...")
                            break  # Exit inner loop, close stream
                
                print("Wake word stream closed")
                
        except Exception as e:
            print(f"Error in wake word listener: {e}")
            time.sleep(0.5)  # Brief pause before retrying
