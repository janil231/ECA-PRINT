'''Staff admin panel: PIN-gated screen for running the kiosk day to day.'''

import glob
import os
import threading
import time

import customtkinter as ctk

try:
    from config import (
        ADMIN_PIN,
        COLOR_APP_BG,
        COLOR_CARD_BG,
        COLOR_PRIMARY_TEXT,
        COLOR_SECONDARY_TEXT,
        COLOR_TERTIARY_TEXT,
        COLOR_PRIMARY_BLUE,
        COLOR_PRIMARY_BLUE_HOVER,
        COLOR_SUCCESS_GREEN,
        COLOR_SUCCESS_DARK,
        COLOR_WARNING_RED,
        COLOR_WARNING_RED_HOVER,
        COLOR_AMBER_BG,
        COLOR_AMBER_TEXT,
        COLOR_BORDER_GRAY,
        COLOR_PILL_GRAY,
        COLOR_PILL_GRAY_HOVER,
        COLOR_LIGHT_BLUE_BG,
        COLOR_LIGHT_BLUE_HOVER,
        COLOR_WHITE,
        CARD_RADIUS,
        BTN_RADIUS,
        PILL_RADIUS,
        UI_FONT,
        SPACE_XS,
        SPACE_SM,
        SPACE_MD,
        SPACE_LG,
    )
except Exception:
    ADMIN_PIN = "1234"
    COLOR_APP_BG = "#F2F2F7"
    COLOR_CARD_BG = "#FFFFFF"
    COLOR_PRIMARY_TEXT = "#111827"
    COLOR_SECONDARY_TEXT = "#6B7280"
    COLOR_TERTIARY_TEXT = "#8E8E93"
    COLOR_PRIMARY_BLUE = "#007AFF"
    COLOR_PRIMARY_BLUE_HOVER = "#0063D1"
    COLOR_SUCCESS_GREEN = "#34C759"
    COLOR_SUCCESS_DARK = "#248A3D"
    COLOR_WARNING_RED = "#FF3B30"
    COLOR_WARNING_RED_HOVER = "#E03228"
    COLOR_AMBER_BG = "#FEF3C7"
    COLOR_AMBER_TEXT = "#B45309"
    COLOR_BORDER_GRAY = "#E5E5EA"
    COLOR_PILL_GRAY = "#E9E9EE"
    COLOR_PILL_GRAY_HOVER = "#D9D9DE"
    COLOR_LIGHT_BLUE_BG = "#EAF2FF"
    COLOR_LIGHT_BLUE_HOVER = "#D8E8FF"
    COLOR_WHITE = "#FFFFFF"
    CARD_RADIUS, BTN_RADIUS, PILL_RADIUS, UI_FONT = 20, 16, 22, "Segoe UI"
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG = 6, 10, 16, 24

from ui.base_view import BaseView

SOFT_BG = "#F7F8FA"
SUCCESS_BG = "#EAF8EE"
DANGER_BG = "#FDE7E6"


def _card(parent, **kwargs):
    return ctk.CTkFrame(
        parent,
        fg_color=COLOR_CARD_BG,
        corner_radius=CARD_RADIUS,
        border_width=1,
        border_color=COLOR_BORDER_GRAY,
        **kwargs,
    )


