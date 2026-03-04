# Raspberry Pi SSH Quick Reference

## Connect to Your Pi

```bash
# Replace with your Pi's hostname or IP address
ssh pi@raspberrypi.local

# Or using IP address
ssh pi@192.168.1.xxx
```

Default password is usually `raspberry` (change it for security!)

## Transfer Files to Pi

### Transfer entire project folder
```powershell
# From Windows PowerShell (your local machine)
scp -r "c:\Users\megzu\OneDrive - University of Arizona\Hospital Retrieval System" pi@raspberrypi.local:~/
```

### Transfer specific files
```powershell
scp "c:\Users\megzu\OneDrive - University of Arizona\Hospital Retrieval System\app.py" pi@raspberrypi.local:~/HospitalRetrievalSystem/
```

### Using Git (Recommended)
```bash
# On your Pi
cd ~
git clone https://github.com/meganzupancic/HospitalRetrievalSystem.git
cd HospitalRetrievalSystem
git checkout model-testing
```

## One-Time Setup on Pi

```bash
# Navigate to project
cd ~/HospitalRetrievalSystem

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 -c "from db import init_db; init_db()"

# Make startup script executable
chmod +x start_raspi.sh
```

## Running the System

### Interactive Launcher
```bash
cd ~/HospitalRetrievalSystem
./start_raspi.sh
```

### Manual Commands

#### Flask UI Only
```bash
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 app.py
```

#### Voice Control Only
```bash
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 -m raspi_system.system_controller
```

#### Background Mode with tmux
```bash
# Start tmux session
tmux new -s hospital

# Run app
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 app.py

# Detach from tmux: Ctrl+B, then D
# Reattach later: tmux attach -t hospital
```

## Systemd Service Commands

```bash
# Start the service
sudo systemctl start hospital-retrieval-ui

# Stop the service
sudo systemctl stop hospital-retrieval-ui

# Restart the service
sudo systemctl restart hospital-retrieval-ui

# Check status
sudo systemctl status hospital-retrieval-ui

# Enable auto-start on boot
sudo systemctl enable hospital-retrieval-ui

# Disable auto-start
sudo systemctl disable hospital-retrieval-ui

# View logs (live)
sudo journalctl -u hospital-retrieval-ui -f

# View recent logs
sudo journalctl -u hospital-retrieval-ui -n 50
```

## Useful Pi Commands

### Find Pi's IP Address
```bash
hostname -I
```

### Check if Flask is Running
```bash
ps aux | grep python
```

### Check Port 5000
```bash
sudo netstat -tulpn | grep 5000
```

### Check Database
```bash
cd ~/HospitalRetrievalSystem
sqlite3 raspi_system/database/rack.db "SELECT COUNT(*) FROM items;"
```

### View Database Contents
```bash
sqlite3 raspi_system/database/rack.db ".tables"
sqlite3 raspi_system/database/rack.db "SELECT * FROM items LIMIT 10;"
```

### Check Disk Space
```bash
df -h
```

### Check Python Version
```bash
python3 --version
```

### Update System
```bash
sudo apt update
sudo apt upgrade -y
```

## Troubleshooting

### Permission Denied for Database
```bash
cd ~/HospitalRetrievalSystem
chmod 755 raspi_system/database/
chmod 644 raspi_system/database/*.db
```

### Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill the process (replace PID with actual process ID)
kill -9 PID
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
cd ~/HospitalRetrievalSystem
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Python Module Not Found
```bash
# Make sure you're in project root and venv is activated
cd ~/HospitalRetrievalSystem
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Accessing the Web UI

Once Flask is running on your Pi:

- **From the Pi itself**: http://localhost:5000
- **From your computer**: http://raspberrypi.local:5000
- **From your phone**: http://192.168.x.x:5000 (use Pi's IP)

### Find Your Pi's IP
```bash
hostname -I | awk '{print $1}'
```

## File Editing on Pi

### Using nano (beginner-friendly)
```bash
nano filename.py
# Ctrl+O to save, Ctrl+X to exit
```

### Using vim (advanced)
```bash
vim filename.py
# Press 'i' to insert, 'Esc' then ':wq' to save and exit
```

## Safety Tips

### Backup Database
```bash
cp raspi_system/database/rack.db raspi_system/database/rack.db.backup
```

### Safe Shutdown
```bash
sudo shutdown -h now
```

### Safe Reboot
```bash
sudo reboot
```

## Common Workflows

### Update Code from Git
```bash
cd ~/HospitalRetrievalSystem
git pull origin model-testing
sudo systemctl restart hospital-retrieval-ui
```

### Check Logs After Change
```bash
sudo journalctl -u hospital-retrieval-ui -f
```

### Test Without Service
```bash
# Stop the service first
sudo systemctl stop hospital-retrieval-ui

# Run manually to see errors
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 app.py

# When done, restart service
sudo systemctl start hospital-retrieval-ui
```

## Network Access from Windows

To access your Pi's UI from your Windows machine:

1. Open browser
2. Go to: `http://raspberrypi.local:5000`
3. Or use IP: `http://192.168.x.x:5000`

## Testing Voice Integration

```bash
# Terminal 1: Run Flask UI
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 app.py

# Terminal 2: Run voice control (in new tmux pane or SSH session)
cd ~/HospitalRetrievalSystem
source venv/bin/activate
python3 -m raspi_system.system_controller
```

---

**Save this file for quick reference when working with your Raspberry Pi!**
