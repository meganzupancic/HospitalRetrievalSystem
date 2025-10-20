# vosk_transcriber/vosk_stream.py
import sounddevice as sd
import queue
import vosk
import json

model = vosk.Model("vosk-model-small-en-us-0.15")  # Adjust path if needed
q = queue.Queue()


def callback(indata, frames, time, status):
    if status:
        print(f"Mic status: {status}")
    q.put(bytes(indata))


def stream_text():
    with sd.RawInputStream(
        samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback
    ):
        rec = vosk.KaldiRecognizer(model, 16000)
        print("Listening...")

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    yield text
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                if partial:
                    print(f"Partial: {partial}", end="\r")
