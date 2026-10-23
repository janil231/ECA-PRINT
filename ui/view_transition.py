import tkinter as tk

from config import (
    APP_BG,
    COLOR_PRIMARY_BLUE,
    COLOR_SECONDARY_TEXT,
    FONT_SMALL,
    UI_FONT,
)


def _ease_in_out_cubic(t):
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - pow(-2.0 * t + 2.0, 3) / 2.0


class FadeTransition:
    def __init__(self, host, duration_ms=320, frame_ms=16):
        self.host = host
        self.duration = max(0.16, duration_ms / 1000.0)
        self.frame_ms = max(10, frame_ms)
        self.running = False
        self._after_id = None
        self._overlay = None
        self._on_done = None
        self._build_new = None
        self._on_switch = None
        self._old_view = None
        self._new_view = None
        self._swapped = False
        self._half = self.duration / 2.0
        self._steps = max(4, int(round(self._half * 1000.0 / self.frame_ms)))
        self._step_index = 0

    def run(self, old_view, build_new, on_switch, on_done=None):
        if self.running:
            return False
        width = self._host_dimension(self.host.winfo_width, self.host.winfo_toplevel().winfo_width)
        height = self._host_dimension(self.host.winfo_height, self.host.winfo_toplevel().winfo_height)
        if width < 10 or height < 10:
            return self._fallback(old_view, build_new, on_switch, on_done)

        self.running = True
        self._on_done = on_done
        self._build_new = build_new
        self._on_switch = on_switch
        self._old_view = old_view
        self._new_view = None
        self._swapped = False
        try:
            self._overlay = self._make_overlay()
        except Exception:
            return self._fallback(old_view, build_new, on_switch, on_done)
        if self._overlay is None:
            return self._fallback(old_view, build_new, on_switch, on_done)

        self._step_index = 0
        try:
            self._after_id = self.host.after(self.frame_ms, self._step)
        except Exception:
            return self._fallback(old_view, build_new, on_switch, on_done)
        return True

    def _step(self):
        self._step_index += 1
        progress = min(1.0, self._step_index / self._steps)
        eased = _ease_in_out_cubic(progress)
        alpha = 1.0 - eased if self._swapped else eased
        try:
            self._overlay.attributes("-alpha", max(0.0, min(1.0, alpha)))
        except Exception:
            return self._fail()

        if not self._swapped and progress >= 1.0:
            self._swapped = True
            self._build_under_cover()
            self._step_index = 0
            return self._schedule()

        if self._swapped and progress >= 1.0:
            return self._finish()

        return self._schedule()

    def _build_under_cover(self):
        try:
            new_view = self._build_new()
        except Exception:
            new_view = None
        if new_view is None:
            return False
        try:
            new_view.pack_forget()
            new_view.place_forget()
            new_view.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            new_view.update_idletasks()
            self._on_switch(new_view)
            try:
                self._old_view.destroy()
            except Exception:
                pass
            self._new_view = new_view
            return True
        except Exception:
            try:
                new_view.destroy()
            except Exception:
                pass
            return False

    def _schedule(self):
        try:
            self._after_id = self.host.after(self.frame_ms, self._step)
        except Exception:
            return self._fail()
        return None

    def _finish(self):
        self._after_id = None
        self.running = False
        self._hide_overlay()
        if self._new_view is not None:
            try:
                self._new_view.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
        self._new_view = None
        self._build_new = None
        self._on_switch = None
        self._old_view = None
        self._run_done()

    def _fail(self):
        self._after_id = None
        self.running = False
        self._hide_overlay()
        if self._old_view is not None and self._widget_exists(self._old_view):
            try:
                self._old_view.place_forget()
            except Exception:
                pass
            try:
                self._old_view.pack(fill="both", expand=True)
            except Exception:
                pass
        if self._new_view is not None and self._widget_exists(self._new_view):
            try:
                self._new_view.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            except Exception:
                pass
        self._new_view = None
        self._build_new = None
        self._on_switch = None
        self._old_view = None
        self._run_done()
        return None

    def _fallback(self, old_view, build_new, on_switch, on_done):
        self.running = False
        self._after_id = None
        self._hide_overlay()
        try:
            new_view = build_new()
        except Exception:
            new_view = None
        if new_view is not None:
            try:
                on_switch(new_view)
                old_view.destroy()
            except Exception:
                pass
        self._on_done = on_done
        self._run_done()
        return False

    def _make_overlay(self):
        root = self.host.winfo_toplevel()
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        width = root.winfo_width()
        height = root.winfo_height()
        overlay = tk.Toplevel(root)
        self._overlay = overlay
        overlay.withdraw()
        overlay.overrideredirect(True)
        overlay.configure(bg=APP_BG)
        overlay.geometry(f"{width}x{height}+{x}+{y}")
        overlay.attributes("-topmost", True)
        try:
            overlay.attributes("-toolwindow", True)
        except Exception:
            pass
        overlay.attributes("-alpha", 0.0)
        self._build_loading_mark(overlay)
        overlay.update_idletasks()
        overlay.deiconify()
        overlay.lift()
        return overlay

    @staticmethod
    def _build_loading_mark(overlay):
        mark = tk.Frame(overlay, bg=APP_BG)
        mark.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            mark,
            text="\U0001F5A8\uFE0F",
            font=(UI_FONT, 44),
            fg=COLOR_PRIMARY_BLUE,
            bg=APP_BG,
        ).pack(pady=(0, 6))
        tk.Label(
            mark,
            text="ECA Print",
            font=(UI_FONT, 28, "bold"),
            fg=COLOR_PRIMARY_BLUE,
            bg=APP_BG,
        ).pack()
        tk.Label(
            mark,
            text="Preparing your screen\u2026",
            font=FONT_SMALL,
            fg=COLOR_SECONDARY_TEXT,
            bg=APP_BG,
        ).pack(pady=(8, 0))

    def _hide_overlay(self):
        if self._overlay is None:
            return
        try:
            self._overlay.attributes("-alpha", 0.0)
        except Exception:
            pass
        try:
            self._overlay.destroy()
        except Exception:
            pass
        self._overlay = None

    @staticmethod
    def _host_dimension(host_getter, window_getter):
        try:
            value = host_getter()
            if value >= 10:
                return value
        except Exception:
            pass
        try:
            return max(10, window_getter())
        except Exception:
            return 0

    @staticmethod
    def _widget_exists(widget):
        try:
            return bool(widget and widget.winfo_exists())
        except Exception:
            return False

    def _run_done(self):
        callback = self._on_done
        self._on_done = None
        if callback is not None:
            try:
                callback()
            except Exception:
                pass

    def cancel(self):
        if self._after_id is not None:
            try:
                self.host.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        self.running = False
        self._on_done = None
        self._build_new = None
        self._on_switch = None
        self._old_view = None
        self._new_view = None
        self._hide_overlay()
