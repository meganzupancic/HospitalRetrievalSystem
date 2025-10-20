# Unit tests for all modules

# test_suite.py

# from system_controller import run_transcriber
import signal
import time

from system_controller import run_system, shutdown_flag


def signal_handler(sig, frame):
    print("Shutting down system...")
    shutdown_flag.set()
    # Do NOT call sys.exit(0) here — let threads exit naturally


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    run_system()
    print("System running. Press Ctrl+C to exit.")
    try:
        while not shutdown_flag.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down system...")
        shutdown_flag.set()
