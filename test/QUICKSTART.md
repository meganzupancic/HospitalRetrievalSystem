# 🎤 Whisper Test System - Getting Started Guide

## What You Have

A complete testing framework for evaluating OpenAI's Whisper speech-to-text model with real-world accuracy testing against a medical supply database.

## Files in `/test` Folder

| File | Purpose |
|------|---------|
| `whisper_test.py` | Main application - audio recording, transcription, and keyword matching |
| `test_ui.html` | Web dashboard - visual representation of racks and real-time detection |
| `medical_supplies_expanded.json` | Database of 40 medical items with rack/location info |
| `run_test.bat` / `run_test.py` | Quick start scripts to launch the application |
| `config.json` | Configuration settings (model, thresholds, server settings) |
| `requirements.txt` | Python dependencies |
| `README.md` | Complete documentation |

## Quick Start (2 Minutes)

### Option 1: Batch File (Windows)
```bash
cd test
run_test.bat
```

### Option 2: Python Script
```bash
cd test
python run_test.py
```

### Option 3: Manual
```bash
cd test
python whisper_test.py
```

## What Happens When You Run It

1. **Startup (10-20 seconds)**
   - Loads Whisper base model (~140MB)
   - Loads 40 medical keywords
   - Starts Flask web server

2. **Console Output**
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

