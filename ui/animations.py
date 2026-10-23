"""Small animation helpers for the kiosk: screen fades and a live printer.

Everything here is drawn with plain tkinter Canvas shapes, so there are
no image files to bundle and nothing extra to install.
"""
import math
import tkinter as tk

import customtkinter as ctk


def fade_in_window(root, duration_ms=220, start_alpha=0.45):
    """Smooth fade-in applied on every screen change (system-wide motion)."""
    try:
        steps = 6
        delay = max(15, duration_ms // steps)

        def tick(i=0):
            try:
                if not root.winfo_exists():
                    return
                alpha = start_alpha + (1.0 - start_alpha) * (i / steps)
                root.attributes("-alpha", max(0.0, min(1.0, alpha)))
                if i < steps:
                    root.after(delay, lambda: tick(i + 1))
                else:
                    root.attributes("-alpha", 1.0)
            except Exception:
                pass

        root.attributes("-alpha", start_alpha)
        root.after(delay, lambda: tick(1))
    except Exception:
        pass


def _mix(c1, c2, t):
    """Linear blend two #RRGGBB colors, t in 0..1 -> '#RRGGBB'."""
    t = max(0.0, min(1.0, float(t)))
    out = []
    for i in (1, 3, 5):
        a = int(c1[i:i + 2], 16)
        b = int(c2[i:i + 2], 16)
        out.append(int(round(a + (b - a) * t)))
    return "#%02X%02X%02X" % tuple(out)


class PrinterPaperAnimation(ctk.CTkFrame):
    """Printer status widget: the sheet advances only when it means something.

    States and their motion:
    - set_progress(0..1): the sheet extends with real render/print progress
      and never moves backwards.
    - start_loop(): the spooler is draining. The sheet creeps forward very
      slowly while the status LED breathes. No oscillation - the paper is
      never pulled back in.
    - show_success(): sheet fully out, green check replacing the LED.
    - show_error(): sheet stops where it is, red warning badge, red LED.
    - stop(): freeze.

    NOTE: never use self._w / self._h / self.canvas here - those names
    collide with tkinter's own Widget internals and break the widget.
    """

    def __init__(self, master, width=560, height=300, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        try:
            from config import CARD_BG
        except Exception:
            CARD_BG = "#FFFFFF"
        self._pic_w, self._pic_h = int(width), int(height)
        self._progress = 0.0
        self._looping = False
        self._phase = 0.0
        self._state = "busy"  # busy | success | error
        self._anim_timer = None

        self._paper_canvas = tk.Canvas(
            self, width=self._pic_w, height=self._pic_h, bg=CARD_BG,
            highlightthickness=0, bd=0,
        )
        self._paper_canvas.pack(pady=(6, 2))
        self._draw_scene()
        self._run()

    # ------------------------------------------------------------ public
    def set_progress(self, value):
        try:
            self._state = "busy"
            self._looping = False
            # Monotonic: the sheet never retracts on a lower value.
            self._progress = max(self._progress,
                                 max(0.0, min(1.0, float(value))))
            self._draw_scene()
        except Exception:
            pass

    def start_loop(self):
        try:
            self._state = "busy"
            self._looping = True
            self._draw_scene()
        except Exception:
            pass

    def show_success(self):
        try:
            self._looping = False
            self._state = "success"
            self._progress = 1.0
            self._draw_scene()
        except Exception:
            pass

    def show_error(self):
        try:
            self._looping = False
            self._state = "error"
            self._draw_scene()
        except Exception:
            pass

    def stop(self):
        try:
            self._looping = False
            if self._anim_timer is not None:
                self.after_cancel(self._anim_timer)
        except Exception:
            pass
        self._anim_timer = None

    # ----------------------------------------------------------- ticking
    def _run(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            if self._looping and self._state == "busy":
                self._phase = (self._phase + 0.02) % 1.0
                # Slow forward creep only: the paper never retracts.
                self._progress = min(0.92, self._progress + 0.0009)
                self._draw_scene()
        except Exception:
            pass
        try:
            self._anim_timer = self.after(40, self._run)
        except Exception:
            pass

    def _led_color(self):
        if self._state == "error":
            return "#FF3B30"
        if self._state == "success":
            return "#34C759"
        if self._looping:
            # Subtle breathing while waiting on the spooler.
            t = 0.5 + 0.5 * math.sin(self._phase * 2 * math.pi)
            return _mix("#1F8B47", "#6BE39B", t)
        return "#34C759"

    # ----------------------------------------------------------- drawing
    def _draw_scene(self):
        c = self._paper_canvas
        try:
            if not c.winfo_exists():
                return
        except Exception:
            return
        try:
            c.delete("all")
        except Exception:
            return

        W, H = self._pic_w, self._pic_h
        cx = W // 2
        body_top, body_bot = 26, 126
        slot_top, slot_bot = body_bot - 14, body_bot
        tray_top = H - 48

        # --- rear paper stack waiting to feed ---
        c.create_rectangle(cx - 66, 10, cx + 66, 18,
                           fill="#FFFFFF", outline="#D1D5DB", width=2)
        c.create_rectangle(cx - 62, 16, cx + 62, 24,
                           fill="#FFFFFF", outline="#D1D5DB", width=2)

        # --- printer body ---
        c.create_rectangle(cx - 150, body_top, cx + 150, body_bot,
                           fill="#1F2937", outline="#111827", width=2)
        # feed slot on top
        c.create_rectangle(cx - 70, body_top + 4, cx + 70, body_top + 12,
                           fill="#0B1220", outline="")
        # front output slot
        c.create_rectangle(cx - 122, slot_top, cx + 122, slot_bot,
                           fill="#0B1220", outline="")
        # restrained brand mark
        c.create_text(cx - 134, body_top + 40, text="PRINT VENDO", anchor="w",
                      font=("Segoe UI", 11, "bold"), fill="#9CA3AF")

        # --- sheet (tucked into the output slot) ---
        sheet_top = slot_bot - 6
        max_len = (tray_top + 14) - sheet_top
        min_len = 30
        length = min_len + max(0.0, min(1.0, self._progress)) * (max_len - min_len)
        x0, x1 = cx - 80, cx + 80
        bottom = sheet_top + length
        c.create_rectangle(x0, sheet_top, x1, bottom,
                           fill="#FFFFFF", outline="#D1D5DB", width=2)
        # printed lines appear as the sheet grows
        for i in range(4):
            y = sheet_top + 26 + i * 24
            if y < bottom - 18:
                lw = 100 - (i % 3) * 22
                c.create_line(x0 + 30, y, x0 + 30 + lw, y,
                              fill="#D1D5DB", width=5)
        if length > min_len + 4:
            c.create_rectangle(x0, bottom - 7, x1, bottom,
                               fill="#E5E7EB", outline="")

        # --- output tray, drawn over the sheet so paper rests in it ---
        c.create_rectangle(cx - 128, tray_top, cx + 128, tray_top + 14,
                           fill="#E9E9EE", outline="#D1D5DB", width=2)
        c.create_line(cx - 128, tray_top + 14, cx + 128, tray_top + 14,
                      fill="#C7CBD3", width=2)

        # --- status light / badge on the right, never over the brand ---
        lx, ly = cx + 128, body_top + 34
        if self._state == "success":
            c.create_oval(lx - 17, ly - 17, lx + 17, ly + 17,
                          fill="#34C759", outline="#FFFFFF", width=3)
            c.create_text(lx, ly + 1, text="\u2713",
                          font=("Segoe UI", 20, "bold"), fill="#FFFFFF")
        elif self._state == "error":
            c.create_oval(lx - 17, ly - 17, lx + 17, ly + 17,
                          fill="#FF3B30", outline="#FFFFFF", width=3)
            c.create_text(lx, ly + 1, text="!",
                          font=("Segoe UI", 20, "bold"), fill="#FFFFFF")
        else:
            color = self._led_color()
            if self._looping:
                c.create_oval(lx - 11, ly - 11, lx + 11, ly + 11,
                              fill="", outline=_mix("#1F2937", color, 0.35),
                              width=2)
            c.create_oval(lx - 6, ly - 6, lx + 6, ly + 6, fill=color, outline="")
