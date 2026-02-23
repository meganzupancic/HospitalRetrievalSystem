# Configuration for multiple Arduino connections by rack
# Each rack has its own Arduino with different BLE address and name

ARDUINO_CONFIG = {
    # 1: {
    #     "name": "Nano33BLE-Rack1",  # Change to your actual Arduino names
    #     "address": "23:F1:16:6E:CB:9B",  # Change to actual BLE addresses
    #     "service_uuid": "12345678-1234-5678-1234-56789abcdef0",
    #     "char_uuid": "12345678-1234-5678-1234-56789abcdef1",
    # },
    # # 2: {
    # #     "name": "Nano33BLE-Rack2",
    # #     "address": "BB:79:DF:E2:3B:B8",
    # #     "service_uuid": "12345678-1234-5678-1234-56789abcdef0",
    # #     "char_uuid": "12345678-1234-5678-1234-56789abcdef1",
    # # },
    # 3: {
    #     "name": "Nano33BLE-Rack3",
    #     "address": "9A:13:C7:BB:2D:31",
    #     "service_uuid": "12345678-1234-5678-1234-56789abcdef0",
    #     "char_uuid": "12345678-1234-5678-1234-56789abcdef1",
    # },
    # 4: {
    #     "name": "Nano33BLE-Rack4",
    #     "address": "06:BA:6D:47:DB:69",
    #     "service_uuid": "12345678-1234-5678-1234-56789abcdef0",
    #     "char_uuid": "12345678-1234-5678-1234-56789abcdef1",
    # },
}


def get_arduino_config(rack_number):
    """Get Arduino configuration for a specific rack number.

    Args:
        rack_number: The rack number (1-4)

    Returns:
        Dictionary with Arduino config or None if invalid rack
    """
    return ARDUINO_CONFIG.get(rack_number)


def get_all_rack_numbers():
    """Get list of all configured rack numbers."""
    return sorted(list(ARDUINO_CONFIG.keys()))
