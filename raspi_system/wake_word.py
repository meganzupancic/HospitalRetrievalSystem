# wake_word.py
import threading

import numpy as np
import pvporcupine
import sounddevice as sd

ACCESS_KEY = "Ol05Gwg+qgIU/93zUK9BRMO0WknMmDvfs09gwnKUB/1iOkiGAbXu+Q=="


def wake_word_listener(
    trigger_event, shutdown_flag, pause_event, wake_stream_active, ui
):
    print("Porcupine wake word thread started.")

    porcupine = None
    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY, keywords=["picovoice"]
        )  # Use built-in wake word
    except Exception as e:
        # Try to detect the specific activation-limit exception class if available
        activation_error_class = None
        try:
            from pvporcupine._porcupine import PorcupineActivationLimitError as activation_error_class
        except Exception:
            activation_error_class = getattr(pvporcupine, "PorcupineActivationLimitError", None)

        # Heuristic: either the specific exception or the picovoice error code shows activation limit
        msg = str(e)
        if (activation_error_class and isinstance(e, activation_error_class)) or "00000136" in msg or "ActivationLimit" in msg or "activation limit" in msg.lower():
            ui.log(
                "Porcupine activation limit reached (Picovoice error 00000136). Wake-word disabled. "
                "Check ACCESS_KEY, device activations in Picovoice Console, or obtain a valid license.",
                tag="red",
            )
        else:
            ui.log(f"Porcupine initialization failed: {e}", tag="red")
        import traceback
        ui.log(traceback.format_exc(), tag="red")

        # Disable wake-word stream and exit listener thread cleanly
        wake_stream_active.clear()
        return

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
