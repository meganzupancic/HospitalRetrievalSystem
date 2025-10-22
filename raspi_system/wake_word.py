# wake_word.py
import threading

import numpy as np
import pvporcupine
import sounddevice as sd

ACCESS_KEY = "u6opFld4V3f6QBSDvUfOP/KFgrojdVzI8H4JghtWNONoxVgqG/kAxQ=="


def wake_word_listener(
    trigger_event, shutdown_flag, pause_event, wake_stream_active, ui
):
    print("Porcupine wake word thread started.")

    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY, keywords=["picovoice"]
    )  # Use built-in wake word
    # audio_stream = sd.RawInputStream(
    #     samplerate=porcupine.sample_rate,
    #     blocksize=porcupine.frame_length,
    #     dtype="int16",
    #     channels=1,
    # )

    def listen_loop():
        while not shutdown_flag.is_set():
            if not pause_event.is_set() and wake_stream_active.is_set():
                with sd.RawInputStream(
                    samplerate=porcupine.sample_rate,
                    blocksize=porcupine.frame_length,
                    dtype="int16",
                    channels=1,
                ) as audio_stream:
                    while wake_stream_active.is_set() and not shutdown_flag.is_set():
                        pcm = audio_stream.read(porcupine.frame_length)[0]
                        pcm = np.frombuffer(pcm, dtype=np.int16)
                        keyword_index = porcupine.process(pcm)
                        if keyword_index >= 0:
                            ui.log("Wake word detected!", tag="green")
                            trigger_event.set()
                            pause_event.set()
                            wake_stream_active.clear()  # Fully stop Porcupine
            else:
                sd.sleep(100)

    threading.Thread(target=listen_loop, daemon=True).start()
