# Raspberry Pi Integration - Changes Summary

## What Changed

Your Hospital Retrieval System now uses a **unified database system** where both the Flask web UI and the voice control system work with the same `rack.db` database.

### New Files Created

1. **`raspi_system/rack_database_adapter.py`**
   - Adapter that makes `rack.db` compatible with the voice control system
   - Provides the same interface as `database_manager.py` but for the rack/slot grid
   - Supports searching by item labels, tags, and other_names
   - Marks items as "called" when requested via voice

2. **`RASPBERRY_PI_DEPLOYMENT.md`**
   - Comprehensive deployment guide for setting up on Raspberry Pi 5
   - Step-by-step instructions for SSH setup, file transfer, and service configuration
   - Troubleshooting tips and security considerations

3. **`migrate_medical_supplies_to_rack.py`**
   - Migration script to transfer data from old `medical_supplies.db` to new `rack.db`
   - Creates backups before migration
   - Maps old location numbers to rack/slot positions

4. **`start_raspi.sh`**
   - Quick launcher script for Raspberry Pi
   - Interactive menu to start Flask UI, voice control, or both
   - Handles virtual environment activation automatically

### Modified Files

1. **`db.py`**
   - Updated to create `rack.db` in `raspi_system/database/` folder
   - Added `isCalled` column to items table (tracks voice-requested items)
   - Smart path detection for local dev vs Raspberry Pi deployment

2. **`raspi_system/nlp_parser.py`**
   - Changed import from `database_manager` to `rack_database_adapter`
   - No other changes needed - interface is compatible

3. **`raspi_system/system_controller.py`**
   - Changed import from `database_manager` to `rack_database_adapter`
   - Now loads from `rack.db` instead of `medical_supplies.db`

## How the Integration Works

### Database Schema Mapping

| Old (medical_supplies.db) | New (rack.db) |
|---------------------------|---------------|
| `medical_supplies.item` | `items.label` + `items.tags` + `items.other_names` |
| `medical_supplies.rack` | `racks.id` |
| `medical_supplies.location` | `rack_slots.id` (calculated from row/col) |
| `medical_supplies.isCalled` | `items.isCalled` |

### Voice Search Enhancement

The voice control now searches across multiple fields:
- **Primary label**: "Band-Aid"
- **Tags**: "bandage", "adhesive"  
- **Other names**: "band aid", "plaster"

When you say any of these words, the system finds the item!

### Example Workflow

1. **Via Web UI** (http://raspberrypi.local:5000):
   - Add item: "Gauze Pad"
   - Tags: "gauze, bandage, dressing"
   - Place in: Rack 1, Slots 15-17

2. **Via Voice**:
   - Wake word: "Hey Hospital" (or your configured wake word)
   - Say: "Find dressing"
   - System lights up slots 15-17 on Rack 1

3. **Database**:
   - `items` table has one entry for "Gauze Pad"
   - `item_slots` links it to slots 15, 16, 17
   - `isCalled` flag set to 1 when voice-activated

## File Structure After Changes

```
HospitalRetrievalSystem/
├── app.py                             # Flask web UI
├── db.py                              # ✏️ MODIFIED: Smart DB path detection
├── models.sql                         # Database schema
├── requirements.txt                   # Python dependencies
│
├── RASPBERRY_PI_DEPLOYMENT.md         # 🆕 NEW: Deployment guide
├── migrate_medical_supplies_to_rack.py # 🆕 NEW: Data migration tool
├── start_raspi.sh                     # 🆕 NEW: Quick launcher
│
├── templates/                         # HTML templates
├── static/                            # CSS, JS, icons
│
└── raspi_system/
    ├── rack_database_adapter.py       # 🆕 NEW: Rack DB adapter
    ├── nlp_parser.py                  # ✏️ MODIFIED: Uses rack adapter
    ├── system_controller.py           # ✏️ MODIFIED: Uses rack adapter
    │
    ├── database_manager.py            # ⚠️ OLD: Keep for backup
    │
    ├── speech_to_text.py              # Unchanged
    ├── vosk_wake_word.py              # Unchanged
    ├── motion_handler.py              # Unchanged
    ├── arduino_config.py              # Unchanged
    │
    └── database/
        ├── rack.db                    # 🆕 NEW: Unified database
        └── medical_supplies.db        # ⚠️ OLD: Backup only
```

## Next Steps

### 1. Test Locally (Optional)
Before deploying to Pi, you can test locally:

```powershell
# In your current directory
python app.py
# Visit http://localhost:5000
```

### 2. Deploy to Raspberry Pi

Follow the guide in [RASPBERRY_PI_DEPLOYMENT.md](RASPBERRY_PI_DEPLOYMENT.md):

```bash
# SSH to your Pi
ssh pi@raspberrypi.local

# Clone or copy the updated code
cd ~/HospitalRetrievalSystem
git pull origin model-testing

# Run the setup
source venv/bin/activate
pip install -r requirements.txt
python3 -c "from db import init_db; init_db()"

# Start the system
./start_raspi.sh
```

### 3. Migrate Existing Data (If Needed)

If you have items in `medical_supplies.db`:

```bash
python3 migrate_medical_supplies_to_rack.py
```

### 4. Run as Service

For auto-start on boot, set up systemd service (see deployment guide).

## Benefits of This Integration

✅ **Single Source of Truth**: One database for both web UI and voice control  
✅ **Better Search**: Voice matches labels, tags, and alternative names  
✅ **Visual + Voice**: Manage via web interface, search via voice  
✅ **Network Accessible**: Access UI from phone, tablet, or computer  
✅ **Flexible Layout**: Grid-based rack system with multi-slot items  
✅ **Easy Deployment**: All tools and guides included

## Backward Compatibility

- Old `database_manager.py` is preserved in case you need it
- Old `medical_supplies.db` remains unchanged
- Migration script creates backups before any changes

## Questions?

See the troubleshooting section in [RASPBERRY_PI_DEPLOYMENT.md](RASPBERRY_PI_DEPLOYMENT.md) or check that the following work:

1. **Database exists**: `raspi_system/database/rack.db`
2. **Flask runs**: `python3 app.py` (accessible at port 5000)
3. **Adapter works**: `python3 -c "from raspi_system.rack_database_adapter import load_database_from_sqlite; print(load_database_from_sqlite())"`

---

**Status**: ✅ Ready for Raspberry Pi deployment!
