"""Capture every kiosk screen for design review / QA.

Run from anywhere:  python tools/ui_screenshots.py [prefix]

Safety: the real print job is patched out (no spooler traffic) and
winsound beeps are muted, so this can never print a page or make noise.
Sale-log lines written by the success state are rolled back afterwards.
"""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

import winsound
winsound.Beep = lambda *a, **k: None  # silent audit

import customtkinter as ctk
from PIL import ImageGrab

import ui.printing_view as pv
pv.PrintingView._do_print = lambda self: None  # never touch the real printer

from ui.header_bar import HeaderBar
from ui.welcome_view import WelcomeView
from ui.file_browser_view import FileBrowserView
from ui.pricing_view import PricingView
from ui.payment_view import PaymentView
from ui.printing_view import PrintingView
from ui.qr_view import QRView
from ui.admin_view import AdminView

PDF = os.path.join("temp", "Sample_Document.pdf")
OUT_DIR = os.path.join(PROJECT_ROOT, "screenshots")
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "current"
LOG = "vendo_log.txt"
LOG_SIZE_AT_START = os.path.getsize(LOG) if os.path.exists(LOG) else 0


class StubCoin:
    def __init__(self, credit=0, sim=True):
        self.credit, self.sim = credit, sim
    def get_credit(self): return self.credit
    def is_simulation_mode(self): return self.sim
    def is_hardware_available(self): return not self.sim
    def is_payment_available(self): return self.sim or self.is_hardware_available()
    def add_credit(self, a): self.credit += a
    def deduct_credit(self, a):
        if self.credit >= a:
            self.credit -= a
            return True
        return False
    def reset_credit(self): self.credit = 0
    def set_credit_callback(self, cb): pass
    def set_simulation_mode(self, v): self.sim = bool(v)


def cb(*a, **k):
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    root = ctk.CTk()
    root.geometry("1920x1080+0+0")
    root.title("ECA Print")
    root.attributes("-topmost", True)
    root.update()

    header = HeaderBar(root)
    header.pack(side="top", fill="x")
    header.update_credit(6)
    header.update_status(True)
    root.update()

    current = [None]

    def show(builder, name, settle=0.4):
        if current[0] is not None:
            try:
                current[0].destroy()
            except Exception:
                pass
            current[0] = None
        root.update()
        view = builder()
        current[0] = view
        time.sleep(settle)
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        w, h = root.winfo_width(), root.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        path = os.path.join(OUT_DIR, "%s_%s.png" % (PREFIX, name))
        img.save(path)
        print("saved", path, img.size)

    show(lambda: WelcomeView(root, StubCoin(), cb), "1welcome")
    show(lambda: FileBrowserView(root, cb, StubCoin()), "2files", settle=1.2)
    show(lambda: PricingView(root, PDF, cb, StubCoin()), "3pricing", settle=1.0)
    show(lambda: PaymentView(root, PDF, 6, "bw", cb, StubCoin(credit=0)), "4payment_empty")
    show(lambda: PaymentView(root, PDF, 6, "bw", cb, StubCoin(credit=6)), "5payment_paid")

    def mk_printing():
        return PrintingView(root, PDF, 6, "bw", StubCoin(6), cb, 1, None, 1, "a4")

    def p_progress():
        v = mk_printing()
        v._set_progress(0.35)
        return v
    show(p_progress, "6printing_progress")

    def p_waiting():
        v = mk_printing()
        v._set_progress(0.4)
        v._show_printing_state()
        return v
    show(p_waiting, "7printing_waiting", settle=1.2)

    def p_success():
        v = mk_printing()
        v._on_print_success(1)
        return v
    show(p_success, "8printing_success", settle=0.6)

    def p_error():
        v = mk_printing()
        v._on_paper_stuck()
        return v
    show(p_error, "9printing_error", settle=0.6)

    show(lambda: QRView(root, "192.168.1.100", cb), "10qr")
    show(lambda: AdminView(root, StubCoin(6), cb), "11admin_pin")

    def admin_panel():
        v = AdminView(root, StubCoin(6), cb)
        v._build_panel()
        return v
    show(admin_panel, "12admin_panel", settle=0.8)

    if current[0] is not None:
        try:
            current[0].destroy()
        except Exception:
            pass
    root.destroy()

    # Roll back the fake sale line the success state logged.
    try:
        if os.path.exists(LOG):
            with open(LOG, "r+b") as f:
                f.truncate(LOG_SIZE_AT_START)
    except Exception as e:
        print("log rollback failed:", e)
    print("DONE")


if __name__ == "__main__":
    main()
