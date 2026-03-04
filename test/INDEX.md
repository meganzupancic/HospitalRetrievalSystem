# Whisper Test System - Complete Documentation

## 📦 What's Included

A complete, production-ready Whisper audio testing framework with:
- **Real-time transcription** using OpenAI's Whisper
- **Intelligent keyword matching** against 40 medical items
- **Interactive web dashboard** with visual rack/slot system
- **Comprehensive testing tools** and result analysis
- **Easy configuration** via JSON settings

## 📂 Directory Structure

```
test/
├── whisper_test.py                 # ⭐ MAIN APPLICATION
├── test_ui.html                    # Web dashboard (open in browser)
├── medical_supplies_expanded.json   # Database of 40 medical items
├── config.json                     # Configuration settings
├── run_test.bat                    # Windows batch launcher
├── run_test.py                     # Python launcher (cross-platform)
├── requirements.txt                # Python dependencies
├── advanced_examples.py            # Advanced testing examples
├── README.md                       # Full documentation
├── QUICKSTART.md                   # Quick start guide (read this first!)
└── test_results.json              # Generated after each test run
```

## 🚀 Getting Started (3 Steps)

### Step 1: Ensure Prerequisites
- Python virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`

### Step 2: Run the Application
```bash
cd test
python whisper_test.py
```

Or use launcher:
```bash
cd test
run_test.bat              # Windows
python run_test.py        # Any platform
```

### Step 3: Open Web Dashboard
At the same time, open browser: **http://127.0.0.1:5000**

## 📊 Quick Overview

### Core Files

**whisper_test.py** (Main Application)
- Records audio from microphone (5 seconds default)
- Uses Whisper base model for transcription
- Matches transcription against 40 medical keywords
- Sends results to web dashboard via WebSocket
- Saves results to JSON file
- Features:
  - Fuzzy matching with 80% confidence threshold
  - Real-time accuracy reporting
  - Interactive console interface

**test_ui.html** (Web Dashboard)
- Beautiful, responsive design
- Shows 4 racks × 10 slots each (physical layout)
- Displays transcription + matched item
- Shows confidence score with visual bar
- Lights up the correct slot when item detected
- Lists all keyword matches with confidence
- Real-time updates via WebSocket

**medical_supplies_expanded.json** (Database)
- 40 medical items total
- Distributed across 4 racks
- 10 locations per rack
- Easy to customize

### Configuration Files

**config.json**
```json
{
  "whisper": {"model": "base"},         // Model size
  "audio": {"record_duration": 5},      // Recording time
  "matching": {"confidence_threshold": 80},  // Match strictness
  "server": {"host": "127.0.0.1", "port": 5000}
}
```

Easily adjust audio length, model, and matching sensitivity!

### Output

**test_results.json** (Generated after test)
```json
[
  {
    "test_number": 1,
    "timestamp": "2026-02-25T10:30:00",
    "transcription": "I need some band aids",
    "matched_item": "band aids",
    "matches_found": 1
  }
]
```

## 🎯 Use Cases

### Use Case 1: Basic Accuracy Testing
```
Run: python whisper_test.py
1. Speak test phrase
2. See transcription in console + web UI
3. Check confidence score
4. Results saved automatically
```

### Use Case 2: Batch Testing Multiple Phrases
See `advanced_examples.py` for batch_test_with_phrases() function

### Use Case 3: Compare Whisper Models
Test the same audio with tiny/base/small/medium models to compare quality vs speed

### Use Case 4: Analyze Results
Generate detailed reports and accuracy metrics from test results

## 🎤 The Testing Process

```
START
  ↓
🎤 Record 5 seconds of audio
  ↓
📝 Transcribe using Whisper base
  ↓
🔍 Match keywords with 80% confidence
  ↓
✨ Light up slot in web UI
  ↓
💾 Save results to JSON
  ↓
Continue or Quit?
  ↓
END → test_results.json saved
```

## 📈 System Architecture

```
┌─────────────────────────┐
│   Microphone Input      │
└────────────┬────────────┘
             ↓
┌─────────────────────────────────────┐
│  Audio Recording (sounddevice)      │
│  Sample Rate: 16000 Hz              │
│  Duration: 5 seconds (configurable) │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│  Whisper Transcription              │
│  Model: base (140MB)                │
│  Language: English                  │
│  Output: Text string                │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│  Fuzzy Keyword Matching             │
│  Algorithm: token_set_ratio         │
│  Threshold: 80% confidence          │
│  Database: 40 medical items         │
└────────────┬────────────────────────┘
             ↓
            /  \
           /    \
          /      \
    Match?    No Match?
      ↓          ↓
   ✓Found    ✗Nothing
      ↓          ↓
   Light up   Clear UI
   Slot
      ↓          ↓
      └────┬─────┘
           ↓
   ┌──────────────────┐
   │ Send to Web UI   │
   │ (WebSocket)      │
   └────────┬─────────┘
            ↓
   ┌──────────────────┐
   │ Console Output   │
   │ + JSON Save      │
   └────────┬─────────┘
            ↓
   ┌──────────────────┐
   │ Next Test or Exit│
   └──────────────────┘
