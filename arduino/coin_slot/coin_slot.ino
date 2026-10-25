// ---------------------------------------------------------------------------
// ECA Print - coin slot reader
// ---------------------------------------------------------------------------
// Hardware:
//   ALLAN 1299 coin selector  ->  signal wire to Arduino D2
//   Arduino UNO R3 (or Nano)  ->  USB to the PC running ECA Print
//
// What it does:
//   The coin slot sends a short electrical pulse for every peso it accepts.
//   This sketch counts those pulses and sends the count to the PC as one
//   line, for example:
//
//       5        <- a 5 peso coin (or 5 pulses from smaller coins)
//       20       <- a 20 peso coin
//
//   The app (core/coin_reader.py) reads those lines at 9600 baud and adds the
//   number to the customer's credit. It expects ONE number per line, so always
//   use Serial.println() and never Serial.print() alone.
// ---------------------------------------------------------------------------

// ----------------------------- settings -----------------------------------
const uint8_t  COIN_PIN     = 2;    // D2 = the coin slot signal wire
const uint8_t  DEBOUNCE_MS  = 25;   // ignore electrical noise inside a pulse
const uint8_t  MIN_PULSE_MS = 8;    // reject short static/contact spikes
const uint16_t MAX_PULSE_MS = 250;  // reject a signal held low by a touch
const uint16_t MAX_PULSES   = 50;   // safety cap per batch
const bool     DEBUG_ECHO   = true; // repeat anything typed in Serial Monitor

// --------------------------- internal state -------------------------------
volatile uint16_t pulseCount   = 0;
volatile uint32_t lastPulseMs  = 0;
volatile uint32_t pulseStartMs = 0;
volatile bool     pulseActive  = false;

// Runs on the falling edge of every electrical pulse from the coin slot.
void onPulse() {
  uint32_t now = millis();

  // Contact bounce: the same pulse often fires several times in a few ms.
  if (pulseActive || now - lastPulseMs < DEBOUNCE_MS) {
    return;
  }

  lastPulseMs  = now;
  pulseStartMs = now;
  pulseActive  = true;
}

void setup() {
  // INPUT_PULLUP: the coin slot normally pulls the line LOW when it pulses.
  pinMode(COIN_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), onPulse, FALLING);

  Serial.begin(9600);
  lastPulseMs = millis();
}

void loop() {
  bool     active;
  uint32_t start;

  noInterrupts();
  active = pulseActive;
  start  = pulseStartMs;
  interrupts();

  // A real coin pulse is LOW for 25-100 ms. Ignore very short static spikes
  // and a line that stays LOW because a coin is being held against the slot.
  if (active) {
    uint32_t width = millis() - start;
    if (digitalRead(COIN_PIN) == HIGH) {
      noInterrupts();
      pulseActive = false;
      if (width >= MIN_PULSE_MS && width <= MAX_PULSE_MS &&
          pulseCount < MAX_PULSES) {
        pulseCount++;
      }
      interrupts();
    } else if (width > MAX_PULSE_MS) {
      noInterrupts();
      pulseActive = false;
      interrupts();
    }
  }

  // Send each pulse batch immediately instead of waiting for a quiet gap.
  // The app adds every number it receives, so the balance counts up while
  // a 20-peso coin is still being scanned.
  uint16_t count;
  noInterrupts();
  count = pulseCount;
  pulseCount = 0;
  interrupts();

  if (count > 0) {
    Serial.println(count);   // one number per line, exactly what the app reads
  }

  // Debug helper: anything typed into the Serial Monitor is sent back out,
  // so you can test the PC side without dropping real coins.
  // Only works while ECA Print is CLOSED (one program per COM port).
  if (DEBUG_ECHO && Serial.available()) {
    while (Serial.available()) {
      Serial.write(Serial.read());
    }
  }
}

// ---------------------------------------------------------------------------
// If the counts are wrong, tune DEBOUNCE_MS
// ---------------------------------------------------------------------------
//  DEBOUNCE_MS  too HIGH -> real pulses are swallowed and a 5 peso coin adds
//                            only 2 or 3. Lower it, for example to 15.
//  DEBOUNCE_MS  too LOW  -> one pulse is counted twice and credit runs high.
//                            Raise it, for example to 35.
//
// Start with the value above and only change it if a test coin misreads.
// ---------------------------------------------------------------------------
// Testing without coins
// ---------------------------------------------------------------------------
//  1. Close ECA Print (it holds the COM port).
//  2. Open the Serial Monitor, set it to 9600 baud.
//  3. Type 5 and press Enter -> if the app were open, credit would go up by 5.
//
// Testing with real coins
// ---------------------------------------------------------------------------
//  1. Close the Serial Monitor, open ECA Print.
//  2. Drop one 1 peso coin. Credit should go up by 1.
//  3. Drop one 5 peso coin. Credit should go up by 5.
//  4. Drop one 10 peso coin. Credit should go up by 10.
//  5. Drop one 20 peso coin. Credit should go up by 20.
//
//  If a 5 peso coin only adds 1, the slot is set to "1 pulse per coin" and must
//  be reprogrammed to "1 pulse per peso" (DIP switches, or separate coin wires).
// ---------------------------------------------------------------------------
