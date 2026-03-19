# Monitors motion sensors and triggers wake logic

# motion_handler.py
import time

# Try to import RPi.GPIO, but allow testing on Windows without it
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available (Windows/dev environment)")

    # Create a mock GPIO object for non-Raspberry Pi environments
    class MockGPIO:
        BCM = 11  # Mock constant
        IN = 1  # Mock constant
        RISING = 1  # Mock constant

        def setwarnings(self, flag):
            pass

        def setmode(self, mode):
            pass

        def setup(self, pin, mode):
            pass

        def add_event_detect(self, pin, edge, callback=None, bouncetime=None):
            pass

        def remove_event_detect(self, pin):
            pass

        def cleanup(self):
            pass

    GPIO = MockGPIO()

# Setup GPIO
PIR_PIN = 17  # GPIO17

GPIO.setwarnings(False)  # Disable warnings if GPIO already in use
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

motion_triggered = False
last_motion_time = 0


def motion_callback(channel):
    global motion_triggered, last_motion_time
    current_time = time.time()

    # Match wake-word behavior: ignore motion while voice session is active.
    wake_active = getattr(motion_callback, "wake_stream_active", None)
    pause_event = getattr(motion_callback, "pause_event", None)
    if wake_active is None or pause_event is None:
        return
    if (not wake_active.is_set()) or pause_event.is_set():
        return

    # Debounce: ignore triggers within 2 seconds
    if current_time - last_motion_time < 2.0:
        return

    last_motion_time = current_time
    motion_triggered = True

    try:
        print(f"🎯 Motion detected on GPIO {channel}!")
        # This will trigger the voice thread just like wake word
        motion_callback.voice_trigger.set()
        motion_callback.wake_stream_active.clear()
        print("✅ Voice trigger set, wake stream cleared")

        # Send a "start" message to the PC to indicate activity (non-blocking)
        try:
            import socket

            HOST = "172.20.10.6"
            PORT = 5050
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((HOST, PORT))
                s.sendall(b"start")
            print(f"📡 Sent 'start' to {HOST}:{PORT}")
        except Exception as e:
            print(f"⚠️ Warning: Could not send start message (not critical): {e}")
    except Exception as e:
        print(f"❌ Error in motion callback: {e}")


def motion_listener(voice_trigger, shutdown_flag, pause_event, wake_stream_active):
    global motion_triggered
    print("🚀 Motion listener started.")
    # Attach shared objects to callback
    motion_callback.voice_trigger = voice_trigger
    motion_callback.wake_stream_active = wake_stream_active
    motion_callback.pause_event = pause_event

    # Register event detection (rising edge = motion)
    try:
        GPIO.add_event_detect(
            PIR_PIN, GPIO.RISING, callback=motion_callback, bouncetime=2000
        )
        print(f"✅ GPIO event detection registered on pin {PIR_PIN}")
    except Exception as e:
        print(f"❌ Failed to register GPIO event detection: {e}")
        return

    try:
        print("👀 Monitoring for motion...")
        while not shutdown_flag.is_set():
            if pause_event.is_set():
                time.sleep(1)  # paused mode
            else:
                time.sleep(0.1)  # idle loop

            # Reset motion_triggered after wake_stream becomes active again
            if wake_stream_active.is_set() and motion_triggered:
                motion_triggered = False  # reset for next detection
                print("🔄 Motion sensor ready for next trigger")
    except KeyboardInterrupt:
        print("⚠️ Motion listener interrupted")
    except Exception as e:
        print(f"❌ Error in motion listener: {e}")
    finally:
        try:
            GPIO.remove_event_detect(PIR_PIN)
            print("🛑 GPIO event detection removed")
        except:
            pass
        GPIO.cleanup()
        print("🧹 GPIO cleanup complete")