```

## 🔧 Configuration Options

### Whisper Model Selection
```json
"model": "tiny"     // 39MB - Fast, lower quality
"model": "base"     // 140MB - Recommended! (default)
"model": "small"    // 466MB - Better quality, slower
"model": "medium"   // 1.5GB - Best quality, very slow
```

### Audio Settings
```json
"record_duration": 3    // Short: faster testing
"record_duration": 5    // Default: good balance
"record_duration": 10   // Long: more audio context
```

### Matching Sensitivity
```json
"confidence_threshold": 70  // Loose: catches more variations
"confidence_threshold": 80  // Balanced (recommended)
"confidence_threshold": 90  // Strict: only high confidence matches
```

## 📊 understanding Output

### In Console
```
TEST #1
🎤 Recording for 5 seconds... (speak now)
✓ Recording complete
📝 Transcribing...
Transcription: "I need some band aids"
✓ Found 1 match(es):
  [1] 'band aids' → 'band aids' (92% confidence)
       📍 Rack 1, Location 1
```

### In Web UI
- **Transcription box:** Shows what was said
- **Item display:** Shows matched item in big colored box
- **Confidence bar:** Visual representation of confidence %
- **Stat boxes:** Confidence % and Rack/Location
- **Matches list:** All possible matches ranked by confidence
- **Rack system:** 4 physical racks displayed with 10 slots each
- **Lighting:** Correct slot lights up when item matched

### In test_results.json
```json
{
  "test_number": 1,
  "timestamp": "2026-02-25T14:30:45.123456",
  "transcription": "I need some band aids",
  "matched_item": "band aids",
  "matches_found": 1
}
```

## 🎯 Expected Accuracy

### Whisper Base Model (default)
- **Clear speech:** 95%+ transcription accuracy
- **Normal speech:** 85-90% transcription accuracy
- **Unclear speech:** 70-80% transcription accuracy

### Keyword Matching (80% threshold)
- **Perfect match:** ~95% confidence
- **Good match:** ~85-90% confidence
- **Partial match:** ~75-85% confidence
- **No match:** <75% confidence

### Overall System
- Expect 80-90% detection accuracy with clear speech
- Varies based on:
  - Audio quality (microphone, background noise)
  - Pronunciation clarity
  - Accent similarity to training data
  - Item similarity (e.g., "gauze" vs "gauze pads")

## 🛠️ Troubleshooting Quick Ref

| Problem | Solution |
|---------|----------|
| Microphone not detected | Check connection, run `sounddevice` test |
| Low transcription accuracy | Speak clearer, reduce background noise |
| Keywords not matching | Lower confidence_threshold in config.json |
| Model download stuck | Check internet, clear cache `~\.cache\whisper\` |
| Web UI not loading | Ensure port 5000 free, check console for errors |
| Results not saving | Ensure write permissions in test/ folder |

## 📚 File Descriptions

| File | Purpose | Key Features |
|------|---------|--------------|
| `whisper_test.py` | Main application engine | Recording, transcription, matching, server |
| `test_ui.html` | Web dashboard | Real-time visualization, rack system |
| `medical_supplies_expanded.json` | Item database | 40 items, 4 racks, easy to edit |
| `config.json` | Settings | Model, audio, matching, server config |
| `run_test.bat` / `run_test.py` | Launchers | One-click startup |
| `advanced_examples.py` | Reference code | Batch testing, file testing, analysis |
| `README.md` | Full documentation | Detailed guide, all features explained |
| `QUICKSTART.md` | Quick reference | Fast setup, common tasks |

## 🚀 Next Steps

1. **Read:** [QUICKSTART.md](QUICKSTART.md) (5 min read)
2. **Setup:** Run `python whisper_test.py`
3. **Test:** Speak phrases and see results
4. **Configure:** Edit `config.json` if needed
5. **Analyze:** Check `test_results.json` for metrics
6. **Advanced:** Use `advanced_examples.py` for custom testing

## 📞 Support

For common issues, check:
1. Console error messages
2. [README.md](README.md) Troubleshooting section
3. [QUICKSTART.md](QUICKSTART.md) FAQ section
4. `advanced_examples.py` for testing variations

## ✨ Features Summary

✅ Real-time audio recording from microphone
✅ OpenAI Whisper transcription (base model)
✅ Fuzzy keyword matching (40 medical items)
✅ Interactive web dashboard with lighting effects
✅ 4-rack × 10-slot physical visualization
✅ Confidence scoring and matching details
✅ WebSocket real-time communication
✅ JSON results logging and analysis
✅ Configurable thresholds and settings
✅ Advanced testing examples included
✅ Cross-platform compatible (Windows/Mac/Linux)
✅ Easy to customize and extend

## 🎓 Learning Path

**Beginner:** 
- Read QUICKSTART.md
- Run whisper_test.py
- Use web UI to see results

**Intermediate:**
- Adjust config.json settings
- Run batch tests with advanced_examples.py
- Analyze test_results.json

**Advanced:**
- Modify whisper_test.py for custom behavior
- Integrate with other systems
- Deploy to multiple machines
- Create custom test pipelines

---

**Created:** February 2026
**Status:** Production Ready
**Last Updated:** 2026-02-25
