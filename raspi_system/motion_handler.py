# Monitors motion sensors and triggers wake logic

# motion_handler.py
import time

import RPi.GPIO as GPIO

# Setup GPIO
PIR_PIN = 17  # GPIO17

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

motion_triggered = False


def motion_callback(channel):
    global motion_triggered
    if not motion_triggered:
        motion_triggered = True
        print("Motion detected!")
        # This will trigger the voice thread just like wake word
        motion_callback.voice_trigger.set()
        motion_callback.wake_stream_active.clear()


def motion_listener(voice_trigger, shutdown_flag, pause_event, wake_stream_active):
    print("Motion listener started.")
    # Attach shared objects to callback
    motion_callback.voice_trigger = voice_trigger
    motion_callback.wake_stream_active = wake_stream_active

    # Register event detection (rising edge = motion)
    GPIO.add_event_detect(
        PIR_PIN, GPIO.RISING, callback=motion_callback, bouncetime=2000
    )

    try:
        while not shutdown_flag.is_set():
            if pause_event.is_set():
                time.sleep(1)  # paused mode
            else:
                time.sleep(0.1)  # idle loop
            if wake_stream_active.is_set():
                global motion_triggered
                motion_triggered = False  # reset for next detection
    finally:
        GPIO.cleanup()
