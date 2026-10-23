// ---------------------------------------------------------------------------
// Print Vendo - coin slot reader
// ---------------------------------------------------------------------------
// Hardware:
//   ALLAN 1299 coin selector  ->  signal wire to Arduino D2
//   Arduino UNO R3 (or Nano)  ->  USB to the PC running Print Vendo
//
// What it does:
//   The coin slot sends a short electrical pulse for every peso it accepts.
//   This sketch counts those pulses, waits for a short quiet gap, then sends
//   the peso value to the PC as one line, for example:
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
const uint16_t GAP_MS       = 500;  // quiet time that means "the coin is done"
const uint8_t  DEBOUNCE_MS  = 15;   // ignore electrical noise inside a pulse
const uint16_t MAX_PULSES   = 50;   // safety cap, so a stuck wire cannot run away
const bool     DEBUG_ECHO   = true; // repeat anything typed in Serial Monitor

// --------------------------- internal state -------------------------------
volatile uint16_t pulseCount   = 0;
volatile uint32_t lastPulseMs  = 0;
volatile bool     counting     = false;

// Runs on every electrical pulse from the coin slot.
void onPulse() {
  uint32_t now = millis();

  // Contact bounce: the same pulse often fires several times in a few ms.
  if (now - lastPulseMs < DEBOUNCE_MS) {
    return;
  }

  if (pulseCount < MAX_PULSES) {
    pulseCount++;
  }
  lastPulseMs = now;
  counting    = true;
}

void setup() {
  // INPUT_PULLUP: the coin slot normally pulls the line LOW when it pulses.
  pinMode(COIN_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), onPulse, FALLING);

  Serial.begin(9600);
  lastPulseMs = millis();
}

void loop() {
  uint16_t count;
  bool     done;

  // Read the shared values with interrupts paused, so a pulse cannot arrive
  // halfway through and give us a broken number.
  noInterrupts();
  done  = counting && (millis() - lastPulseMs >= GAP_MS);
  count = pulseCount;
  if (done) {
    pulseCount = 0;
    counting   = false;
  }
  interrupts();

  if (done && count > 0) {
    Serial.println(count);   // one number per line, exactly what the app reads
  }

  // Debug helper: anything typed into the Serial Monitor is sent back out,
  // so you can test the PC side without dropping real coins.
  // Only works while Print Vendo is CLOSED (one program per COM port).
  if (DEBUG_ECHO && Serial.available()) {
    while (Serial.available()) {
      Serial.write(Serial.read());
    }
  }
}

// ---------------------------------------------------------------------------
// If the counts are wrong, tune these TWO numbers
// ---------------------------------------------------------------------------
//  DEBOUNCE_MS  too HIGH -> real pulses are swallowed and a 5 peso coin adds
//                            only 2 or 3. Lower it, for example to 8.
//  DEBOUNCE_MS  too LOW  -> one pulse is counted twice and credit runs high.
//                            Raise it, for example to 25.
//  GAP_MS       too LOW  -> one coin is split into two lines (harmless, the
//                            values simply add up), but a slow slot may send
//                            half a coin at a time. Raise it, for example to 800.
//
// Start with the values above and only change them if a test coin misreads.
// ---------------------------------------------------------------------------
// Testing without coins
// ---------------------------------------------------------------------------
//  1. Close Print Vendo (it holds the COM port).
//  2. Open the Serial Monitor, set it to 9600 baud.
//  3. Type 5 and press Enter -> if the app were open, credit would go up by 5.
//
// Testing with real coins
// ---------------------------------------------------------------------------
//  1. Close the Serial Monitor, open Print Vendo.
//  2. Drop one 1 peso coin. Credit should go up by 1.
//  3. Drop one 5 peso coin. Credit should go up by 5.
//  4. Drop one 10 peso coin. Credit should go up by 10.
//  5. Drop one 20 peso coin. Credit should go up by 20.
//
//  If a 5 peso coin only adds 1, the slot is set to "1 pulse per coin" and must
//  be reprogrammed to "1 pulse per peso" (DIP switches, or separate coin wires).
// ---------------------------------------------------------------------------