3. **Web Dashboard** (Open http://127.0.0.1:5000)
   - Shows transcription in real-time
   - Displays matched item and confidence score
   - Visualizes 4 racks with 10 slots each
   - Lights up the correct slot when item is detected
   - Shows list of all matches with confidence scores

## How It Works

### Audio Pipeline
```
🎤 Microphone
  ↓
📝 Whisper Transcription (base model - highest quality)
  ↓
🔍 Fuzzy Keyword Matching (80% confidence threshold)
  ↓
💡 Visual Feedback (UI lights up the correct slot)
  ↓
📊 Results Saved (test_results.json)
```

### The 4 Racks System
```
┌─────────────────────────────────────────────┐
│        4 Racks × 10 Locations Each          │
├──────────────────────────────────────────────┤
│  Rack 1 │ Rack 2 │ Rack 3 │ Rack 4        │
│  ━━━━━  │ ━━━━━  │ ━━━━━  │ ━━━━━        │
│  [1][2] │ [1][2] │ [1][2] │ [1][2]       │
│  [3][4] │ [3][4] │ [3][4] │ [3][4]       │
│  [5][6] │ [5][6] │ [5][6] │ [5][6]       │
│  [7][8] │ [7][8] │ [7][8] │ [7][8]       │
│  [9][10]│ [9][10]│ [9][10]│ [9][10]      │
└──────────────────────────────────────────────┘
```

When you say "band aids", slot 1 in Rack 1 lights up! ✨

## The 40 Medical Items

Organized across 4 racks:

**Rack 1 (10 items)**
- Band aids, Gauze pads, Antiseptic wipes, Latex gloves, Thermometer, Saline solution, Eye wash, Aspirin, Antibiotic powder, Finger splint

**Rack 2 (10 items)**
- Alcohol swabs, Medical tape, Syringes, Face masks, Scissors, Antihistamine, Antacid, Antidiarrheal, Sterile gauze, Ankle wrap

**Rack 3 (10 items)**
- Tweezers, Elastic bandage, Comfort pack, Pain reliever, Anti nausea, Decongestant, Cough syrup, Laxative, Wound closure strips, Knee brace

**Rack 4 (10 items)**
- Hydrocortisone cream, Antibiotic ointment, Burn gel, Cold pack, Heating pad, Ibuprofen, Acetaminophen, Digestive enzyme, Triangular bandage, Wrist support

## Testing Workflow

### Basic Test Session

1. **Start Application**
   ```bash
   cd test
   python whisper_test.py
   ```

2. **Wait for Console Prompt**
   ```
   TEST #1
   🎤 Recording for 5 seconds... (speak now)
   ```

3. **Speak Test Phrase**
   - Say one of the medical items clearly
   - Example: "bandages" or "gauze pads" or "acetaminophen"

4. **See Results**
   - Console shows transcription
   - Web dashboard lights up the correct slot
   - Confidence score displayed
   - All matches listed

5. **Continue or Quit**
   - Press Enter for next test
   - Type 'q' to quit testing

### Example Test Session

```
TEST #1: "I need band aids"
✓ Match: "band aids" at Rack 1, Location 1 (92% confidence)

TEST #2: "Give me some gauze"
✓ Match: "gauze pads" at Rack 1, Location 2 (87% confidence)

TEST #3: "Thermometer please"
✓ Match: "thermometer" at Rack 1, Location 5 (95% confidence)

TEST #4: "Can I get the scissors"
✓ Match: "scissors" at Rack 2, Location 5 (89% confidence)
```

## Understanding Confidence Scores

```
90-100%  ✓ Perfect match
80-89%   ✓ Good match
70-79%   ⚠ Acceptable (increase threshold to be stricter)
<70%     ✗ No match recommended
```

Factors affecting score:
- **Whisper transcription accuracy** - How well it recognizes speech
- **Fuzzy matching distance** - How close the words are
- **Audio quality** - Clear speech = higher scores

## Configuration Guide

Edit `config.json` to customize behavior:

```json
{
  "whisper": {
    "model": "base"  // Change to "tiny", "small", "medium", "large"
  },
  "audio": {
    "record_duration": 5  // Shorter = faster; longer = more audio context
  },
  "matching": {
    "confidence_threshold": 80  // Higher = stricter matching
  }
}
```

### Model Size Tradeoffs

| Model | Quality | Speed | Size |
|-------|---------|-------|------|
| tiny | ⭐ Poor | ⚡ Fast | 39MB |
| base | ⭐⭐⭐⭐ Excellent | Normal | 140MB |
| small | ⭐⭐⭐ Good | Slow | 466MB |
| medium | ⭐⭐⭐⭐⭐ Best | Very Slow | 1.5GB |

**Recommended:** Use `"base"` (default) - best balance of quality and speed

## Output Results

After the test ends, check `test_results.json`:

```json
[
  {
    "test_number": 1,
    "timestamp": "2026-02-25T10:30:00",
    "transcription": "I need band aids",
    "matched_item": "band aids",
    "matches_found": 1
  },
  {
    "test_number": 2,
    "timestamp": "2026-02-25T10:35:00",
    "transcription": "Can I get gauze pads",
    "matched_item": "gauze pads",
    "matches_found": 1
  }
]
```

## Troubleshooting

### Microphone Not Working
```bash
# Check available microphones
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Whisper Model Download Issues
- First run requires ~140MB download
- Cached in: `C:\Users\{username}\.cache\whisper\`
- Models auto-download if missing

### Low Accuracy
1. **Speak more clearly** - Slow, distinct pronunciation
2. **Reduce background noise** - Find quiet room
3. **Adjust threshold** - Lower `confidence_threshold` in config
4. **Use longer recording** - Increase `record_duration` for more context

### Web Dashboard Not Loading
- Check console output for errors
- Ensure port 5000 is not in use
- Try `http://localhost:5000` instead of `http://127.0.0.1:5000`
- Clear browser cache (Ctrl+Shift+Delete)

## Advanced Features

### Custom Keyword Database
Edit `medical_supplies_expanded.json`:
```json
{
  "item": "your item name",
  "rack": 1,
  "location": 1
}
```
Restart application to load new items.

### Batch Testing
Create a test script:
```python
test_phrases = [
    "I need band aids",
    "Give me gauze pads",
    "Can I have a thermometer"
]
# Add to whisper_test.py for automation
```

### Real-time Accuracy Monitoring
Check `test_results.json` after each test:
- Sum of successful matches / total tests = accuracy percentage
- Average confidence for successful matches
- Common mismatch patterns

## FAQ

**Q: Can I use a different model?**
A: Yes! Change `"model": "base"` to `"tiny"`, `"small"`, `"medium"`, or `"large"` in config.json

**Q: How do I add more items?**
A: Edit `medical_supplies_expanded.json` and add more objects to the `medical_supplies` array

**Q: Can I test from a file instead of microphone?**
A: Modify `whisper_test.py` to load from file instead of recording (advanced usage)

**Q: What's the difference between Rack and Location?**
A: Rack = which of 4 racks (1-4); Location = which slot within that rack (1-10)

**Q: Can I change the recording time?**
A: Yes, in `config.json` change `"record_duration"` field

## Performance Tips

1. **Faster turnaround:** Use `"tiny"` model (less accurate but 10x faster)
2. **Better accuracy:** Use `"base"` model (default, recommended)
3. **Maximum accuracy:** Use `"medium"` model (slower, better results on complex audio)
4. **Quieter environment:** Higher confidence scores with less background noise
5. **Clear speech:** Slower, distinct speaking = better transcription

## Next Steps

1. ✅ Run `python whisper_test.py`
2. ✅ Open http://127.0.0.1:5000 in browser
3. ✅ Speak test phrases and see results light up
4. ✅ Check `test_results.json` for accuracy metrics
5. ✅ Adjust settings in `config.json` as needed

Happy testing! 🚀
