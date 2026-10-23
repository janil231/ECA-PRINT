import customtkinter as ctk
import threading
import winsound
import os
import sys
import time

from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SIMULATION_MODE,
    ADD_CREDIT_KEY,
    APP_BG,
    VIEW_RESET_SECONDS,
    QR_RESET_SECONDS,
    ADMIN_RESET_SECONDS,
    CREDIT_EXPIRY_SECONDS,
    LOCK_ESCAPE,
    PRINTER_STATUS_POLL,
    VIEW_TRANSITION_MS,
)
from core.coin_reader import CoinReader
from core.usb_detect import USBDetector
from core.file_reader import FileReader
from wireless.server import get_local_ip, app
from ui.welcome_view import WelcomeView
from ui.header_bar import HeaderBar
from ui.view_transition import FadeTransition


class PrintVendoApp:
    def __init__(self):
        # Initialize directories
        os.makedirs("temp/output", exist_ok=True)
        os.makedirs("temp/uploads", exist_ok=True)
        os.makedirs("temp", exist_ok=True)

        # Packaged builds have no console: send output to a log file so
        # failures can be diagnosed instead of vanishing.
        self._setup_logging()
        # Keep temp/ from growing forever on an always-on kiosk.
        self._cleanup_temp()
        # Never carry a previous customer's documents into a new session.
        self._clear_session_files()
        # Unpack the demo documents packed inside the exe so a freshly
        # downloaded exe has real files to show during a presentation.
        self._seed_demo_files()

        # Auto-generate sample PDF if temp/ is empty
        sample_path = os.path.join("temp", "Sample_Document.pdf")
        if not os.path.exists(sample_path):
            try:
                import fitz
                doc = fitz.open()
                page = doc.new_page()
                # Add test text - use simple black color
                page.insert_text((70, 100), "Print Vendo Test Page", fontsize=32)
                page.insert_text((70, 150), "Page 1 of 2", fontsize=20)
                doc.save(sample_path)
                doc.close()
                print(f"[Main] Generated sample PDF: {sample_path}")
            except Exception:
                # Fallback: create empty PDF
                try:
                    from PIL import Image
                    img = Image.new('RGB', (800, 1124), "white")
                    img.save(sample_path)
                    print(f"[Main] Generated fallback sample PDF: {sample_path}")
                except Exception:
                    print(f"[Main] Could not generate sample PDF")

        # CustomTkinter setup - modern clean light theme
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()

        # Fit the UI to the actual display. The design is built for
        # 1920x1080; a professor's laptop is often 1366x768, where the full
        # size layout would be cut off. Scaling every widget down keeps the
        # whole screen visible. At 1920x1080 or larger this is a no-op, so
        # the kiosk machine looks exactly as before.
        try:
            _sw = self.root.winfo_screenwidth()
            _sh = self.root.winfo_screenheight()
            _scale = min(_sw / 1920.0, _sh / 1080.0)
            _scale = max(0.72, min(1.0, _scale))
            if _scale < 0.99:
                ctk.set_widget_scaling(round(_scale, 2))
                print(f"[Main] UI scaled to {_scale:.2f} for a {_sw}x{_sh} screen")
        except Exception:
            pass

        self.root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        self.root.title("Print Vendo Kiosk")

        # Make borderless/fullscreen for kiosk
        self.root.attributes("-fullscreen", True)
        self.root.configure(fg_color=APP_BG)

        # Coin reader - start in the mode chosen by config.SIMULATION_MODE.
        # On a real machine this is False, so no free credit can be added.
        self.coin_reader = CoinReader()
        if SIMULATION_MODE:
            self.coin_reader.force_simulation()
        self.coin_reader.set_credit_callback(self._on_credit_change)
        self.coin_reader.set_status_callback(self._on_coin_status_change)
        self.coin_reader.start()

        # USB detector
        self.usb_detector = USBDetector()

        # Header bar - SINGLE instance, managed by main.py only
        self.header = HeaderBar(self.root)
        self.header.pack(side="top", fill="x")

        self.view_host = ctk.CTkFrame(self.root, fg_color=APP_BG, corner_radius=0)
        self.view_host.pack(side="top", fill="both", expand=True)
        self._sync_payment_status()
        # Staff can open the panel by tapping the title 5 times quickly.
        try:
            self.header.title_label.bind("<Button-1>", self._on_title_tap)
        except Exception:
            pass
        self._title_taps = []

        # View state
        self.current_view = None
        self.current_view_name = None
        self.view_transition = FadeTransition(self.view_host, duration_ms=VIEW_TRANSITION_MS)
        self.inactivity_timer = None
        self.last_activity = time.time()
        self.last_credit = self.coin_reader.get_credit()
        self.credit_expiry_timer = None
        self.printer_status_timer = None

        # Keyboard bindings
        self._setup_keybindings()

        # Start Flask server in background thread
        self.flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, use_reloader=False), daemon=True)
        self.flask_thread.start()

        # Start inactivity watchdog + printer health checks
        self._watch_inactivity()
        self._clear_stale_print_jobs()
        self._watch_printer_status()

        # Show welcome screen
        self.switch_view("welcome", ip_address=get_local_ip())

    # ------------------------------------------------------- keyboard
    def _setup_keybindings(self):
        try:
            self.root.bind("<" + ADD_CREDIT_KEY + ">", self._on_add_credit)
        except Exception:
            pass
        self.root.bind("<Escape>", self._on_escape)
        # Any tap anywhere counts as activity, so the 60s idle reset only
        # fires when the customer has really walked away - not while they
        # are reading a screen or picking a paper size.
        try:
            self.root.bind_all("<Button-1>", self._on_any_click, add="+")
        except Exception:
            pass
        # Hidden staff shortcut: Ctrl+Shift+A opens the admin panel.
        for seq in ("<Control-Shift-A>", "<Control-Shift-a>"):
            try:
                self.root.bind(seq, self._on_admin_hotkey)
            except Exception:
                pass

    def _on_add_credit(self, event):
        # Simulation only. On a real machine with a coin slot attached, the
        # 'c' key must never add free credit (that would be a way to cheat).
        try:
            if not self.coin_reader.is_simulation_mode():
                return
        except Exception:
            return
        # add_credit() fires the credit callback itself, so no direct UI
        # update here (avoids a double update / flicker per keypress).
        self.coin_reader.add_credit(1)
        try:
            winsound.Beep(1200, 120)
        except Exception:
            pass
        self._reset_inactivity_timer()

    def _on_escape(self, event):
        # In a real kiosk, Esc must NOT drop the customer to the Windows
        # desktop. Staff exit through the admin panel instead.
        if LOCK_ESCAPE:
            return
        if self.root.attributes("-fullscreen"):
            self.root.attributes("-fullscreen", False)
        else:
            self.root.quit()

    def _on_any_click(self, event=None):
        # Every tap on the kiosk is real activity.
        self._reset_inactivity_timer()

    def _on_admin_hotkey(self, event=None):
        self.switch_view("admin")

    def _on_title_tap(self, event=None):
        now = time.time()
        self._title_taps = [t for t in self._title_taps if now - t < 1.2] + [now]
        if len(self._title_taps) >= 5:
            self._title_taps = []
            self.switch_view("admin")

    # ------------------------------------------------------- credit
    def _on_credit_change(self, credit):
        # Coin callbacks can arrive from background threads (serial / keyboard hook).
        # Touching Tk widgets off the UI thread causes flicker and crashes,
        # so marshal everything back onto the Tk main loop.
        if threading.current_thread() is not threading.main_thread():
            try:
                self.root.after(0, lambda c=credit: self._on_credit_change(c))
            except Exception:
                pass
            return
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        # Credit went up (or was set): restart the idle expiry countdown.
        try:
            if credit != self.last_credit:
                self.last_credit = credit
                if credit > 0:
                    self._arm_credit_expiry()
                # A coin dropping in is activity too - never reset the
                # screen out from under someone who is paying.
                self._reset_inactivity_timer()
        except Exception:
            pass
        # HeaderBar itself guards redundant .configure() calls.
        try:
            self.header.update_credit(credit)
        except Exception:
            pass
        self._sync_payment_status()
        # Update current view if it shows credit - view guards redundant updates.
        try:
            if self.current_view and hasattr(self.current_view, 'update_credit_display'):
                self.current_view.update_credit_display()
        except Exception:
            pass

    def _on_coin_status_change(self, hardware_available, simulation_mode):
        if threading.current_thread() is not threading.main_thread():
            try:
                self.root.after(0, self._on_coin_status_change,
                                hardware_available, simulation_mode)
            except Exception:
                pass
            return
        self._sync_payment_status()

    def _sync_payment_status(self):
        header = getattr(self, "header", None)
        if header is None:
            return
        try:
            sim = self.coin_reader.is_simulation_mode()
            available = self.coin_reader.is_payment_available()
            header.update_status(sim)
            header.set_payment_warning(None if available else "PAYMENT OFFLINE")
        except Exception:
            return
        try:
            view = getattr(self, "current_view", None)
            if view and hasattr(view, "update_payment_status"):
                view.update_payment_status()
        except Exception:
            pass

    def _arm_credit_expiry(self):
        """(Re)start the 5-minute idle countdown for inserted credit."""
        try:
            if self.credit_expiry_timer is not None:
                self.root.after_cancel(self.credit_expiry_timer)
        except Exception:
            pass
        try:
            self.credit_expiry_timer = self.root.after(
                CREDIT_EXPIRY_SECONDS * 1000, self._expire_credit)
        except Exception:
            self.credit_expiry_timer = None

    def _expire_credit(self):
        self.credit_expiry_timer = None
        try:
            if self.coin_reader.get_credit() <= 0:
                return
        except Exception:
            return
        # Never clear credit while a job is printing or about to.
        try:
            name = type(self.current_view).__name__ if self.current_view else ""
        except Exception:
            name = ""
        if name in ("PrintingView", "PaymentView"):
            # Customer is mid-transaction - give them another full window.
            self._arm_credit_expiry()
            return
        try:
            self.coin_reader.reset_credit()
            self.last_credit = 0
            print("[Main] Idle credit expired after %ss" % CREDIT_EXPIRY_SECONDS)
        except Exception:
            pass

    # ------------------------------------------------------- timers
    def _watch_inactivity(self):
        elapsed = time.time() - self.last_activity
        # Never yank the screen away mid-print or mid-payment - that would
        # destroy the view while its background thread is running. The staff
        # panel gets a longer timeout so an unattended unlocked panel cannot
        # be left open for customers.
        try:
            name = type(self.current_view).__name__ if self.current_view else ""
        except Exception:
            name = ""
        protected = name in ("PrintingView", "PaymentView", "WelcomeView")
        if name == "AdminView":
            limit = ADMIN_RESET_SECONDS
        elif name == "QRView":
            limit = QR_RESET_SECONDS
        else:
            limit = VIEW_RESET_SECONDS
        if elapsed > limit and not protected:
            self._reset_to_welcome()
        try:
            self.inactivity_timer = self.root.after(1000, self._watch_inactivity)
        except Exception:
            pass

    def _clear_stale_print_jobs(self):
        """One-time startup sweep of dead print jobs left by an earlier crash.

        A job stuck from a previous paper-out / crash keeps the Epson's
        "paper out" bit latched, so the header would otherwise show a false
        PAPER OUT from the moment the kiosk opens. Done off the UI thread.
        """
        def work():
            try:
                from core.printer import Printer
                Printer().clear_stuck_jobs(only_errored=True)
            except Exception:
                pass
        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            pass

    def _watch_printer_status(self):
        """Poll printer health in the background and warn in the header."""
        def work():
            msg = None
            try:
                from core.printer import Printer
                state, text = Printer().get_status()
                if state != "ok":
                    msg = text
            except Exception:
                msg = None
            try:
                self.root.after(0, lambda m=msg: self._apply_printer_warning(m))
            except Exception:
                pass
        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            pass
        try:
            self.printer_status_timer = self.root.after(
                PRINTER_STATUS_POLL * 1000, self._watch_printer_status)
        except Exception:
            pass

    def _apply_printer_warning(self, message):
        try:
            self.header.set_printer_warning(message)
        except Exception:
            pass

    def _reset_inactivity_timer(self):
        self.last_activity = time.time()

    # ------------------------------------------------------- routing
    def switch_view(self, view_name, **kwargs):
        if view_name == "welcome_from_any":
            self._reset_to_welcome()
            return
        if self.view_transition.running:
            return
        if view_name == "welcome":
            self._clear_session_files()
        self._reset_inactivity_timer()

        old_view = self.current_view
        if not self._widget_exists(old_view):
            self._show_initial_view(view_name, **kwargs)
            return

        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            pass

        def build_new():
            try:
                return self._build_view(view_name, **kwargs)
            except Exception as e:
                print(f"[Main] Could not open '{view_name}': {e}")
                self._destroy_orphan_views(keep=old_view)
                return None

        def apply_new(new_view):
            self.current_view = new_view
            self.current_view_name = view_name

        self.view_transition.run(
            old_view, build_new, apply_new, on_done=self._after_view_switch)

    def _show_initial_view(self, view_name, **kwargs):
        try:
            new_view = self._build_view(view_name, **kwargs)
        except Exception as e:
            print(f"[Main] Could not open '{view_name}': {e}")
            self._destroy_orphan_views()
            self.current_view = None
            self.current_view_name = None
            if view_name != "welcome":
                self.switch_view("welcome")
            return
        self.current_view = new_view
        self.current_view_name = view_name
        self._after_view_switch()

    def _after_view_switch(self):
        try:
            view = self.current_view
            if view is not None and hasattr(view, "on_view_shown"):
                view.on_view_shown()
        except Exception:
            pass
        try:
            self.header.update_credit(self.coin_reader.get_credit())
        except Exception:
            pass

    @staticmethod
    def _widget_exists(widget):
        try:
            return bool(widget and widget.winfo_exists())
        except Exception:
            return False

    def _build_view(self, view_name, **kwargs):
        if view_name == "welcome":
            from ui.welcome_view import WelcomeView
            return WelcomeView(self.view_host, self.coin_reader, self._on_welcome_switch)
        if view_name == "file_browser":
            from ui.file_browser_view import FileBrowserView
            return FileBrowserView(self.view_host, self._on_file_browser_switch, self.coin_reader)
        if view_name == "pricing":
            from ui.pricing_view import PricingView
            return PricingView(self.view_host, kwargs.get("filepath"),
                               self._on_pricing_switch, self.coin_reader)
        if view_name == "payment":
            from ui.payment_view import PaymentView
            return PaymentView(
                self.view_host, kwargs.get("filepath"), kwargs.get("due", 0),
                kwargs.get("print_mode", "bw"), self._on_payment_switch, self.coin_reader,
                kwargs.get("start_page", 1), kwargs.get("end_page"),
                kwargs.get("copies", 1), kwargs.get("paper_size"))
        if view_name == "printing":
            from ui.printing_view import PrintingView
            return PrintingView(
                self.view_host, kwargs.get("filepath"), kwargs.get("due", 0),
                kwargs.get("print_mode", "bw"), self.coin_reader,
                self._on_printing_complete, kwargs.get("start_page", 1),
                kwargs.get("end_page"), kwargs.get("copies", 1),
                kwargs.get("paper_size"))
        if view_name == "qr":
            from ui.qr_view import QRView
            return QRView(self.view_host, kwargs.get("ip_address") or get_local_ip(),
                          self._on_qr_switch)
        if view_name == "admin":
            from ui.admin_view import AdminView
            return AdminView(self.view_host, self.coin_reader, self._on_admin_back,
                             on_restart=self._restart_app, on_exit=self._exit_app)
        raise ValueError(f"Unknown view: {view_name}")

    def _destroy_orphan_views(self, keep=None):
        try:
            from ui.base_view import BaseView
            for child in list(self.view_host.winfo_children()):
                if isinstance(child, BaseView) and child is not keep:
                    try:
                        child.destroy()
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_welcome_switch(self, target):
        self.switch_view(target)

    def _on_file_browser_switch(self, target, filepath=None):
        self.switch_view(target, filepath=filepath)

    def _on_pricing_switch(self, target, filepath=None, due=0, print_mode="bw", start_page=1, end_page=None, copies=1, paper_size=None):
        self.switch_view(target, filepath=filepath, due=due, print_mode=print_mode, start_page=start_page, end_page=end_page, copies=copies, paper_size=paper_size)

    def _on_payment_switch(self, target, filepath=None, due=0, print_mode="bw", start_page=1, end_page=None, copies=1, paper_size=None):
        if target == "printing":
            self.switch_view("printing", filepath=filepath, due=due, print_mode=print_mode, start_page=start_page, end_page=end_page, copies=copies, paper_size=paper_size)
        else:
            self.switch_view(target)

    def _on_printing_complete(self, target="welcome"):
        self.switch_view("welcome")

    def _on_qr_switch(self, target="welcome"):
        self.switch_view(target or "welcome")

    def _on_admin_back(self):
        self.switch_view("welcome")

    def _reset_to_welcome(self):
        # Preserve inserted credit, just reset UI
        self.switch_view("welcome")

    # ------------------------------------------------------- app control
    def _restart_app(self):
        try:
            self.coin_reader.stop()
        except Exception:
            pass
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            try:
                self.root.quit()
            except Exception:
                pass

    def _exit_app(self):
        try:
            self.coin_reader.stop()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass

    # ------------------------------------------------------- housekeeping
    @staticmethod
    def _setup_logging():
        try:
            if not getattr(sys, "frozen", False):
                return  # running from source - keep the console output
            os.makedirs("temp", exist_ok=True)
            log = open(os.path.join("temp", "app_log.txt"), "a", buffering=1, encoding="utf-8")
            sys.stdout = log
            sys.stderr = log
            print(f"\n--- Print Vendo started {time.strftime('%Y-%m-%d %X')} ---")
        except Exception:
            pass

    @staticmethod
    def _seed_demo_files():
        """Copy the demo documents bundled inside the exe into temp/ once.

        A freshly downloaded exe starts with an empty temp/ folder, so the
        file list would show only a blank sample page. Copying a few real
        documents (CV, resume, chapter) makes the demo worth watching.
        """
        marker = os.path.join("temp", ".demo_seeded")
        if os.path.exists(marker):
            return
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            src = os.path.join(base, "demo_files")
            if os.path.isdir(src):
                import shutil
                for name in os.listdir(src):
                    try:
                        shutil.copy2(os.path.join(src, name), os.path.join("temp", name))
                    except Exception:
                        pass
            with open(marker, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %X"))
        except Exception:
            pass

    @staticmethod
    def _cleanup_temp():
        # Delete stale temp files so a kiosk that runs for days never fills
        # the disk: printed previews after 1 day, cached Word PDFs after 7.
        import glob
        for pattern, days in (
            (os.path.join("temp", "output", "*"), 1),
            (os.path.join("temp", "converted", "*"), 7),
        ):
            cutoff = time.time() - days * 86400
            for path in glob.glob(pattern):
                try:
                    if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                        os.remove(path)
                except Exception:
                    pass

    @staticmethod
    def _clear_session_files():
        # Phone uploads, Word conversions and print previews all contain the
        # customer's document. Never leave them for the next customer.
        import glob
        for pattern in (
            os.path.join("temp", "uploads", "*"),
            os.path.join("temp", "converted", "*"),
            os.path.join("temp", "output", "*"),
        ):
            for path in glob.glob(pattern):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except Exception:
                    pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # In a packaged exe the working folder is wherever it was launched from
    # (often C:\Windows\System32 when double-clicked). Anchor it to the exe's
    # own folder so temp/, vendo_log.txt and the upload page are found.
    try:
        if getattr(sys, "frozen", False):
            os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
    except Exception:
        pass
    app = PrintVendoApp()
    app.run()
