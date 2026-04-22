# Convertes audio to text using offline STT engine (Vosk)
# class SpeechToTextProcessor
###___________________________________________________________________________________________________

# speech_to_text.py
import json
import os
import queue
import time

import sounddevice as sd
import vosk

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VOSK_MODEL_DIR = os.path.join(_BASE_DIR, "vosk_model")
_DEFAULT_AUDIO_BLOCKSIZE = 1600
_DEFAULT_EARLY_PARTIAL_MIN_CHARS = 4
_DEFAULT_EARLY_PARTIAL_STABLE_HITS = 2


def _log_partials_enabled():
    raw = str(os.getenv("HRS_LOG_PARTIALS", "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _early_partial_enabled():
    raw = str(os.getenv("HRS_EARLY_PARTIAL_FIRE", "1")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _get_early_partial_min_chars():
    raw = os.getenv(
        "HRS_EARLY_PARTIAL_MIN_CHARS", str(_DEFAULT_EARLY_PARTIAL_MIN_CHARS)
    )
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_EARLY_PARTIAL_MIN_CHARS
    return max(1, value)


def _get_early_partial_stable_hits():
    raw = os.getenv(
        "HRS_EARLY_PARTIAL_STABLE_HITS", str(_DEFAULT_EARLY_PARTIAL_STABLE_HITS)
    )
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_EARLY_PARTIAL_STABLE_HITS
    return max(1, value)


def _get_audio_blocksize():
    raw = os.getenv("HRS_AUDIO_BLOCKSIZE", str(_DEFAULT_AUDIO_BLOCKSIZE))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_AUDIO_BLOCKSIZE
    return value if value > 0 else _DEFAULT_AUDIO_BLOCKSIZE


def _model_path(folder_name):
    return os.path.join(_VOSK_MODEL_DIR, folder_name)


# Default model path (kept in sync with current loaded model)
model_path = _model_path("vosk-model-en-us-0.22")

# Available models configuration
AVAILABLE_MODELS = {
    "vosk_small": _model_path("vosk-model-small-en-us-0.15"),
    "vosk_medium": _model_path("vosk-model-en-us-0.22"),
    "vosk_large": _model_path("vosk-model-en-us-0.42-gigaspeech"),
    "whisper_tiny": None,  # Not implemented yet
    "whisper_base": None,  # Not implemented yet
}

# Current model (will be set by set_stt_model_choice)
model = None
current_model_name = None
q = queue.Queue()


def _is_model_available(path):
    return bool(path) and os.path.isdir(path)


def _best_available_vosk_model():
    # Prefer larger models when available for better transcription accuracy.
    for name in ("vosk_large", "vosk_medium", "vosk_small"):
        if _is_model_available(AVAILABLE_MODELS.get(name)):
            return name
    return "vosk_small"


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

    if not _is_model_available(model_path):
        fallback = _best_available_vosk_model()
        print(
            f"⚠️  Model files not found for '{model_name}' at '{model_path}'. "
            f"Using '{fallback}' instead."
        )
        model_name = fallback
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


def get_stt_model_info():
    """Return the active STT model name and path for diagnostics/logging."""
    return {
        "name": current_model_name,
        "path": model_path,
    }


def ensure_stt_model(model_name="vosk_medium"):
    """Ensure a specific STT model is loaded; returns active model name."""
    global current_model_name
    normalized = str(model_name or "").strip().lower().replace(" ", "_")
    if normalized and current_model_name != normalized:
        return set_stt_model_choice(normalized)
    return current_model_name


# Initialize with default model
if model is None:
    env_model = os.getenv("STT_MODEL")
    if env_model:
        set_stt_model_choice(env_model)
    else:
        set_stt_model_choice("vosk_small")


def callback(indata, frames, time, status):
    # reduce noisy status prints
    if status:
        pass
    q.put(bytes(indata))


def listen_and_transcribe(shutdown_flag):
    info = get_stt_model_info()
    audio_blocksize = _get_audio_blocksize()
    log_partials = _log_partials_enabled()
    early_partial = _early_partial_enabled()
    early_partial_min_chars = _get_early_partial_min_chars()
    early_partial_stable_hits = _get_early_partial_stable_hits()
    print(f"STT active model: {info['name']} ({info['path']})")
    print(f"STT audio blocksize: {audio_blocksize}")
    print(
        f"STT early partial fire: {early_partial} (min_chars={early_partial_min_chars}, stable_hits={early_partial_stable_hits})"
    )
    print("Listening...")
    rec = vosk.KaldiRecognizer(model, 16000)
    first_partial_time = None
    last_partial = ""
    partial_stable_count = 0

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
            blocksize=audio_blocksize,
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
                    final_time = time.time()
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        text = _dedupe_tail(text)
                        if text:
                            stt_endpoint_ms = None
                            first_partial_ts = first_partial_time
                            if first_partial_time is not None:
                                stt_endpoint_ms = (
                                    final_time - first_partial_time
                                ) * 1000
                            first_partial_time = None
                            yield {
                                "text": text,
                                "stt_first_partial_ts": first_partial_ts,
                                "stt_final_ts": final_time,
                                "stt_endpoint_ms": stt_endpoint_ms,
                                "stt_early_fire": False,
                            }
                    last_partial = ""
                    partial_stable_count = 0
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    # Print partials in real-time for live feedback
                    if partial:
                        if first_partial_time is None:
                            first_partial_time = time.time()

                        normalized_partial = str(partial).strip()
                        if normalized_partial == last_partial:
                            partial_stable_count += 1
                        else:
                            last_partial = normalized_partial
                            partial_stable_count = 1

                        if (
                            early_partial
                            and normalized_partial
                            and len(normalized_partial) >= early_partial_min_chars
                            and partial_stable_count >= early_partial_stable_hits
                        ):
                            early_time = time.time()
                            stt_endpoint_ms = None
                            if first_partial_time is not None:
                                stt_endpoint_ms = (
                                    early_time - first_partial_time
                                ) * 1000
                            yield {
                                "text": normalized_partial,
                                "stt_first_partial_ts": first_partial_time,
                                "stt_final_ts": early_time,
                                "stt_endpoint_ms": stt_endpoint_ms,
                                "stt_early_fire": True,
                            }
                            # Avoid repeatedly yielding the same stable partial.
                            last_partial = ""
                            partial_stable_count = 0
                            first_partial_time = None
                    else:
                        last_partial = ""
                        partial_stable_count = 0
                        first_partial_time = None

                    if log_partials and partial:
                        print(f"Partial: {partial}", end="\r")
    except Exception as e:
        print(f"Error in audio stream: {e}")
