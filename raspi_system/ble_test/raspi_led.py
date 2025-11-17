import asyncio
from bleak import BleakClient

DEVICE_ADDRESS = "C6:10:17:BD:9F:7F"  # your Nordic_LBS MAC
LBS_LED_CHAR_UUID = "00001525-1212-efde-1523-785feabcd123"

async def main():
    client = BleakClient(DEVICE_ADDRESS)
    try:
        print("Connecting...")
        await client.connect()
        print("Connected!")

        while True:
            user_input = input("Enter 1 to turn LED ON, 0 to turn LED OFF, q to quit: ")
            if user_input == "1":
                await client.write_gatt_char(LBS_LED_CHAR_UUID, bytearray([0x01]), response=True)
                print("LED ON")
            elif user_input == "0":
                await client.write_gatt_char(LBS_LED_CHAR_UUID, bytearray([0x00]), response=True)
                print("LED OFF")
            elif user_input.lower() == "q":
                break
            else:
                print("Invalid input, use 1, 0, or q.")
    finally:
        try:
            await client.disconnect()
            print("Disconnected.")
        except Exception as e:
            print(f"Disconnect error ignored: {e}")


asyncio.run(main())
