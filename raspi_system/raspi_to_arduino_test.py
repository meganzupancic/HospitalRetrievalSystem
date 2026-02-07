import asyncio

from bleak import BleakClient

ADDRESS = "8D:3E:F7:D1:4E:34"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"


async def main():
    print("Connecting...")
    async with BleakClient(ADDRESS) as client:
        print("Connected and ready")

        while True:
            input("Press ENTER to send signal...")
            await client.write_gatt_char(CHAR_UUID, b"1", response=False)
            print("Signal sent")


asyncio.run(main())
