# wake_word.py
import json
import queue
import time

import sounddevice as sd
import vosk

WAKE_WORD = "iris"
WAKE_WORD_DISPLAY = "Iris"
model_path = "vosk_model/vosk-model-small-en-us-0.15"
model = vosk.Model(model_path)
q = queue.Queue()

# test to see if sound device is working
print(sd.query_devices())


def callback(indata, frames, time, status):
    if status:
        pass
    q.put(bytes(indata))


def wake_word_listener(
    voice_trigger,
    shutdown_flag,
    pause_event,
    wake_stream_active,
    ble_sender=None,
    rack_provider=None,
):
    print("Wake word listener started.")
    rec = vosk.KaldiRecognizer(model, 16000)

    # Prefer injected callbacks from the running controller instance so we don't
    # accidentally import a second copy of system_controller with separate globals.
    if ble_sender is None or rack_provider is None:
        try:
            from raspi_system.arduino_config import get_all_rack_numbers
            from raspi_system.system_controller import send_ble_command_now

            rack_provider = get_all_rack_numbers
            ble_sender = send_ble_command_now
            ble_available = True
        except Exception as e:
            print(f"BLE communication not available: {e}")
            ble_available = False
    else:
        ble_available = True

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
                            print(f"Wake word '{WAKE_WORD_DISPLAY}' detected.")

                            # Send 'start' to all connected Arduino devices via BLE
                            if ble_available:
                                try:
                                    rack_numbers = rack_provider()

                                    for rack_num in rack_numbers:
                                        if ble_sender(rack_num, "wake_word_start"):
                                            print(
                                                f"✅ 'start' sent for Arduino on Rack {rack_num}"
                                            )
                                        else:
                                            print(
                                                f"❌ 'start' failed for Arduino on Rack {rack_num}"
                                            )

                                    print(
                                        f"Sent 'start' to {len(rack_numbers)} Arduino device(s)"
                                    )
                                except Exception as e:
                                    print(
                                        f"Error sending 'start' to Arduino devices: {e}"
                                    )

                            voice_trigger.set()
                            wake_stream_active.clear()
                            print(
                                "⏸️  Wake word stream paused for voice transcription..."
                            )
                            break  # Exit inner loop, close stream

                print("Wake word stream closed")

        except Exception as e:
            print(f"Error in wake word listener: {e}")
            time.sleep(0.5)  # Brief pause before retrying
