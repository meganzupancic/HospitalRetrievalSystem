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

        def setwarnings(self, flag):
            pass

        def setmode(self, mode):
            pass

        def setup(self, pin, mode):
            pass

        def input(self, pin):
            return 0  # Mock: always return no motion

        def cleanup(self):
            pass

    GPIO = MockGPIO()

GPIO.setwarnings(False)  # Disable warnings
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
PIR_PIN = 17  # Match the pin in motion_handler.py
GPIO.setup(PIR_PIN, GPIO.IN)  # Set up as input

print(f"🎯 Motion Sensor Test - Monitoring GPIO pin {PIR_PIN}")
print("=" * 50)
print("Move in front of the PIR sensor to test...")
print("Press Ctrl+C to stop.")
print("=" * 50)

motion_count = 0
last_state = GPIO.input(PIR_PIN)
print(f"Initial state: {'HIGH (motion)' if last_state else 'LOW (no motion)'}")

try:
    while True:
        current_state = GPIO.input(PIR_PIN)

        # Detect state change
        if current_state != last_state:
            if current_state:
                motion_count += 1
                print(
                    f"🚨 Motion detected! (Count: {motion_count}) - {time.strftime('%H:%M:%S')}"
                )
            else:
                print(f"✅ Motion cleared - {time.strftime('%H:%M:%S')}")
            last_state = current_state

        time.sleep(0.1)  # Check every 100ms

except KeyboardInterrupt:
    print(f"\n{'=' * 50}")
    print(f"Test complete. Total motion detections: {motion_count}")
    GPIO.cleanup()
    print("GPIO cleaned up. Goodbye!")
