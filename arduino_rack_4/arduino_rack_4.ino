#include <Adafruit_NeoPixel.h>
#include <ArduinoBLE.h>
// ================= LED CONFIG =================
#define LED_PIN   6
#define LED_COUNT 400

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// ================= INDEX CONFIG =================
#define MAX_INDEXES 80
#define TOTAL_BITS 82
#define TOTAL_BYTES 11   // 26 bits fits in 4 bytes

const int MAX_PIXELS_PER_INDEX = (LED_COUNT / 80) * 2 + 2;

unsigned long indexTimer[MAX_INDEXES];
bool indexActive[MAX_INDEXES];
bool indexTimed[MAX_INDEXES];   // NEW: track whether this index should auto-timeout
int pixelRefs[LED_COUNT];

const unsigned long ON_DURATION = 5000;

// ================= BLE CONFIG =================
BLEService lightService("12345678-1234-5678-1234-56789abcdef0");

BLECharacteristic lightChar(
  "12345678-1234-5678-1234-56789abcdef1",
  BLEWrite,
  TOTAL_BYTES
);

// ============================================================
// ===================== STARTUP SHOW ==========================
// ============================================================

void startupShow() {
    const int total = LED_COUNT;
    const int sparkleCount = LED_COUNT * 0.30;  // ~20% sparkle
    const int minDelay = 1;                     // twinkle speed
    const int maxDelay = 5;
    const int fadeStep = 5;                     // how fast LEDs dim each iteration

    uint8_t brightness[LED_COUNT] = {0};        // track per-pixel brightness
    bool used[LED_COUNT] = {false};

    // Start with everything OFF
    for (int i = 0; i < total; i++) {
        strip.setPixelColor(i, 0);
    }
    strip.show();

    int litCount = 0;

    // TWINKLE LOOP: random LEDs turn on, previous ones fade
    while (litCount < sparkleCount) {

        // ---- TWINKLE ONE RANDOM LED ----
        int p = random(0, total);

        if (!used[p]) {
            used[p] = true;
            litCount++;

            brightness[p] = 255;   // new LED pops on full-white
        }

        // ---- DIM ALL CURRENTLY-LIT PIXELS ----
        for (int i = 0; i < total; i++) {
            if (brightness[i] > 0) {

                // dim toward black
                if (brightness[i] > fadeStep) 
                    brightness[i] -= fadeStep;
                else 
                    brightness[i] = 0;

                strip.setPixelColor(i, brightness[i], brightness[i], brightness[i]);
            }
        }

        strip.show();
        delay(random(minDelay, maxDelay));
    }

    // ---- FINAL FADE OUT EVERYTHING ----
    bool stillLit = true;

    while (stillLit) {
        stillLit = false;

        for (int i = 0; i < total; i++) {
            if (brightness[i] > 0) {
                stillLit = true;

                if (brightness[i] > fadeStep)
                    brightness[i] -= fadeStep;
                else
                    brightness[i] = 0;

                strip.setPixelColor(i, brightness[i], brightness[i], brightness[i]);
            }
        }

        strip.show();
        delay(10);
    }

    // Ensure total blackout
    for (int i = 0; i < total; i++) strip.setPixelColor(i, 0);
    strip.show();
}

// ============================================================

int getPixelsForIndex(int indexzero, int outPixels[]) {
  int index = indexzero - 1;
  int count = 0;

  for (int i = 0; i < (LED_COUNT / 80); i++) {

    if (index < 20)
      outPixels[count++] = LED_COUNT - (index * LED_COUNT / 80) - i;

    else if (index < 40) {
      outPixels[count++] = (LED_COUNT - (index - 20) * LED_COUNT / 80) - i;
      outPixels[count++] = (LED_COUNT/2) + (index - 20) * LED_COUNT/80 + i;
    }

    else if (index < 60) {
      outPixels[count++] = (LED_COUNT/2) + (index - 40) * LED_COUNT/80 + i;
      outPixels[count++] = (LED_COUNT/2) - ((index - 40) * LED_COUNT/80) - i;
    }

    else {
      outPixels[count++] = (LED_COUNT/2) - ((index - 60) * LED_COUNT/80) - i;
      outPixels[count++] = (index - 60) * LED_COUNT/80 + i;
    }
  }

  return count;
}

