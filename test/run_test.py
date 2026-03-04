#!/usr/bin/env python3
"""
Quick start script for Whisper Test System
Activates venv and launches the test application
"""

import os
import platform
import subprocess
import sys


def main():
    print("=" * 60)
    print("  WHISPER SPEECH TEST SYSTEM - QUICK START")
    print("=" * 60)
    print()

    # Get parent directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(test_dir)

    # Check if venv exists
    venv_dir = os.path.join(project_dir, "venv")
    if not os.path.exists(venv_dir):
        print("ERROR: Virtual environment not found!")
        print("Please ensure you have activated the virtual environment first.")
        if platform.system() == "Windows":
            print("Run: .\\venv\\Scripts\\Activate.ps1")
        else:
            print("Run: source venv/bin/activate")
        sys.exit(1)

    # Determine Python executable based on OS
    if platform.system() == "Windows":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(python_exe):
        print("ERROR: Python executable not found in virtual environment")
        sys.exit(1)

    print("✓ Virtual environment found")
    print()
    print("Starting test application...")
    print("=" * 60)
    print()
    print("🌐 After startup, navigate to: http://127.0.0.1:5000")
    print()
    print("Instructions:")
    print("  1. The script will show numbered tests")
    print("  2. After 'Recording...' prompt, speak your test phrase")
    print("  3. Press Enter after each test to continue")
    print("  4. Type 'q' to quit")
    print()
    print("=" * 60)
    print()

    # Change to test directory and run
    os.chdir(test_dir)

    # Run the test
    result = subprocess.run([python_exe, "whisper_test.py"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
