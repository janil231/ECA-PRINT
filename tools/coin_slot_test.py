r"""Standalone coin-slot hardware test.

Close ECA Print first, then run from the print-vendo folder:

    python tools\coin_slot_test.py

Drop coins and watch the pulse values and running total. Press Ctrl+C to stop.
"""
import sys
import time

import serial
import serial.tools.list_ports

BAUD_RATE = 9600
HINTS = (
    "arduino", "genuino", "ch340", "ch341", "wch",
    "usb-serial", "usb serial", "ftdi", "cp210", "silicon labs",
    "1a86", "2341", "2a03",
)


def find_arduino_port():
    for port in serial.tools.list_ports.comports():
        haystack = " ".join(
            str(getattr(port, attr, "") or "")
            for attr in ("device", "description", "manufacturer", "hwid")
        ).lower()
        if any(hint in haystack for hint in HINTS):
            return port
    return None


def show_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No COM ports found at all.")
        return
    print("Available COM ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")


def main():
    port = find_arduino_port()
    if port is None:
        print("No Arduino/CH340 serial port detected.")
        show_ports()
        print("\nPlug in the Arduino, close ECA Print, then run this again.")
        return 1

    print(f"Using {port.device} ({port.description})")
    print("Close ECA Print before this test. Drop a coin now.")
    total = 0
    try:
        with serial.Serial(port.device, BAUD_RATE, timeout=1) as connection:
            time.sleep(2)
            connection.reset_input_buffer()
            print("Waiting for coin pulses... (Ctrl+C to stop)")
            while True:
                line = connection.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.isdigit() and int(line) > 0:
                    value = int(line)
                    total += value
                    print(f"Pulse: +{value}  |  Test total: {total}")
                else:
                    print(f"Arduino: {line}")
    except KeyboardInterrupt:
        print(f"\nStopped. Test total: {total}")
        return 0
    except serial.SerialException as exc:
        print(f"Could not open {port.device}: {exc}")
        print("Close ECA Print and the Arduino Serial Monitor, then try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
