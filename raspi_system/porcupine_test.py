import pvporcupine

ACCESS_KEY = "u6opFld4V3f6QBSDvUfOP/KFgrojdVzI8H4JghtWNONoxVgqG/kAxQ=="

try:
    print("Initializing Porcupine...")
    porcupine = pvporcupine.create(access_key=ACCESS_KEY, keywords=["porcupine"])
    print("Porcupine initialized successfully!")
except Exception as e:
    print(f"Error: {e}")
