import time

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(17, GPIO.IN)  # Replace 17 with your GPIO pin number

print("Monitoring motion sensor... Press Ctrl+C to stop.")
try:
    while True:
        if GPIO.input(17):
            print("Motion detected!")
        else:
            print("No motion")
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
