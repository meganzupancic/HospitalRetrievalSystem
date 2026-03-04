"""
Debug script to test individual components
"""

import numpy as np
import sounddevice as sd
import whisper
import json

print("=" * 60)
print("WHISPER TEST - DEBUG MODE")
print("=" * 60)

# Test 1: Audio Recording
print("\n[1] Testing Audio Recording...")
print("Recording 3 seconds of audio (speak now)...")
try:
    audio_data = sd.rec(int(16000 * 3), samplerate=16000, channels=1, dtype=np.float32)
    sd.wait()
    print(f"   ✓ Recording successful")
    print(f"   - Audio shape: {audio_data.shape}")
    print(f"   - Max value: {np.max(np.abs(audio_data)):.4f}")
    print(f"   - Is silent (max < 0.01)? {np.max(np.abs(audio_data)) < 0.01}")
    
    if np.max(np.abs(audio_data)) < 0.01:
        print("   ⚠️  WARNING: Audio seems to be silent. Check microphone!")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Whisper Model Load
print("\n[2] Testing Whisper Model Loading...")
try:
    print("   Loading model... (this may take 10-20 seconds)")
    model = whisper.load_model("base")
    print(f"   ✓ Model loaded successfully")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Database Loading
print("\n[3] Testing Database Loading...")
try:
    with open("medical_supplies_expanded.json", "r") as f:
        data = json.load(f)
    print(f"   ✓ Database loaded successfully")
    print(f"   - Items: {len(data['medical_supplies'])}")
    print(f"   - Sample item: {data['medical_supplies'][0]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Flask/SocketIO
print("\n[4] Testing Flask/SocketIO...")
try:
    from flask import Flask
    from flask_socketio import SocketIO
    app = Flask(__name__)
    socketio = SocketIO(app)
    print(f"   ✓ Flask and SocketIO imported successfully")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("DEBUG TEST COMPLETE")
print("=" * 60)
print("\nIf all tests passed, the issue is in the main script logic.")
print("If any test failed, that's the component to fix.")
