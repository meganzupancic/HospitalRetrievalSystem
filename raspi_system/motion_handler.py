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

    wake_active = getattr(motion_callback, "wake_stream_active", None)
    pause_event = getattr(motion_callback, "pause_event", None)
    if wake_active is None or pause_event is None:
        return

    # Debounce: ignore triggers within 2 seconds
    if current_time - last_motion_time < 2.0:
        return

    last_motion_time = current_time
    motion_triggered = True

    try:
        print(f"🎯 Motion detected on GPIO {channel}!")
        # This will trigger the voice thread just like wake word.
        # The start command is still sent even if a voice session is already active.
        motion_callback.voice_trigger.set()
        motion_callback.wake_stream_active.clear()
        print("✅ Voice trigger set, wake stream cleared")

        # Send the same BLE start signal used by the wake-word path.
        try:
            ble_sender = getattr(motion_callback, "ble_sender", None)
            rack_provider = getattr(motion_callback, "rack_provider", None)

            if ble_sender is None or rack_provider is None:
                raise RuntimeError("BLE sender not configured")

            rack_numbers = rack_provider()
            for rack_num in rack_numbers:
                if ble_sender(rack_num, "wake_word_start"):
                    print(f"✅ 'start' sent for Arduino on Rack {rack_num}")
                else:
                    print(f"❌ 'start' failed for Arduino on Rack {rack_num}")

            print(f"Sent 'start' to {len(rack_numbers)} Arduino device(s)")
        except Exception as e:
            print(f"⚠️ Warning: Could not send start message (not critical): {e}")
    except Exception as e:
        print(f"❌ Error in motion callback: {e}")


def motion_listener(
    voice_trigger,
    shutdown_flag,
    pause_event,
    wake_stream_active,
    ble_sender=None,
    rack_provider=None,
):
    global motion_triggered
    print("🚀 Motion listener started.")
    # Attach shared objects to callback
    motion_callback.voice_trigger = voice_trigger
    motion_callback.wake_stream_active = wake_stream_active
    motion_callback.pause_event = pause_event
    motion_callback.ble_sender = ble_sender
    motion_callback.rack_provider = rack_provider

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
