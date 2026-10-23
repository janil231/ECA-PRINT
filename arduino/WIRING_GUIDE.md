# ECA Print - Coin Slot Wiring Guide

A one-page guide for building and testing the coin payment part.

---

## Parts you need

| Part | Purpose |
| --- | --- |
| ALLAN 1299 coin selector | Accepts the coins and sends pulses |
| Arduino UNO R3 (or Nano) | Counts the pulses and talks to the PC |
| 12V 1A or 2A DC adapter | Powers the coin selector |
| 4x male-to-female jumper wires | Connections |
| Locked coin box | Collects the coins |

---

## The connections

| From | To | Wire colour in most 1299 units |
| --- | --- | --- |
| 12V adapter **+** | Coin slot **12V / red** | red |
| 12V adapter **-** | Coin slot **GND / black** | black |
| Coin slot **COIN / signal** | Arduino **D2** | white or yellow |
| 12V adapter **-** | Arduino **GND** | also black (shared ground) |
| Arduino **USB** | PC USB port | the data cable |

**Two rules that matter:**

1. **The Arduino and the coin slot must share a ground.** Without that shared
   black wire the pulses are meaningless and the counter will read randomly.
2. **Never feed 12V into the Arduino.** The 12V adapter goes to the coin slot
   only. The Arduino is powered from USB. Sharing GND is safe; sharing 12V
   destroys the board.

---

## Check the signal voltage FIRST

Some coin slots pulse at **5V** (safe for the Arduino). Others pulse at
**12V**, which will destroy the pin.

1. Plug in the coin slot, but leave the signal wire disconnected from D2.
2. Set a multimeter to DC volts, black probe on the shared GND, red probe on
   the signal wire.
3. Drop a coin and watch the reading.

| Reading | What to do |
| --- | --- |
| Around **5V** | Connect straight to D2. Done. |
| Around **12V** | **Do not connect directly.** Use a 2-resistor divider below. |
| Around **0V, brief dip** | Open-collector output. Connect to D2 directly; `INPUT_PULLUP` already handles it. |

**12V to 5V divider:** 10k resistor from the signal wire to D2, and 6.8k
resistor from D2 to GND. That drops 12V to about 4.8V.

---

## Uploading the sketch

1. Install the **Arduino IDE** (free, from arduino.cc).
2. Open `coin_slot.ino`.
3. **Tools > Board >** Arduino UNO (or Arduino Nano for a Nano).
4. **Tools > Port >** pick the COM port of the board.
   - If no port appears on a CH340 board, install the **CH340 driver**.
5. Click **Upload**.

---

## Testing, in order

Do these in sequence. Stop at the first one that fails.

| Step | Do this | Expect |
| --- | --- | --- |
| 1 | Open Device Manager, expand **Ports (COM & LPT)** | a `COM` device appears |
| 2 | Open Serial Monitor at **9600 baud** | no error, empty window |
| 3 | Type `5` and press Enter (ECA Print closed) | `5` echoes back |
| 4 | Close Serial Monitor, open ECA Print | header shows the coin port found |
| 5 | Drop one **1 peso** coin | credit `+1` |
| 6 | Drop one **5 peso** coin | credit `+5` |
| 7 | Drop one **10 peso** coin | credit `+10` |
| 8 | Drop one **20 peso** coin | credit `+20` |

---

## Troubleshooting

| Problem | Cause | Fix |
| --- | --- | --- |
| No COM port in Device Manager | CH340 driver missing | Install the CH340 driver, replug |
| Credit never changes | Signal wire not on D2, or no shared GND | Recheck the two wiring rules above |
| A 5 peso coin adds only 1 | Slot set to "1 pulse per coin" | Reprogram to "1 pulse per peso", or use separate coin wires |
| Credit jumps by random amounts | Contact bounce, or interference | Twist the signal and ground wires together, shorten them |
| A 5 peso coin adds only 2 or 3 | `DEBOUNCE_MS` too high in the sketch | Lower it (try 8) and re-upload |
| One coin is counted twice | `DEBOUNCE_MS` too low | Raise it (try 25) and re-upload |
| Every second coin is rejected | Normal for these slots (about 95% acceptance) | Clean the coin path, test with flat clean coins |
| Credit added, then vanishes | Idle credit expiry (5 minutes) | Working as designed |

---

## How it fits the app

```
12V adapter  ->  1299 coin slot  ->  pulse on D2
                                        |
                                   Arduino UNO
                                        |
                              USB serial, 9600 baud
                                        |
                                   ECA Print
```

The app reads one whole number per line. So the sketch sends:

```
5\n
```

and the app adds `5` to the customer's credit. There is no fixed list of
accepted values, so any positive whole number works - which is why 20 peso
coins are already supported without changing the app.

---

## Prices for reference

| Mode | Price per page |
| --- | --- |
| Black and white | 2 pesos |
| Full colour | 4 pesos |

Set in `config.py` as `BW_PRICE_PER_PAGE` and `COLOR_PRICE_PER_PAGE`.

**Note:** the machine gives no change. A 20 peso coin on a 6 peso job leaves
14 pesos of credit, which expires after 5 minutes idle.
