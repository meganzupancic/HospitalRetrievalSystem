# Convertes audio to text using offline STT engine (Vosk)
# class SpeechToTextProcessor
###___________________________________________________________________________________________________

# speech_to_text.py
import json
import queue

import sounddevice as sd
import vosk

# Default model path
model_path = "vosk_model/vosk-model-small-en-us-0.15"

# Available models configuration
AVAILABLE_MODELS = {
    "vosk_small": "vosk_model/vosk-model-small-en-us-0.15",
    "vosk_medium": "vosk_model/vosk-model-en-us-0.22",
    "whisper_tiny": None,  # Not implemented yet
    "whisper_base": None,  # Not implemented yet
}

# Current model (will be set by set_stt_model_choice)
model = None
current_model_name = None
q = queue.Queue()


def set_stt_model_choice(choice):
    """Set the STT model based on user choice.
    
    Args:
        choice: Can be 1-4 (numeric selection) or model name string
        
    Returns:
        str: Name of the selected model
    """
    global model, model_path, current_model_name
    
    # Map numeric choices to model names
    choice_map = {
        1: "vosk_small",
        "1": "vosk_small",
        2: "vosk_medium",
        "2": "vosk_medium",
        3: "whisper_tiny",
        "3": "whisper_tiny",
        4: "whisper_base",
        "4": "whisper_base",
    }
    
    # Handle numeric or string choice
    if isinstance(choice, (int, str)) and choice in choice_map:
        model_name = choice_map[choice]
    else:
        model_name = str(choice).lower().replace(" ", "_")
    
    # Get model path
    if model_name not in AVAILABLE_MODELS:
        print(f"⚠️  Unknown model '{model_name}', defaulting to vosk_small")
        model_name = "vosk_small"
    
    model_path = AVAILABLE_MODELS[model_name]
    
    if model_path is None:
        print(f"⚠️  Model '{model_name}' not implemented yet, defaulting to vosk_small")
        model_name = "vosk_small"
        model_path = AVAILABLE_MODELS[model_name]
    
    # Load the model
    try:
        print(f"📦 Loading STT model: {model_name}...")
        model = vosk.Model(model_path)
        current_model_name = model_name
        print(f"✅ Model loaded successfully: {model_name}")
        return model_name
    except Exception as e:
        print(f"❌ Error loading model '{model_name}': {e}")
        # Fallback to small model
        print("🔄 Falling back to vosk_small...")
        model_path = AVAILABLE_MODELS["vosk_small"]
        model = vosk.Model(model_path)
        current_model_name = "vosk_small"
        return "vosk_small"


# Initialize with default model
if model is None:
    set_stt_model_choice(1)


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
                    # Yield None to allow timeout checks in voice_thread
                    yield None
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
