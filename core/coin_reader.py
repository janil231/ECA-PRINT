import threading
import time
import serial
import serial.tools.list_ports

from config import BAUD_RATE


class CoinReader:
    def __init__(self):
        self.credit = 0
        self.simulation_mode = False
        self.hardware_available = False
        self._thread = None
        self._running = False
        self._credit_callback = None
        self._status_callback = None

    def set_credit_callback(self, callback):
        self._credit_callback = callback

    def set_status_callback(self, callback):
        self._status_callback = callback

    def detect_arduino_port(self):
        """Return the Arduino's COM port, or None.

        Only real USB-serial bridges are accepted (Arduino / CH340 / CH341 /
        FTDI / CP210x). Matching every port whose text contained 'COM' used
        to grab unrelated devices such as Bluetooth serial ports.
        """
        try:
            ports = list(serial.tools.list_ports.comports())
        except Exception:
            return None
        hints = (
            "arduino", "genuino", "ch340", "ch341", "wch",
            "usb-serial", "usb serial", "ftdi", "cp210", "silicon labs",
            "1a86", "2341", "2a03",
        )
        for p in ports:
            hay = " ".join(
                str(getattr(p, attr, "") or "")
                for attr in ("device", "description", "manufacturer", "hwid")
            ).lower()
            if any(h in hay for h in hints):
                return getattr(p, "device", None)
        return None

    def start(self):
        if self.simulation_mode:
            self._simulation_start()
            return
        if self._running:
            self._notify_status()
            return
        self._running = True
        self._thread = threading.Thread(target=self._hardware_listener, daemon=True)
        self._thread.start()

    def force_simulation(self):
        """Mark simulation BEFORE start(), so config.SIMULATION_MODE wins."""
        self.simulation_mode = True

    def _simulation_start(self):
        self.simulation_mode = True
        print("[CoinReader] Starting simulation mode")
        self._notify_status()

    def _notify(self):
        cb = self._credit_callback
        if cb:
            try:
                cb(self.credit)
            except Exception:
                pass

    def _notify_status(self):
        cb = self._status_callback
        if cb:
            try:
                cb(self.hardware_available, self.simulation_mode)
            except Exception:
                pass

    def _set_hardware_available(self, available):
        available = bool(available)
        if available == self.hardware_available:
            return
        self.hardware_available = available
        self._notify_status()

    def _hardware_listener(self):
        """Connect to the coin slot, retrying until one appears."""
        while self._running:
            if self.simulation_mode:
                self._set_hardware_available(False)
                time.sleep(0.5)
                continue
            port = self.detect_arduino_port()
            if not port:
                self._set_hardware_available(False)
                time.sleep(2)
                continue
            ser = None
            try:
                ser = serial.Serial(port, BAUD_RATE, timeout=1)
                self._set_hardware_available(True)
                print(f"[CoinReader] Connected on {port}")
                while self._running and not self.simulation_mode:
                    try:
                        if ser.in_waiting > 0:
                            line = ser.readline().decode("utf-8", errors="ignore").strip()
                            if line.isdigit() and int(line) > 0:
                                self.credit += int(line)
                                print(f"[CoinReader] Pulse received, credit now: {self.credit}")
                                self._notify()
                        else:
                            time.sleep(0.05)
                    except Exception as read_err:
                        print(f"[CoinReader] Serial read error: {read_err}")
                        break
            except Exception as e:
                print(f"[CoinReader] Coin slot unavailable on {port}: {e}")
            finally:
                try:
                    if ser:
                        ser.close()
                except Exception:
                    pass
                self._set_hardware_available(False)
            if self._running and not self.simulation_mode:
                time.sleep(2)

    def stop(self):
        self._running = False
        if self._thread:
            try:
                self._thread.join(timeout=3)
            except Exception:
                pass

    def get_credit(self):
        return self.credit

    def deduct_credit(self, amount):
        if self.credit >= amount:
            self.credit -= amount
            self._notify()
            return True
        return False

    def add_credit(self, amount):
        self.credit += amount
        self._notify()

    def reset_credit(self):
        self.credit = 0
        self._notify()

    def is_simulation_mode(self):
        return self.simulation_mode

    def is_hardware_available(self):
        return bool(self.hardware_available)

    def is_payment_available(self):
        return bool(self.simulation_mode or self.hardware_available)

    def set_simulation_mode(self, value):
        """Force simulation on/off at runtime (used by the staff panel).

        Turning it on lets staff add credit with the 'c' key / coin buttons
        for a demo. Turning it off means only real coin pulses count.
        """
        self.simulation_mode = bool(value)
        self._notify()
        if not self.simulation_mode and not self._running:
            self.start()
        else:
            self._notify_status()