class AdminView(BaseView):
    def __init__(self, master, coin_reader, on_back, on_restart=None, on_exit=None,
                 on_simulation_change=None):
        super().__init__(master)
        self.coin_reader = coin_reader
        self.on_back = on_back
        self.on_restart = on_restart
        self.on_exit = on_exit
        self.on_simulation_change = on_simulation_change
        self.pin_buffer = ""
        self._test_running = False

        wrap = ctk.CTkFrame(self, fg_color=COLOR_APP_BG)
        wrap.pack(expand=True, fill="both", padx=SPACE_LG, pady=SPACE_LG)

        header = ctk.CTkFrame(
            wrap,
            fg_color=COLOR_CARD_BG,
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=COLOR_BORDER_GRAY,
            height=84,
        )
        header.pack(fill="x", pady=(0, SPACE_MD))
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=(SPACE_LG, 0), pady=18)

        icon_tile = ctk.CTkFrame(left, width=48, height=48, fg_color=COLOR_LIGHT_BLUE_BG,
                                 corner_radius=14)
        icon_tile.pack(side="left", padx=(0, SPACE_MD))
        icon_tile.pack_propagate(False)
        ctk.CTkLabel(icon_tile, text="🛠", font=(UI_FONT, 21),
                     text_color=COLOR_PRIMARY_BLUE).pack(expand=True)

        titles = ctk.CTkFrame(left, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Staff panel", font=(UI_FONT, 24, "bold"),
                     text_color=COLOR_PRIMARY_TEXT).pack(anchor="w")
        ctk.CTkLabel(titles, text="Sales, printer health, and kiosk controls",
                     font=(UI_FONT, 13), text_color=COLOR_SECONDARY_TEXT).pack(
            anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=SPACE_LG, pady=20)

        self.close_btn = ctk.CTkButton(
            right, text="‹  Close", width=116, height=44,
            font=(UI_FONT, 14, "bold"), fg_color=COLOR_PILL_GRAY,
            hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT,
            corner_radius=BTN_RADIUS, command=self._close,
        )
        self.close_btn.pack(side="right")

        self.refresh_btn = ctk.CTkButton(
            right, text="↻  Refresh", width=116, height=44,
            font=(UI_FONT, 14, "bold"), fg_color=COLOR_LIGHT_BLUE_BG,
            hover_color=COLOR_LIGHT_BLUE_HOVER, text_color=COLOR_PRIMARY_BLUE,
            corner_radius=BTN_RADIUS, command=self._refresh_panel,
        )
        self.refresh_btn.pack(side="right", padx=(0, SPACE_SM))
        self.refresh_btn.pack_forget()

        self.body = ctk.CTkFrame(wrap, fg_color="transparent")
        self.body.pack(expand=True, fill="both")

        self._build_pin()

    def _build_pin(self):
        self._clear_body()
        self.refresh_btn.pack_forget()

        center = ctk.CTkFrame(self.body, fg_color="transparent")
        center.place(relx=0.5, rely=0.48, anchor="center")

        card = _card(center)
        card.pack()

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=32)

        icon = ctk.CTkFrame(inner, width=56, height=56, fg_color=COLOR_LIGHT_BLUE_BG,
                            corner_radius=18)
        icon.pack()
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, text="🔐", font=(UI_FONT, 24)).pack(expand=True)

        ctk.CTkLabel(inner, text="Staff access", font=(UI_FONT, 27, "bold"),
                     text_color=COLOR_PRIMARY_TEXT).pack(pady=(SPACE_MD, 2))
        ctk.CTkLabel(inner, text="Enter your 4-digit PIN to open the control panel",
                     font=(UI_FONT, 14), text_color=COLOR_SECONDARY_TEXT).pack()

        dots_pill = ctk.CTkFrame(inner, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        dots_pill.pack(pady=(SPACE_MD, SPACE_XS))
        self.pin_dots = ctk.CTkLabel(dots_pill, text="○  ○  ○  ○",
                                     font=(UI_FONT, 24, "bold"),
                                     text_color=COLOR_PRIMARY_BLUE)
        self.pin_dots.pack(padx=24, pady=8)

        self.pin_msg = ctk.CTkLabel(inner, text=" ", font=(UI_FONT, 13, "bold"),
                                    text_color=COLOR_WARNING_RED, height=18)
        self.pin_msg.pack(pady=(0, SPACE_XS))

        pad = ctk.CTkFrame(inner, fg_color="transparent")
        pad.pack()
        layout = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["C", "0", "↩"]]
        for row in layout:
            r = ctk.CTkFrame(pad, fg_color="transparent")
            r.pack(pady=5)
            for key in row:
                ctk.CTkButton(
                    r, text=key, width=96, height=60, font=(UI_FONT, 21, "bold"),
                    corner_radius=BTN_RADIUS,
                    fg_color=COLOR_PILL_GRAY if key.isdigit() else COLOR_WHITE,
                    hover_color=COLOR_PILL_GRAY_HOVER,
                    border_width=0 if key.isdigit() else 1,
                    border_color=COLOR_BORDER_GRAY,
                    text_color=COLOR_PRIMARY_TEXT,
                    command=lambda k=key: self._pin_key(k),
                ).pack(side="left", padx=5)

        ctk.CTkLabel(inner, text="Press Close to return to the kiosk",
                     font=(UI_FONT, 12), text_color=COLOR_TERTIARY_TEXT).pack(
            pady=(SPACE_MD, 0))

    def _pin_key(self, key):
        if key == "C":
            self.pin_buffer = ""
        elif key == "↩":
            self._check_pin()
            return
        elif len(self.pin_buffer) < 4:
            self.pin_buffer += key
        try:
            self.pin_dots.configure(text="  ".join(
                "●" if i < len(self.pin_buffer) else "○" for i in range(4)))
        except Exception:
            pass
        if len(self.pin_buffer) == 4:
            self.after(120, self._check_pin)

    def _check_pin(self):
        if self.pin_buffer == str(ADMIN_PIN):
            self._build_panel()
        else:
            self.pin_buffer = ""
            try:
                self.pin_dots.configure(text="○  ○  ○  ○")
                self.pin_msg.configure(text="Wrong PIN, try again")
            except Exception:
                pass

    def _build_panel(self):
        self._clear_body()
        self.refresh_btn.pack(side="right", padx=(0, SPACE_SM))

        content = ctk.CTkFrame(self.body, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        stats = ctk.CTkFrame(content, fg_color="transparent", height=128)
        stats.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_MD))
        stats.grid_propagate(False)
        for col in range(3):
            stats.grid_columnconfigure(col, weight=1, uniform="stats")

        self.revenue_lbl, self.revenue_sub = self._stat_card(
            stats, 0, "REVENUE TODAY", "₱", COLOR_LIGHT_BLUE_BG, COLOR_PRIMARY_BLUE)
        self.jobs_lbl, self.jobs_sub = self._stat_card(
            stats, 1, "JOBS TODAY", "✓", SUCCESS_BG, COLOR_SUCCESS_DARK)
        self.pages_lbl, self.pages_sub = self._stat_card(
            stats, 2, "PAGES TODAY", "▤", COLOR_AMBER_BG, COLOR_AMBER_TEXT)

        middle = ctk.CTkFrame(content, fg_color="transparent")
        middle.grid(row=1, column=0, sticky="nsew")
        middle.grid_rowconfigure(0, weight=1)
        middle.grid_columnconfigure(0, weight=3)
        middle.grid_columnconfigure(1, weight=2)

        self._build_activity(middle)
        self._build_status(middle)
        self._build_operations(content)

        self._paint_sim_btn()
        self._load_sales()
        self._load_status()

    def _stat_card(self, parent, col, label, icon, icon_bg, icon_fg):
        card = _card(parent)
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0, SPACE_SM) if col < 2 else 0)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=14)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=(UI_FONT, 11, "bold"),
                     text_color=COLOR_TERTIARY_TEXT).pack(side="left")

        badge = ctk.CTkFrame(top, width=30, height=30, fg_color=icon_bg,
                             corner_radius=9)
        badge.pack(side="right")
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=icon, font=(UI_FONT, 15, "bold"),
                     text_color=icon_fg).pack(expand=True)

        value = ctk.CTkLabel(inner, text="…", font=(UI_FONT, 30, "bold"),
                             text_color=COLOR_PRIMARY_TEXT, anchor="w")
        value.pack(fill="x", pady=(2, 0))

        sub = ctk.CTkLabel(inner, text="", font=(UI_FONT, 12),
                           text_color=COLOR_TERTIARY_TEXT, anchor="w")
        sub.pack(fill="x")
        return value, sub

    def _activity_grid(self, parent):
        parent.grid_columnconfigure(0, minsize=58, weight=0)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_columnconfigure(2, minsize=70, weight=0)
        parent.grid_columnconfigure(3, minsize=58, weight=0)
        parent.grid_columnconfigure(4, minsize=76, weight=0)

    def _build_activity(self, parent):
        card = _card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_LG, pady=(18, 16))

        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Recent activity", font=(UI_FONT, 19, "bold"),
                     text_color=COLOR_PRIMARY_TEXT).pack(anchor="w")
        ctk.CTkLabel(titles, text="Completed jobs and payments",
                     font=(UI_FONT, 12), text_color=COLOR_SECONDARY_TEXT).pack(
            anchor="w", pady=(2, 0))

        pill = ctk.CTkFrame(head, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        pill.pack(side="right")
        self.jobs_pill_lbl = ctk.CTkLabel(pill, text="0 JOBS",
                                          font=(UI_FONT, 11, "bold"),
                                          text_color=COLOR_SECONDARY_TEXT)
        self.jobs_pill_lbl.pack(padx=12, pady=5)

        ctk.CTkFrame(inner, height=1, fg_color=COLOR_BORDER_GRAY).pack(
            fill="x", pady=(SPACE_SM, 0))

        self.table_head = ctk.CTkFrame(inner, fg_color="transparent")
        self.table_head.pack(fill="x", pady=(SPACE_SM, SPACE_XS))
        self._activity_grid(self.table_head)
        for col, text, anchor in (
            (0, "TIME", "w"), (1, "FILE", "w"), (2, "MODE", "w"),
            (3, "PAGES", "e"), (4, "PAID", "e"),
        ):
            ctk.CTkLabel(self.table_head, text=text, font=(UI_FONT, 11, "bold"),
                         text_color=COLOR_TERTIARY_TEXT, anchor=anchor).grid(
                row=0, column=col, sticky="ew",
                padx=(10, 0) if col in (0, 1) else (0, 10))

        self.activity_list = ctk.CTkFrame(inner, fg_color="transparent")
        self.activity_list.pack(fill="both", expand=True)

        self.updated_lbl = ctk.CTkLabel(inner, text="", font=(UI_FONT, 11),
                                        text_color=COLOR_TERTIARY_TEXT, anchor="e")
        self.updated_lbl.pack(fill="x", pady=(SPACE_XS, 0))

    def _build_status(self, parent):
        card = _card(parent)
        card.grid(row=0, column=1, sticky="nsew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_LG, pady=(18, 16))

        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Machine status", font=(UI_FONT, 19, "bold"),
                     text_color=COLOR_PRIMARY_TEXT).pack(anchor="w")

        self.status_badge = ctk.CTkFrame(head, fg_color=COLOR_PILL_GRAY,
                                         corner_radius=PILL_RADIUS)
        self.status_badge.pack(side="right")
        self.status_badge_lbl = ctk.CTkLabel(self.status_badge, text="CHECKING",
                                             font=(UI_FONT, 11, "bold"),
                                             text_color=COLOR_SECONDARY_TEXT)
        self.status_badge_lbl.pack(padx=12, pady=5)

        pblock = ctk.CTkFrame(inner, fg_color=SOFT_BG, corner_radius=BTN_RADIUS)
        pblock.pack(fill="x", pady=(SPACE_SM, 0))
        picon = ctk.CTkFrame(pblock, width=42, height=42, fg_color=COLOR_LIGHT_BLUE_BG,
                             corner_radius=12)
        picon.pack(side="left", padx=(12, 10), pady=10)
        picon.pack_propagate(False)
        ctk.CTkLabel(picon, text="🖨", font=(UI_FONT, 18)).pack(expand=True)

        ptext = ctk.CTkFrame(pblock, fg_color="transparent")
        ptext.pack(side="left", fill="x", expand=True, pady=10)
        self.printer_name_lbl = ctk.CTkLabel(ptext, text="Checking printer…",
                                              font=(UI_FONT, 16, "bold"),
                                              text_color=COLOR_PRIMARY_TEXT, anchor="w")
        self.printer_name_lbl.pack(fill="x")
        self.printer_note_lbl = ctk.CTkLabel(ptext, text="", height=16,
                                              font=(UI_FONT, 11),
                                              text_color=COLOR_TERTIARY_TEXT, anchor="w")
        self.printer_note_lbl.pack(fill="x", pady=(2, 0))

        details = ctk.CTkFrame(inner, fg_color="transparent")
        details.pack(fill="x", pady=(SPACE_SM, 0))
        for col in range(2):
            details.grid_columnconfigure(col, weight=1, uniform="detail")
        for row in range(2):
            details.grid_rowconfigure(row, weight=1, uniform="detailrow")

        self.health_lbl = self._status_tile(details, "HEALTH", 0, 0)
        self.payment_lbl = self._status_tile(details, "PAYMENT MODE", 0, 1)
        self.credit_lbl = self._status_tile(details, "CURRENT CREDIT", 1, 0)
        self.queue_lbl = self._status_tile(details, "PRINT QUEUE", 1, 1)

        tip = ctk.CTkFrame(inner, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=12)
        tip.pack(fill="x", pady=(SPACE_SM, 0))
        ctk.CTkLabel(tip, text="Tip: Run a test print before opening; clear temp files after each customer.",
                     font=(UI_FONT, 12), text_color=COLOR_SECONDARY_TEXT,
                     anchor="w", justify="left", wraplength=780).pack(
            fill="x", padx=12, pady=8)

        self.checked_lbl = ctk.CTkLabel(inner, text="", font=(UI_FONT, 11),
                                         text_color=COLOR_TERTIARY_TEXT, anchor="w")
        self.checked_lbl.pack(fill="x", pady=(SPACE_XS, 0))

    def _status_tile(self, parent, label, row, col):
        tile = ctk.CTkFrame(parent, fg_color=SOFT_BG, corner_radius=12)
        tile.grid(row=row, column=col, sticky="nsew",
                  padx=(0, SPACE_XS) if col == 0 else 0,
                  pady=(0, SPACE_XS) if row == 0 else 0)
        box = ctk.CTkFrame(tile, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=12, pady=(9, 8))
        ctk.CTkLabel(box, text=label, font=(UI_FONT, 10, "bold"),
                     text_color=COLOR_TERTIARY_TEXT, anchor="w").pack(fill="x")
        value = ctk.CTkLabel(box, text="…", font=(UI_FONT, 13, "bold"),
                             text_color=COLOR_PRIMARY_TEXT, anchor="w",
                             justify="left", wraplength=250)
        value.pack(fill="x", pady=(2, 0))
        return value

    def _build_operations(self, parent):
        card = _card(parent)
        card.grid(row=2, column=0, sticky="ew", pady=(SPACE_MD, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_LG, pady=(18, 16))

        titles = ctk.CTkFrame(inner, fg_color="transparent")
        titles.pack(fill="x")
        ctk.CTkLabel(titles, text="Operations", font=(UI_FONT, 19, "bold"),
                     text_color=COLOR_PRIMARY_TEXT).pack(anchor="w")
        ctk.CTkLabel(titles, text="Maintenance and session controls",
                     font=(UI_FONT, 12), text_color=COLOR_SECONDARY_TEXT).pack(
            anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(SPACE_SM, 0))
        for col in range(3):
            actions.grid_columnconfigure(col, weight=1, uniform="ops")

        self.test_btn = self._action_button(actions, "🖨  Test print", self._test_print, "primary")
        self.test_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self._action_button(actions, "♻  Clear temp files", self._clear_temp).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew")
        self._action_button(actions, "₱  Reset credit", self._reset_credit).grid(
            row=0, column=2, padx=5, pady=5, sticky="ew")
        self._action_button(actions, "↻  Restart app", self._restart).grid(
            row=1, column=0, padx=5, pady=5, sticky="ew")
        self.sim_btn = self._action_button(actions, "🧪  Simulation", self._toggle_sim)
        self.sim_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self._action_button(actions, "⏻  Exit kiosk", self._exit, "danger").grid(
            row=1, column=2, padx=5, pady=5, sticky="ew")

        self.feedback = ctk.CTkFrame(inner, fg_color=SOFT_BG, corner_radius=12)
        self.feedback.pack(fill="x", pady=(SPACE_SM, 0))
        self.feedback_dot = ctk.CTkLabel(self.feedback, text="●", font=(UI_FONT, 12),
                                          text_color=COLOR_TERTIARY_TEXT)
        self.feedback_dot.pack(side="left", padx=(12, 6), pady=8)
        self.msg_lbl = ctk.CTkLabel(self.feedback, text="Panel ready",
                                     font=(UI_FONT, 12, "bold"),
                                     text_color=COLOR_SECONDARY_TEXT, anchor="w")
        self.msg_lbl.pack(side="left", pady=8)
        self.feedback_meta = ctk.CTkLabel(
            self.feedback, text="Changes apply immediately",
            font=(UI_FONT, 11), text_color=COLOR_TERTIARY_TEXT, anchor="e")
        self.feedback_meta.pack(side="right", padx=12, pady=8)
        self.prog = ctk.CTkProgressBar(self.feedback, width=200, height=8,
                                        fg_color=COLOR_PILL_GRAY,
                                        progress_color=COLOR_PRIMARY_BLUE,
                                        corner_radius=4)
        self.prog.set(0)

    def _action_button(self, parent, text, command, variant="secondary"):
        if variant == "primary":
            fg, hover, color = COLOR_PRIMARY_BLUE, COLOR_PRIMARY_BLUE_HOVER, "#FFFFFF"
        elif variant == "danger":
            fg, hover, color = DANGER_BG, "#F9D3CF", COLOR_WARNING_RED
        else:
            fg, hover, color = COLOR_PILL_GRAY, COLOR_PILL_GRAY_HOVER, COLOR_PRIMARY_TEXT
        return ctk.CTkButton(
            parent, text=text, height=54, font=(UI_FONT, 14, "bold"),
            corner_radius=BTN_RADIUS, fg_color=fg, hover_color=hover,
            text_color=color, command=command,
        )

    def _paint_sim_btn(self):
        try:
            on = self.coin_reader.is_simulation_mode()
        except Exception:
            on = False
        try:
            self.sim_btn.configure(
                text="🧪  Simulation  ON" if on else "🧪  Simulation  OFF",
                fg_color=COLOR_AMBER_BG if on else COLOR_PILL_GRAY,
                hover_color="#FDE9B5" if on else COLOR_PILL_GRAY_HOVER,
                text_color=COLOR_AMBER_TEXT if on else COLOR_PRIMARY_TEXT,
            )
        except Exception:
            pass

    def _clear_body(self):
        for child in list(self.body.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

    def _load_sales(self):
        try:
            from core import sales_log
            t = sales_log.today_summary()
            a = sales_log.all_time_summary()
            self.revenue_lbl.configure(text=f"₱{t['revenue']:.0f}")
            self.revenue_sub.configure(text=f"All time ₱{a['revenue']:.0f}")
            self.jobs_lbl.configure(text=str(t["jobs"]))
            self.jobs_sub.configure(text=f"All time {a['jobs']}")
            self.pages_lbl.configure(text=str(t["pages"]))
            self.pages_sub.configure(text="Includes multiple copies")
            self.jobs_pill_lbl.configure(
                text=f"{t['jobs']} JOB" + ("" if t["jobs"] == 1 else "S"))
            self._render_activity(sales_log.recent(5))
        except Exception:
            try:
                self.revenue_lbl.configure(text="—")
                self.revenue_sub.configure(text="Could not read sales log")
                self.jobs_lbl.configure(text="—")
                self.jobs_sub.configure(text="Check the sales log")
                self.pages_lbl.configure(text="—")
                self.pages_sub.configure(text="Then tap Refresh")
                self.jobs_pill_lbl.configure(text="LOG ERROR")
                self._render_activity([], "Could not read the sales log",
                                      "Check the sales log, then tap Refresh.")
            except Exception:
                pass

    def _render_activity(self, rows, empty_title="No sales logged yet",
                         empty_note="Completed print jobs will appear here."):
        for child in list(self.activity_list.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        if not rows:
            self.table_head.pack_forget()
            empty = ctk.CTkFrame(self.activity_list, fg_color="transparent")
            empty.pack(fill="both", expand=True)
            block = ctk.CTkFrame(empty, fg_color="transparent")
            block.place(relx=0.5, rely=0.45, anchor="center")
            badge = ctk.CTkFrame(block, width=54, height=54,
                                 fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=16)
            badge.pack()
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text="▤", font=(UI_FONT, 24),
                         text_color=COLOR_PRIMARY_BLUE).pack(expand=True)
            ctk.CTkLabel(block, text=empty_title, font=(UI_FONT, 17, "bold"),
                         text_color=COLOR_PRIMARY_TEXT).pack(pady=(12, 2))
            ctk.CTkLabel(block, text=empty_note, font=(UI_FONT, 12),
                         text_color=COLOR_TERTIARY_TEXT).pack()
            self.updated_lbl.configure(text=f"Updated {time.strftime('%H:%M')}")
            return

        self.table_head.pack_forget()
        self.table_head.pack(fill="x", pady=(SPACE_SM, SPACE_XS),
                             before=self.activity_list)

        for index, entry in enumerate(rows):
            row = ctk.CTkFrame(
                self.activity_list,
                fg_color=SOFT_BG if index % 2 == 0 else "transparent",
                corner_radius=10,
            )
            row.pack(fill="x", pady=2)
            self._activity_grid(row)

            name = str(entry.get("file", ""))
            if len(name) > 58:
                name = name[:55] + "…"
            mode = str(entry.get("mode", "")).lower()
            is_color = mode not in ("", "bw", "b&w", "black", "blackwhite")
            mode_text = "COLOR" if is_color else "B&W"
            mode_bg = COLOR_LIGHT_BLUE_BG if is_color else COLOR_PILL_GRAY
            mode_fg = COLOR_PRIMARY_BLUE if is_color else COLOR_SECONDARY_TEXT
            pages = int(entry.get("pages", 0) or 0) * int(entry.get("copies", 1) or 1)
            paid = float(entry.get("paid", 0) or 0)

            ctk.CTkLabel(row, text=str(entry.get("time", ""))[:5],
                         font=(UI_FONT, 13, "bold"), text_color=COLOR_PRIMARY_TEXT,
                         anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 0),
                                          pady=8)
            ctk.CTkLabel(row, text=name, font=(UI_FONT, 13),
                         text_color=COLOR_PRIMARY_TEXT, anchor="w").grid(
                row=0, column=1, sticky="ew", padx=(10, 0), pady=8)
            ctk.CTkLabel(row, text=mode_text, font=(UI_FONT, 10, "bold"),
                         fg_color=mode_bg, text_color=mode_fg, corner_radius=7,
                         width=54, height=24).grid(row=0, column=2, sticky="w",
                                                    padx=(0, 10), pady=6)
            ctk.CTkLabel(row, text=str(pages), font=(UI_FONT, 13, "bold"),
                         text_color=COLOR_PRIMARY_TEXT, anchor="e").grid(
                row=0, column=3, sticky="e", padx=(0, 10), pady=8)
            ctk.CTkLabel(row, text=f"₱{paid:.0f}", font=(UI_FONT, 13, "bold"),
                         text_color=COLOR_PRIMARY_BLUE, anchor="e").grid(
                row=0, column=4, sticky="e", padx=(0, 10), pady=8)

        self.updated_lbl.configure(
            text=f"Showing latest {len(rows)}  ·  Updated {time.strftime('%H:%M')}")

    def _load_status(self):
        try:
            from core.printer import Printer
            p = Printer()
            printer_name = p.get_printer_name()
            state, msg = p.get_status()
            jobs = p.get_job_count()
            credit = self.coin_reader.get_credit()
            sim = self.coin_reader.is_simulation_mode()
            try:
                hardware = self.coin_reader.is_hardware_available()
            except Exception:
                hardware = not sim

            if sim:
                self.printer_name_lbl.configure(
                    text=printer_name or "Simulation mode")
                self.printer_note_lbl.configure(
                    text="Prints are saved to temp/output.",
                    text_color=COLOR_AMBER_TEXT)
                self.health_lbl.configure(
                    text="Simulation mode", text_color=COLOR_AMBER_TEXT)
            else:
                self.printer_name_lbl.configure(
                    text=printer_name or "No printer detected")
                if not printer_name:
                    note = "Connect a printer for physical copies."
                elif state == "error":
                    note = "Check power and the USB connection."
                else:
                    note = "Windows print queue"
                self.printer_note_lbl.configure(
                    text=note,
                    text_color=COLOR_WARNING_RED if state == "error" else COLOR_TERTIARY_TEXT)
                self.health_lbl.configure(
                    text=msg or "Unknown",
                    text_color=COLOR_WARNING_RED if state == "error"
                    else COLOR_AMBER_TEXT if state == "warning" else COLOR_PRIMARY_TEXT)
            if sim:
                payment_text, payment_color = "Simulation", COLOR_AMBER_TEXT
            elif hardware:
                payment_text, payment_color = "Coin slot", COLOR_PRIMARY_TEXT
            else:
                payment_text, payment_color = "Coin slot offline", COLOR_WARNING_RED
            self.payment_lbl.configure(text=payment_text, text_color=payment_color)
            self.credit_lbl.configure(text=f"₱{credit}")
            self.queue_lbl.configure(
                text=f"{jobs} job" + ("" if jobs == 1 else "s"))
            self.checked_lbl.configure(text=f"Last checked {time.strftime('%H:%M:%S')}")
            self._paint_status_badge("sim" if sim else state,
                                     "simulation" if sim else msg)
        except Exception:
            try:
                self.printer_name_lbl.configure(text="Status unavailable")
                self.printer_note_lbl.configure(
                    text="Could not read the printer.", text_color=COLOR_WARNING_RED)
                self.health_lbl.configure(text="Unavailable",
                                          text_color=COLOR_WARNING_RED)
                self.payment_lbl.configure(text="Unknown")
                self.credit_lbl.configure(text="—")
                self.queue_lbl.configure(text="—")
                self._paint_status_badge("error", "unavailable")
            except Exception:
                pass

    def _paint_status_badge(self, state, msg):
        low = (msg or "").lower()
        if state == "sim":
            label = "SIMULATION"
            bg, fg = COLOR_AMBER_BG, COLOR_AMBER_TEXT
        elif state == "error":
            label = "OFFLINE" if "offline" in low else "ATTENTION"
            bg, fg = DANGER_BG, COLOR_WARNING_RED
        elif state == "warning":
            label = "NO PRINTER" if "no printer" in low else "CHECK"
            bg, fg = COLOR_AMBER_BG, COLOR_AMBER_TEXT
        else:
            label = "READY"
            bg, fg = SUCCESS_BG, COLOR_SUCCESS_DARK
        try:
            self.status_badge.configure(fg_color=bg)
            self.status_badge_lbl.configure(text=label, text_color=fg)
        except Exception:
            pass

    def _say(self, text, ok=True):
        try:
            self.msg_lbl.configure(
                text=text,
                text_color=COLOR_SUCCESS_DARK if ok else COLOR_WARNING_RED)
            self.feedback_dot.configure(
                text_color=COLOR_SUCCESS_GREEN if ok else COLOR_WARNING_RED)
        except Exception:
            pass

    def _refresh_panel(self):
        if not hasattr(self, "activity_list"):
            return
        self._load_sales()
        self._load_status()
        self._say("Dashboard refreshed.")

    def _test_print(self):
        if self._test_running:
            return
        self._test_running = True
        self._say("Sending test page…")
        try:
            self.test_btn.configure(state="disabled", text="🖨  Working…")
        except Exception:
            pass
        try:
            self.prog.pack(side="right", padx=(12, 12), pady=8)
            self.prog.configure(mode="indeterminate")
            self.prog.start()
        except Exception:
            pass

        def work():
            ok = False
            sim = False
            try:
                from core.printer import Printer
                from PIL import Image, ImageDraw
                p = Printer()
                img = Image.new("RGB", (1240, 1754), "white")
                d = ImageDraw.Draw(img)
                d.text((90, 120), "ECA Print - Test Page", fill="black")
                d.text((90, 180), time.strftime("%Y-%m-%d %X"), fill="black")
                d.line((90, 220, 1150, 220), fill="black", width=3)
                try:
                    from config import SIMULATION_MODE
                    sim = bool(SIMULATION_MODE)
                except Exception:
                    sim = False
                try:
                    if self.coin_reader.is_simulation_mode():
                        sim = True
                except Exception:
                    pass
                try:
                    if not p.get_printer_name():
                        sim = True
                except Exception:
                    sim = True
                if sim:
                    os.makedirs("temp/output", exist_ok=True)
                    img.save(os.path.join("temp/output", "sim_test_page.png"))
                    ok = True
                else:
                    ok = bool(p.print_image(img, color_mode="B&W", paper_size="a4"))
                if ok and not sim:
                    try:
                        p.wait_until_idle(timeout=120)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Test print error: {e}")
            try:
                self.after(0, lambda: self._test_done(ok, sim))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _test_done(self, ok, sim):
        self._test_running = False
        try:
            self.prog.stop()
            self.prog.configure(mode="determinate")
            self.prog.set(1 if ok else 0)
        except Exception:
            pass
        try:
            self.test_btn.configure(state="normal", text="🖨  Test print")
        except Exception:
            pass
        if not ok:
            self._say("Test print failed.", ok=False)
        elif sim:
            self._say("Test page saved (simulation mode).", ok=True)
        else:
            self._say("Test page printed.", ok=True)
        self._load_status()

    def _clear_temp(self):
        removed = 0
        for pattern in ("temp/output/*", "temp/converted/*", "temp/uploads/*"):
            for path in glob.glob(pattern):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        removed += 1
                except Exception:
                    pass
        self._say(f"Cleared {removed} temp file(s).")
        self._load_status()

    def _reset_credit(self):
        try:
            self.coin_reader.reset_credit()
            self._say("Credit reset to ₱0.")
        except Exception:
            self._say("Could not reset credit.", ok=False)
        self._load_status()

    def _toggle_sim(self):
        try:
            new = not self.coin_reader.is_simulation_mode()
            self.coin_reader.set_simulation_mode(new)
            try:
                import config
                config.SIMULATION_MODE = new
            except Exception:
                pass
            self._paint_sim_btn()
            self._say(f"Simulation {'ON' if new else 'OFF'}.")
            try:
                if self.on_simulation_change:
                    self.on_simulation_change(new)
            except Exception:
                pass
        except Exception:
            self._say("Could not toggle simulation.", ok=False)
        self._load_status()

    def _restart(self):
        try:
            if self.on_restart:
                self.on_restart()
                return
        except Exception:
            pass
        self._say("Restart not available.", ok=False)

    def _exit(self):
        try:
            if self.on_exit:
                self.on_exit()
                return
        except Exception:
            pass
        self._say("Exit not available.", ok=False)

    def _close(self):
        try:
            self.on_back()
        except Exception:
            pass
