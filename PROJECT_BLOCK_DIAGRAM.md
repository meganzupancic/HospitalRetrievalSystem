# Project Block Diagram

This is a simple high-level flow of the project structure, excluding the wake word and motion sensor paths.

```mermaid
flowchart LR
    User[User] --> Web[Flask Web UI]
    Web --> App[app.py]
    App --> DB[(db.py / SQLite rack.db)]
    DB --> App
    App --> Logs[System logs and rack views]

    Voice[Voice command input] --> STT[speech_to_text.py]
    STT --> NLP[nlp_parser.py]
    NLP --> Adapter[rack_database_adapter.py]
    Adapter --> DB
    Adapter --> System[system_controller.py]
    System --> BLE[BLE communication / Arduino payload]
    BLE --> Arduino[arduino_rack_4.ino]
    Arduino --> Rack[Physical rack slots]
```

## Short Flow Summary

1. The Flask app serves the UI and reads/writes rack data from SQLite.
2. Voice commands go through speech-to-text, then NLP parsing.
3. The parsed request looks up inventory/location data in the database.
4. The controller converts the result into BLE payloads for the Arduino rack.
5. The Arduino updates the physical rack slots.

