# wake_word.py
import json
import queue

import sounddevice as sd
import vosk

WAKE_WORD = "hospital system"
model_path = "vosk_model/vosk-model-small-en-us-0.15"
model = vosk.Model(model_path)
q = queue.Queue()


def callback(indata, frames, time, status):
    if status:
        pass
    q.put(bytes(indata))


def wake_word_listener(voice_trigger, shutdown_flag, pause_event, wake_stream_active):
    print("Wake word listener started.")
    rec = vosk.KaldiRecognizer(model, 16000)

    try:
        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while not shutdown_flag.is_set():
                if not wake_stream_active.is_set():
                    continue  # Wait until voice thread is done

                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if WAKE_WORD in text.lower():
                        print(f"Wake word '{WAKE_WORD}' detected.")
                        voice_trigger.set()
                        wake_stream_active.clear()
    except Exception as e:
        print(f"Error in wake word listener: {e}")
