# Whisper Speech Test System

A comprehensive testing framework for OpenAI's Whisper speech-to-text model with medical keyword detection and visual feedback system.

## Features

- 🎤 **Real-time Audio Recording** - Capture audio from your microphone
- 🤖 **Advanced Transcription** - Uses Whisper Base model (highest quality available)
- 🔍 **Fuzzy Keyword Matching** - Intelligent matching against 40 medical keywords
- 💾 **Medical Supply Database** - 40 common hospital items with rack/location tracking
- 🎨 **Interactive UI** - Visual representation of 4 racks with 10 slots each
- 💡 **Lighting System** - Slots light up when items are detected
- 📊 **Accuracy Testing** - Console output and results logging for testing validation
- 📈 **Real-time Web Dashboard** - Live updates via WebSocket connection

## System Architecture

### Components

1. **whisper_test.py** - Main application
   - Audio recording and transcription
   - Keyword matching with fuzzy logic
   - Flask/SocketIO server for web UI
   - Test cycle management

2. **test_ui.html** - Web-based dashboard
   - 4-rack physical system visualization
   - Real-time detection results
   - Confidence scoring and location display
   - Interactive slot highlighting

3. **medical_supplies_expanded.json** - Database
   - 40 medical items
   - Rack and location assignments
   - Product lookup

## Setup Instructions

### Prerequisites

Ensure these dependencies are already in your main `requirements.txt`:
- Flask==3.1.2
- Flask-SocketIO==5.5.1
- openai-whisper
- sounddevice==0.5.3
- rapidfuzz
- numpy==2.0.2

### Installation

1. **Ensure your Python environment is activated:**
   ```bash
   cd "Hospital Retrieval System"
   .\venv\Scripts\Activate.ps1
   ```

2. **Install any missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Navigate to test folder:**
   ```bash
   cd test
   ```

## Running the Test

### Start the Application

```bash
python whisper_test.py
```

### What You'll See

**Console Output:**
```
============================================================
WHISPER ACCURACY TEST - MEDICAL KEYWORD DETECTION
============================================================

Configuration:
  Model: Whisper base
  Sample Rate: 16000 Hz
  Recording Duration: 5 seconds
  Confidence Threshold: 80%
  Keywords Loaded: 40

🌐 Web UI available at: http://127.0.0.1:5000

Starting audio test in console mode...

============================================================
TEST #1
============================================================

🎤 Recording for 5 seconds... (speak now)
✓ Recording complete

📝 Transcribing...
Transcription: "I need some gauze pads please"

✓ Found 1 match(es):
  [1] 'gauze pads' → 'gauze pads' (95% confidence)
       📍 Rack 1, Location 2

Press Enter to record another test (or 'q' to quit):
```

**Web Dashboard:**
- Open `http://127.0.0.1:5000` in your browser
- See real-time transcription and detection results
- Watch the rack system light up when items are detected
- View confidence scores and all matching results

## Medical Supplies Database

40 items organized across 4 racks with 10 locations each:

### Sample Items:
- **Rack 1:** Band aids, Gauze pads, Antiseptic wipes, Latex gloves, Thermometer, etc.
- **Rack 2:** Alcohol swabs, Medical tape, Syringes, Face masks, Scissors, etc.
- **Rack 3:** Tweezers, Elastic bandage, Comfort pack, Pain reliever, Anti nausea, etc.
- **Rack 4:** Hydrocortisone cream, Antibiotic ointment, Burn gel, Cold pack, Heating pad, etc.

## Testing Workflow

### Recommended Testing Process

1. **Warm-up Test** (1-2 tests)
   - Speak clearly with natural voice
   - Say simple phrases like "bandages" or "gauze pads"

2. **Accuracy Testing** (20-30 tests)
   - Vary speaking speed and tone
   - Test different accents/pronunciations
   - Test multi-word items
   - Test partial phrases

3. **Challenge Tests** (10-15 tests)
   - Background noise
   - Whispered speech
   - Fast/slurred speech
   - Similar-sounding items

### Success Criteria

- **Transcription Accuracy:** > 90% for clear speech
- **Keyword Match Accuracy:** > 85% for matching database items
- **Confidence Scores:** Looking for matches > 80% confidence

## Output Files

### test_results.json

Generated after each test run, contains:
```json
[
  {
    "test_number": 1,
    "timestamp": "2026-02-25T10:30:00.000000",
    "transcription": "I need gauze pads",
    "matched_item": "gauze pads",
    "matches_found": 1
  }
]
```

## Configuration Options

You can modify these settings in `whisper_test.py`:

```python
WHISPER_MODEL = "base"          # Model size (base is highest quality)
SAMPLE_RATE = 16000             # Audio recording rate (Hz)
RECORD_DURATION = 5             # Recording length (seconds)
CONFIDENCE_THRESHOLD = 80       # Fuzzy match threshold (%)
```

## Troubleshooting

### Issue: "No input devices found"
**Solution:** Check your microphone connection. Run:
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Issue: Whisper model not found
**Solution:** Model will auto-download on first run. Requires internet connection.
- Download size: ~141MB for base model
- Models cached in: `~/.cache/whisper/`

### Issue: Low accuracy
**Suggestions:**
- Speak more clearly
- Reduce background noise
- Increase `RECORD_DURATION` for more audio context
- Lower `CONFIDENCE_THRESHOLD` if matches are missing

### Issue: Web UI not connecting
**Solution:** Ensure Flask server is running (check console output). 
Try: `http://localhost:5000` instead of `http://127.0.0.1:5000`

## Accuracy Metrics

The system generates several accuracy measurements:

1. **Transcription Accuracy** - How well Whisper transcribes audio
2. **Keyword Matching Accuracy** - How well fuzzy matching finds keywords
3. **False Positive Rate** - Non-matching audio detected as items
4. **False Negative Rate** - Medical items not detected
5. **Average Confidence Score** - Mean confidence of successful matches

## Performance Notes

- **Model Loading:** ~10-15 seconds on first run
- **Per-Test Processing:** ~3-5 seconds (recording 5 seconds, transcription ~1-2 seconds)
- **Web UI Updates:** Real-time via WebSocket (<100ms latency)

## Advanced Usage

### Custom Keyword Database

Edit `medical_supplies_expanded.json` to add/remove items:

```json
{
  "medical_supplies": [
    { "item": "your item name", "rack": 1, "location": 1 },
    ...
  ]
}
```

Then restart the application.

### Adjusting Fuzzy Matching

The matching algorithm uses token_set_ratio from rapidfuzz:
- Higher threshold = stricter matching (fewer false positives)
- Lower threshold = looser matching (catch more variations)

### Recording Custom Audio Files

Modify the test script to use pre-recorded `speech_to_text.py`:
```python
# Instead of recording live
audio_data = load_audio_file("sample.wav")
result = transcriber.transcribe(audio_data)
```

## License

Part of Hospital Retrieval System project

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review console output for error messages
3. Check `test_results.json` for historical data
