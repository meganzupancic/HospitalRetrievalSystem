#!/bin/bash
# Quick start script for Hospital Retrieval System on Raspberry Pi

echo "======================================"
echo "  Hospital Retrieval System Launcher"
echo "======================================"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Initialize database if it doesn't exist
if [ ! -f "raspi_system/database/rack.db" ]; then
    echo "Initializing rack.db database..."
    python3 -c "from db import init_db; init_db()"
    echo "✅ Database initialized"
    echo ""
fi

# Show menu
echo "Choose what to run:"
echo "  1) Flask Web UI (port 5000)"
echo "  2) Voice Control System (raspi_system)"
echo "  3) Both (Flask UI + Voice Control)"
echo "  4) Migrate data from medical_supplies.db"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Starting Flask Web UI..."
        echo "Access at: http://$(hostname -I | awk '{print $1}'):5000"
        echo "Press Ctrl+C to stop"
        echo ""
        python3 app.py
        ;;
    2)
        echo ""
        echo "Starting Voice Control System..."
        echo "Press Ctrl+C to stop"
        echo ""
        python3 -m raspi_system.system_controller
        ;;
    3)
        echo ""
        echo "Starting both systems..."
        echo "Flask UI: http://$(hostname -I | awk '{print $1}'):5000"
        echo "Press Ctrl+C to stop both"
        echo ""
        # Run Flask in background
        python3 app.py &
        FLASK_PID=$!
        
        # Run voice control in foreground
        python3 -m raspi_system.system_controller
        
        # When voice control stops, kill Flask too
        kill $FLASK_PID 2>/dev/null
        ;;
    4)
        echo ""
        echo "Running migration script..."
        python3 migrate_medical_supplies_to_rack.py
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Shutdown complete."
