# Raspberry Pi Deployment Guide

This guide walks you through deploying the Flask UI app to run on your Raspberry Pi 5, integrated with the existing raspi_system voice control.

## Overview

The system now uses **rack.db** (located in `raspi_system/database/`) as the single source of truth for both:
- The Flask web UI (rack grid interface)
- The voice control system (keyword matching)

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS installed
- SSH access to your Pi
- The `raspi_system` folder already working on the Pi
- Python 3.9+ installed on the Pi

## Step 1: Transfer Files to Raspberry Pi

From your local machine, SSH into your Raspberry Pi and transfer the necessary files. You have a few options:

### Option A: Using Git (Recommended)

```bash
# On your Raspberry Pi
cd ~
git clone https://github.com/meganzupancic/HospitalRetrievalSystem.git
cd HospitalRetrievalSystem
git checkout model-testing
```

### Option B: Using SCP (Manual File Transfer)

```bash
# On your local machine (PowerShell)
# Replace pi@raspberrypi.local with your Pi's username and hostname/IP
scp -r "c:\Users\megzu\OneDrive - University of Arizona\Hospital Retrieval System\*" pi@raspberrypi.local:~/HospitalRetrievalSystem/
```

### Files That Need to Be on the Pi:
- `app.py` - Main Flask application
- `db.py` - Database connection handler
- `models.sql` - Database schema
- `requirements.txt` - Python dependencies
- `socketio_instance.py` - SocketIO configuration (if using real-time features)
- `templates/` - HTML templates folder
- `static/` - CSS, JS, and assets folder
- `raspi_system/` - Already on your Pi, now updated with `rack_database_adapter.py`

## Step 2: Set Up Python Environment on Raspberry Pi

```bash
# SSH into your Raspberry Pi
ssh pi@raspberrypi.local

# Navigate to your project directory
cd ~/HospitalRetrievalSystem

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Initialize the Database

The rack.db database will be created in `raspi_system/database/`:

```bash
# Make sure you're in the project root directory
cd ~/HospitalRetrievalSystem

# Run the Flask app once to initialize the database
python3 -c "from db import init_db; init_db()"
```

This creates:
- `raspi_system/database/rack.db` with the rack/slot grid schema
- Default 4 racks (5 rows × 10 columns each)

## Step 4: Run the Flask App

### For Testing (Development Mode):

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the Flask app
python3 app.py
```

