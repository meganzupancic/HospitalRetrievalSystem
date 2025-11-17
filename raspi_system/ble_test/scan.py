import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for BLE devices...")

    def detection_callback(device, advertisement_data):
        print(
            f"Device: {device.name}, "
            f"Address: {device.address}, "
            f"RSSI: {advertisement_data.rssi}"
        )

    scanner = BleakScanner(detection_callback)
    await scanner.start()
    await asyncio.sleep(5.0)  # scan for 5 seconds
    await scanner.stop()

asyncio.run(main())
