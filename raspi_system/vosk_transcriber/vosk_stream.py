# vosk_transcriber/vosk_stream.py
import sounddevice as sd
import queue
import vosk
import json

model = vosk.Model("vosk-model-small-en-us-0.15")  # Adjust path if needed
q = queue.Queue()


def callback(indata, frames, time, status):
    # suppress status printing to avoid noisy terminal output
    if status:
        pass
    q.put(bytes(indata))


def stream_text():
    with sd.RawInputStream(
        samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback
    ):
        rec = vosk.KaldiRecognizer(model, 16000)
        print("Listening...")

        def _dedupe_tail(s: str) -> str:
            if not s:
                return s
            max_k = min(5, len(s) // 2)
            for k in range(1, max_k + 1):
                if s.endswith(s[-k:] * 2):
                    return s[:-k]
            return s

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    text = _dedupe_tail(text)
                    if text:
                        yield text
            else:
                # do not print partials in the terminal
                # partial = json.loads(rec.PartialResult()).get("partial", "")
                # if partial:
                #     print(f"Partial: {partial}", end="\r")
                pass
