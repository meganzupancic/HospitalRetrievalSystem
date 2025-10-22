# Monitors motion sensors and triggers wake logic

# motion_handler.py
import time


def motion_listener(trigger_event, shutdown_flag, pause_event, ui):
    print("Motion thread started.")
    sleep_time = 30
    elapsed = 0

    while not shutdown_flag.is_set():
        if not pause_event.is_set():
            time.sleep(sleep_time)
            elapsed += 1
            if elapsed >= sleep_time:
                ui.log("Motion detected!", tag="green")
                trigger_event.set()
                elapsed = 0
        else:
            time.sleep(1)  # Sleep briefly when paused to avoid busy waiting
            elapsed = 0