The app will be accessible at:
- From the Pi itself: `http://localhost:5000`
- From your computer: `http://raspberrypi.local:5000` (or use Pi's IP address)
- From your phone (same network): `http://192.168.x.x:5000` (use Pi's IP)

### To Find Your Pi's IP Address:

```bash
hostname -I
```

## Step 5: Run as Background Service (Production)

To keep the Flask app running even after you disconnect from SSH:

### Option A: Using tmux (Simple)

```bash
# Install tmux if not already installed
sudo apt install tmux

# Start a tmux session
tmux new -s flask_app

# In the tmux session, activate venv and run app
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 app.py

# Detach from tmux: Press Ctrl+B, then D
# To reattach later: tmux attach -t flask_app
```

### Option B: Using systemd (Recommended for Auto-start)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/hospital-retrieval-ui.service
```

Add this content:

```ini
[Unit]
Description=Hospital Retrieval System Flask UI
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/HospitalRetrievalSystem
Environment="PATH=/home/pi/HospitalRetrievalSystem/venv/bin"
ExecStart=/home/pi/HospitalRetrievalSystem/venv/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable hospital-retrieval-ui.service

# Start the service now
sudo systemctl start hospital-retrieval-ui.service

# Check the status
sudo systemctl status hospital-retrieval-ui.service

# View logs
sudo journalctl -u hospital-retrieval-ui.service -f
```

Service management commands:
```bash
sudo systemctl start hospital-retrieval-ui    # Start the service
sudo systemctl stop hospital-retrieval-ui     # Stop the service
sudo systemctl restart hospital-retrieval-ui  # Restart the service
sudo systemctl status hospital-retrieval-ui   # Check status
```

## Step 6: Using Both Systems Together

Now both systems work with the same `rack.db` database:

### Flask Web UI (Port 5000)
- Add/edit items on the rack grid
- Visual interface for managing inventory
- Access from any device on your network

### Voice Control (raspi_system)
- Say item names: "bandage", "gauze", "syringe"
- The system searches rack.db for matches (including tags and other_names)
- LED strips light up to show the item location

### Adding Items with Voice Recognition Support

When using the Flask UI to add items, include:
1. **Label**: The primary name (e.g., "Band-Aid")
2. **Tags**: Alternative terms (e.g., "bandage, adhesive")
3. **Other Names**: Brand names or variations (e.g., "band aid, plaster")

The voice system will match any of these terms!

## Step 7: Testing the Integration

1. **Add an item via the web UI:**
   - Go to `http://raspberrypi.local:5000`
   - Add an item with label "Syringe" and tags "needle, injection"
   - Place it in rack 1, slots 5-7

2. **Test voice recognition:**
   - Activate the wake word on your raspi_system
   - Say "Find needle"
   - The system should light up slots 5-7 on rack 1

## Troubleshooting

### Can't Access the Web UI

```bash
# Check if Flask is running
ps aux | grep python

# Check which port Flask is listening on
sudo netstat -tulpn | grep 5000

# Check firewall (usually not an issue on Pi OS)
sudo ufw status
```

### Database Permission Errors

```bash
# Make sure the database directory is writable
chmod 755 ~/HospitalRetrievalSystem/raspi_system/database/
chmod 644 ~/HospitalRetrievalSystem/raspi_system/database/rack.db
```

### Import Errors in raspi_system

```bash
# Make sure you're running from the project root
cd ~/HospitalRetrievalSystem

# Verify Python path includes the project
python3 -c "import sys; print(sys.path)"
```

### Voice System Not Finding Items

```bash
# Check the database has items
sqlite3 raspi_system/database/rack.db "SELECT * FROM items;"

# Test the adapter directly
python3 -c "from raspi_system.rack_database_adapter import load_database_from_sqlite; print(load_database_from_sqlite())"
```

## Port Configuration

- **Flask UI**: Port 5000 (HTTP)
- **WebSocket** (if using): Port 5000 (same as Flask)

To change the port, edit [app.py](app.py):
```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # Change port here
```

## Security Considerations

For production use on an open network:

1. **Add authentication** to the Flask app
2. **Use HTTPS** with a reverse proxy (nginx)
3. **Restrict access** by IP or use a VPN

For a home/lab network, the current setup is generally sufficient.

## Next Steps

- Configure your router to assign a static IP to the Pi
- Set up port forwarding if you want external access
- Add a domain name or use dynamic DNS
- Integrate with the existing medical_supplies.db if needed

## File Structure on Raspberry Pi

```
~/HospitalRetrievalSystem/
├── app.py                          # Flask web server
├── db.py                           # Database utilities
├── models.sql                      # Database schema
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── base.html
│   └── rack.html
├── static/                         # CSS, JS, images
│   ├── styles.css
│   ├── app.js
│   └── rack.js
└── raspi_system/
    ├── rack_database_adapter.py    # NEW: Adapter for rack.db
    ├── nlp_parser.py               # UPDATED: Uses rack.db
    ├── system_controller.py        # UPDATED: Uses rack.db
    ├── database_manager.py         # OLD: For medical_supplies.db (backup)
    └── database/
        ├── rack.db                 # Main database for both systems
        └── medical_supplies.db     # Legacy database (backup)
```

## Summary

✅ Flask UI runs on Raspberry Pi port 5000  
✅ Voice control uses the same rack.db database  
✅ Items can be added via web UI and found via voice  
✅ Tags and other_names support flexible voice matching  
✅ System can run as a background service  
✅ Accessible from any device on your network
