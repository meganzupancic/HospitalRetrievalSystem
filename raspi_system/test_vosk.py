import json

import sounddevice as sd
import vosk

print(sd.query_devices())
print("Default input device:", sd.default.device)

model = vosk.Model("vosk-model-small-en-us-0.15")
rec = vosk.KaldiRecognizer(model, 16000)

with sd.RawInputStream(
    samplerate=16000, blocksize=8000, dtype="int16", channels=1
) as stream:
    print("Say something...")
    while True:
        data = stream.read(8000)[0]
        if rec.AcceptWaveform(data):
            print(json.loads(rec.Result()))
        else:
            print(json.loads(rec.PartialResult()))