// ============================================================

void activateIndex(int idx, bool timedMode) {   // CHANGED: timedMode parameter

  int pixels[MAX_PIXELS_PER_INDEX];
  int count = getPixelsForIndex(idx, pixels);

  for (int i = 0; i < count; i++) {
    int p = pixels[i];
    if (p >= 0 && p < LED_COUNT) {
      pixelRefs[p]++;
      strip.setPixelColor(p, strip.Color(255,0,0));
    }
  }

  indexActive[idx - 1] = true;
  indexTimed[idx - 1] = timedMode;              // NEW
  indexTimer[idx - 1] = millis();
  strip.show();
}

void deactivateIndex(int idx) {
  Serial.print("IDX OFF ");
  Serial.println(idx);

  int pixels[MAX_PIXELS_PER_INDEX];
  int count = getPixelsForIndex(idx, pixels);

  for (int i = 0; i < count; i++) {
    int p = pixels[i];
    if (p >= 0 && p < LED_COUNT) {
      pixelRefs[p]--;
      if (pixelRefs[p] <= 0) {
        pixelRefs[p] = 0;
        strip.setPixelColor(p, 0);
      }
    }
  }

  indexActive[idx - 1] = false;
  indexTimed[idx - 1] = false;                  // NEW
  strip.show();
}

// ============================================================
// =================== BIT UNPACK ==============================
// ============================================================

void processPacket(uint8_t *data) {

  // NEW: bit 80 => timed mode flag
  bool timedMode = (data[10] & 0x01);

  // ----- START BIT (bit 81) -----
  // Keeping your original check exactly:
  Serial.print(data[10]);
  if (data[10] == 2) {
    Serial.println("START BIT");
    startupShow();
  }

  // ----- INDEX BITS -----
  for (int bit = 0; bit < MAX_INDEXES; bit++) {

    int byteIndex = bit / 8;
    int bitIndex  = bit % 8;

    bool on = (data[byteIndex] >> bitIndex) & 0x01;

    if (on) {
      if (!indexActive[bit]) {
        activateIndex(bit + 1, timedMode);      // CHANGED
      } else {
        // NEW: refresh mode/timer for already-active indexes
        indexTimed[bit] = timedMode;
        indexTimer[bit] = millis();
      }
    } else {
      // NEW: in persistent mode packets, zero bits mean "turn off this index"
      if (!timedMode && indexActive[bit]) {
        deactivateIndex(bit + 1);
      }
    }
  }
}

// ============================================================
// ========================= SETUP =============================
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(1500);

  strip.begin();
  strip.show();

  for (int i = 0; i < MAX_INDEXES; i++) {
    indexActive[i] = false;
    indexTimed[i] = false;    // NEW
    indexTimer[i] = 0;
  }
  for (int i = 0; i < LED_COUNT; i++) pixelRefs[i] = 0;

  if (!BLE.begin()) {
    Serial.println("BLE FAIL");
    while (1);
  }

  BLE.setLocalName("Nano33BLE-Rack4");
  BLE.setDeviceName("Nano33BLE-Rack4");

  BLE.setAdvertisedService(lightService);
  lightService.addCharacteristic(lightChar);
  BLE.addService(lightService);

  BLE.advertise();
  Serial.println("READY");
}

// ============================================================
// ========================== LOOP =============================
// ============================================================

void loop() {

  BLE.poll();
  BLEDevice central = BLE.central();

  if (central) {
    Serial.println("CONNECTED");

    while (central.connected()) {
      BLE.poll();

      if (lightChar.written()) {

        uint8_t buffer[TOTAL_BYTES];
        lightChar.readValue(buffer, TOTAL_BYTES);

        Serial.print("RAW: ");
        for (int i = 0; i < TOTAL_BYTES; i++) {
          Serial.print(buffer[i], HEX);
          Serial.print(" ");
        }
        Serial.println();

        processPacket(buffer);
      }

      unsigned long now = millis();
      for (int i = 0; i < MAX_INDEXES; i++) {
        // CHANGED: timeout applies only to timed indexes
        if (indexActive[i] && indexTimed[i] && (now - indexTimer[i] >= ON_DURATION)) {
          deactivateIndex(i + 1);
        }
      }
    }

    Serial.println("DISCONNECTED");
  }
}