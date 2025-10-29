# Convertes audio to text using offline STT engine (Vosk)
# class SpeechToTextProcessor
###___________________________________________________________________________________________________

# speech_to_text.py
import json
import queue

import sounddevice as sd
import vosk

model_path = "vosk_model/vosk-model-small-en-us-0.15"

model = vosk.Model(model_path)  # Path to your Vosk model folder
q = queue.Queue()


def callback(indata, frames, time, status):
    # reduce noisy status prints
    if status:
        pass
    q.put(bytes(indata))


def listen_and_transcribe(shutdown_flag):
    print("Listening...")
    rec = vosk.KaldiRecognizer(model, 16000)

    def _dedupe_tail(s: str) -> str:
        # If the string ends with a small substring repeated twice (e.g. 'aidaid'), trim one repetition.
        if not s:
            return s
        max_k = min(5, len(s) // 2)
        for k in range(1, max_k + 1):
            if s.endswith(s[-k:] * 2):
                return s[:-k]
        return s

    try:
        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ) as stream:
            print("Stream opened")
            while not shutdown_flag.is_set():
                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                # data = stream.read(8000)[0]
                # data = bytes(data)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        text = _dedupe_tail(text)
                        if text:
                            print(f"Heard: {text}")
                            yield text
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    # Do not print partials to the main terminal (reduces duplicates/noise)
                    # if partial:
                    #     print(f"Partial: {partial}", end="\r")
    except Exception as e:
        print(f"Error in audio stream: {e}")
