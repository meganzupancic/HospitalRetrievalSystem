#!/usr/bin/env python3
"""Test suite for Hospital Retrieval System

This runs the full system with:
- Motion detection
- Wake word detection  
- Voice recognition
- BLE communication to Arduino racks
- Database lookup from rack.db

IMPORTANT: Must run with sudo for GPIO access:
    sudo $(which python3) test_suite.py
"""

import signal
import sys
import time

print("✅ Starting imports...")

# Check if running as root (needed for GPIO)
import os
if os.geteuid() != 0:
    print("\n❌ ERROR: This script needs GPIO access.")
    print("Please run with sudo:")
    print("    sudo $(which python3) test_suite.py")
    print("    OR")
    print("    sudo /path/to/venv/bin/python3 test_suite.py\n")
    sys.exit(1)

import RPi.GPIO as GPIO

try:
    from system_controller import run_system, shutdown_flag
    print("✅ system_controller imported successfully")
    print("✅ Using rack.db database for voice recognition")
except Exception as e:
    print(f"❌ Error importing system_controller: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def signal_handler(sig, frame):
    print("\n\n🛑 Shutting down system...")
    shutdown_flag.set()
    time.sleep(2)  # Give threads time to exit
    GPIO.cleanup()
    print("✅ System shut down cleanly.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Hospital Retrieval System - Full System Test")
    print("="*60)
    print("\nStarting all subsystems:")
    print("  - Motion detection")
    print("  - Wake word listener")
    print("  - Voice recognition (rack.db)")
    print("  - BLE communication")
    print("\nPress Ctrl+C to exit.\n")
    
    try:
        run_system()
        
        # Keep main thread alive
        while not shutdown_flag.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Keyboard interrupt received...")
        shutdown_flag.set()
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ Error running system: {e}")
        import traceback
        traceback.print_exc()
        shutdown_flag.set()
    finally:
        GPIO.cleanup()
        print("\n✅ Cleanup complete.")
