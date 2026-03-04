"""
Test Whisper via command-line interface
"""

import subprocess
import sounddevice as sd
import numpy as np
import os
import tempfile

print("Testing Whisper CLI...")

# Record audio
print("\n[MIC] Recording 3 seconds...")
audio = sd.rec(int(16000 * 3), samplerate=16000, channels=1, dtype=np.float32)
sd.wait()
print("[OK] Recording complete")

# Save to WAV
temp_file = os.path.join(tempfile.gettempdir(), "test_audio.wav")
import soundfile as sf
sf.write(temp_file, audio, 16000)
print(f"[OK] Saved to {temp_file}")

# Try Whisper CLI
try:
    result = subprocess.run(
        ["whisper", temp_file, "--model", "base", "--output_format", "json", "--output_dir", tempfile.gettempdir()],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print(f"\n[OK] Whisper CLI ran successfully")
    print(f"Return code: {result.returncode}")
    
    # Read the JSON result
    json_file = os.path.join(tempfile.gettempdir(), "test_audio.json")
    if os.path.exists(json_file):
        import json
        with open(json_file) as f:
            data = json.load(f)
        print(f"Transcription: {data.get('text', 'ERROR')}")
    else:
        print("No JSON output found")
        
except Exception as e:
    print(f"[ERROR] {e}")

# Clean up
try:
    os.remove(temp_file)
    os.remove(os.path.join(tempfile.gettempdir(), "test_audio.json"))
except:
    pass

print("\n[OK] Test complete")
