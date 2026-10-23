import customtkinter as ctk
import os
import winsound
from config import (
    CARD_BG,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    TERTIARY_TEXT,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    SUCCESS_GREEN,
    WARNING_RED,
    WARNING_RED_HOVER,
    AMBER_TEXT,
    BORDER_GRAY,
    PILL_GRAY,
    PILL_GRAY_HOVER,
    BTN_RADIUS,
    UI_FONT,
)
from ui.base_view import BaseView


class PaymentView(BaseView):
    def __init__(self, master, filepath, due, print_mode, back_callback, coin_reader,
                 start_page=1, end_page=None, copies=1, paper_size=None):
        super().__init__(master)
        self.filepath = filepath
        self.due_amount = due
        self.print_mode = print_mode
        self.paper_size = paper_size
        self.start_page = start_page or 1
        self.end_page = end_page
        try:
            self.copies = max(1, int(copies or 1))
        except Exception:
            self.copies = 1
        self.switch_callback = back_callback
        self.back_callback = back_callback
        self.coin_reader = coin_reader

        if end_page is None:
            try:
                from core.file_reader import FileReader as _FR
                _total = _FR.get_total_pages_fast(filepath)
            except Exception:
                _total = None
            if _total:
                self.end_page = _total

        # Outer wrapper fills the whole view, centers content vertically.
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(expand=True, fill="both", padx=40, pady=12)

        center = ctk.CTkFrame(wrap, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ---- White card (auto-sizing — never fixed height) ----
        card = ctk.CTkFrame(center, fg_color=CARD_BG, corner_radius=24,
                            border_width=1, border_color=BORDER_GRAY)
        card.pack(padx=10, pady=6)

        ctk.CTkLabel(card, text="\U0001F4B3  Checkout", font=(UI_FONT, 28, "bold"),
                     text_color=PRIMARY_TEXT).pack(pady=(26, 2), padx=40)

        mode_tag = "B&W" if (print_mode or "bw") == "bw" else "Color"
        try:
            end_txt = self.end_page if self.end_page else "?"
            fname = os.path.basename(filepath or "")
            if len(fname) > 34:
                fname = fname[:32] + "…"
            job = (f"{fname}  \u2022  {mode_tag}  \u2022  "
                   f"Pages {self.start_page}\u2013{end_txt}  \u2022  "
                   f"{self.copies} cop{'y' if self.copies == 1 else 'ies'}")
        except Exception:
            job = mode_tag
        job_pill = ctk.CTkFrame(card, fg_color=PILL_GRAY, corner_radius=14)
        job_pill.pack(pady=8, padx=30)
        ctk.CTkLabel(job_pill, text=job, font=(UI_FONT, 15),
                     text_color=SECONDARY_TEXT).pack(padx=18, pady=7)

        ctk.CTkLabel(card, text="TOTAL DUE", font=(UI_FONT, 14, "bold"),
                     text_color=TERTIARY_TEXT).pack(pady=(8, 0))
        self.due_big = ctk.CTkLabel(card, text=f"\u20B1{due}", font=(UI_FONT, 56, "bold"),
                                    text_color=PRIMARY_TEXT)
        self.due_big.pack(pady=(0, 2), padx=30)

        self.credit_lbl = ctk.CTkLabel(card, text="", font=(UI_FONT, 17),
                                       text_color=SECONDARY_TEXT)
        self.credit_lbl.pack()
        self.remain_lbl = ctk.CTkLabel(card, text="", font=(UI_FONT, 17, "bold"),
                                       text_color=AMBER_TEXT)
        self.remain_lbl.pack(pady=2)
        self.payment_note_lbl = ctk.CTkLabel(card, text="", font=(UI_FONT, 15, "bold"),
                                             text_color=WARNING_RED)
        self.payment_note_lbl.pack(pady=(2, 0))
        self.prompt_lbl = ctk.CTkLabel(card, text="", font=(UI_FONT, 16),
                                       text_color=SECONDARY_TEXT)
        self.prompt_lbl.pack(pady=2)

        # Reserved slot for the confirm button so showing/hiding it
        # never shifts or clips the card. Fixed width so the full
        # "Confirm & Start Printing" text always fits.
        self.confirm_slot = ctk.CTkFrame(card, fg_color="transparent",
                                         width=580, height=76)
        self.confirm_slot.pack(pady=(2, 6), padx=20)
        self.confirm_slot.pack_propagate(False)

        self.confirm_btn = ctk.CTkButton(
            self.confirm_slot, text="Confirm & Start Printing",
            height=68, width=540, font=(UI_FONT, 20, "bold"),
            fg_color=PRIMARY_BLUE, hover_color=PRIMARY_BLUE_HOVER,
            text_color="#FFFFFF", corner_radius=BTN_RADIUS,
            command=self._trigger_print,
        )

        self.paper_lbl = ctk.CTkLabel(card, text="\U0001F5A8\uFE0F  Please load the exact sheet count into the tray",
                                      font=(UI_FONT, 14), text_color=TERTIARY_TEXT)
        self.paper_lbl.pack(pady=(2, 18), padx=30)

        # Coin row (outside the card, centered). Built ONLY in simulation
        # mode: on a real machine coins arrive through the slot, and
        # on-screen buttons would mint free credit (a cheating vector).
        try:
            show_sim_coins = bool(coin_reader.is_simulation_mode())
        except Exception:
            show_sim_coins = False
        self.coin_row = None
        if show_sim_coins:
            coins = ctk.CTkFrame(center, fg_color="transparent")
            coins.pack(pady=12)
            self.coin_row = coins
            for amt in (1, 5, 10):
                ctk.CTkButton(
                    coins, text=f"+ \u20B1{amt}", font=(UI_FONT, 22, "bold"),
                    width=170, height=72, corner_radius=BTN_RADIUS,
                    fg_color=PRIMARY_BLUE, hover_color=PRIMARY_BLUE_HOVER,
                    text_color="#FFFFFF",
                    command=lambda a=amt: self._insert_coin(a),
                ).pack(side="left", padx=10)

        # Cancel + back
        row2 = ctk.CTkFrame(center, fg_color="transparent")
        row2.pack()
        self.actions_row = row2
        ctk.CTkButton(row2, text="Cancel / Refund", font=(UI_FONT, 17, "bold"),
                      width=240, height=60, corner_radius=BTN_RADIUS,
                      fg_color="transparent", hover_color=PILL_GRAY_HOVER,
                      border_width=1, border_color=BORDER_GRAY,
                      text_color=WARNING_RED, command=self._on_cancel).pack(side="left", padx=8)
        ctk.CTkButton(row2, text="\u2039  Back", font=(UI_FONT, 17, "bold"),
                      width=200, height=60, corner_radius=BTN_RADIUS,
                      fg_color=PILL_GRAY, hover_color=PILL_GRAY_HOVER,
                      text_color=PRIMARY_TEXT, command=self._on_back).pack(side="left", padx=8)

        self._last_credit = None
        self._last_remaining = None
        self._is_paid = None
        self._confirm_visible = False
        self._refresh_state()

    def _trigger_print(self):
        try:
            from core.printer import printer_block_reason
            problem = printer_block_reason()
        except Exception:
            problem = None
        if problem:
            try:
                self.prompt_lbl.configure(
                    text=f"{problem} \u2014 printing is unavailable. Please ask staff.",
                    text_color=WARNING_RED)
            except Exception:
                pass
            try:
                winsound.Beep(400, 250)
            except Exception:
                pass
            return
        self.switch_callback("printing", self.filepath, self.due_amount, self.print_mode,
                             self.start_page, self.end_page, self.copies, self.paper_size)

    def _set_coins_visible(self, show):
        """Hide the insert buttons once fully paid, so Confirm is the only
        primary action. Restored if credit is later cleared (expiry)."""
        row = getattr(self, "coin_row", None)
        if row is None:
            return
        try:
            if show:
                if not row.winfo_ismapped():
                    row.pack(pady=12, before=self.actions_row)
            else:
                row.pack_forget()
        except Exception:
            pass

    def _on_paid(self):
        """Called when the user taps Confirm & Start Printing.
        Switches to the printing screen and hides coin controls."""
        # Credit is already validated in _refresh_state; just ensure coin row
        # is hidden after payment so Confirm remains the sole primary action.
        self._set_coins_visible(False)
        # Ensure confirm button is centered and visible.
        try:
            self._set_confirm_visible(True)
        except Exception:
            pass

    def _set_confirm_visible(self, show):
        if show == self._confirm_visible:
            return
        self._confirm_visible = show
        try:
            if show:
                self.confirm_btn.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self.confirm_btn.place_forget()
        except Exception:
            pass

    def _refresh_state(self):
        try:
            current_credit = self.coin_reader.get_credit()
        except Exception:
            return
        remaining = max(0, self.due_amount - current_credit)
        is_paid = current_credit >= self.due_amount
        self._refresh_payment_note(is_paid)
        try:
            if current_credit != self._last_credit:
                self._last_credit = current_credit
                self.credit_lbl.configure(text=f"Inserted  \u20B1{current_credit}  of  \u20B1{self.due_amount}")
            if remaining != self._last_remaining:
                self._last_remaining = remaining
                if is_paid:
                    self.remain_lbl.configure(text="\u2713  Fully paid", text_color=SUCCESS_GREEN)
                else:
                    self.remain_lbl.configure(text=f"Insert \u20B1{remaining} more", text_color=AMBER_TEXT)
            if is_paid != self._is_paid:
                self._is_paid = is_paid
                self._set_coins_visible(not is_paid)
                # Mute the Cancel button when paid so the primary action is Confirm
                try:
                    self._update_cancel_appearance(is_paid)
                except Exception:
                    pass
                if is_paid:
                    self.prompt_lbl.configure(text="Paper loaded? Tap Confirm to start \U0001F5A8\uFE0F")
                else:
                    self.prompt_lbl.configure(text="")
                self._set_confirm_visible(is_paid)
        except Exception:
            pass

    def _refresh_payment_note(self, is_paid):
        try:
            available = self.coin_reader.is_payment_available()
        except Exception:
            try:
                available = bool(self.coin_reader.is_simulation_mode())
            except Exception:
                available = True
        text = "" if available or is_paid else "Coin slot offline \u2014 please ask staff."
        try:
            self.payment_note_lbl.configure(text=text)
        except Exception:
            pass

    def update_payment_status(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._refresh_state()

    def _update_cancel_appearance(self, is_paid):
        """Tweak Cancel button look: dimmed when paid, restored when unpaid."""
        try:
            if is_paid:
                self.actions_row.winfo_children()[0].configure(
                    fg_color="#FFFFFF", hover_color=PILL_GRAY_HOVER,
                    border_color=BORDER_GRAY, text_color=SECONDARY_TEXT)
            else:
                self.actions_row.winfo_children()[0].configure(
                    fg_color="transparent", hover_color=PILL_GRAY_HOVER,
                    border_width=1, border_color=BORDER_GRAY, text_color=WARNING_RED)
        except Exception:
            pass

    def _insert_coin(self, amount):
        # Simulation only. On a real machine with a coin slot attached, these
        # on-screen buttons must never add free credit (that would be a way
        # to cheat). Same rule as the 'c' key in main.py.
        try:
            if not self.coin_reader.is_simulation_mode():
                return
        except Exception:
            return
        try:
            self.coin_reader.add_credit(amount)
        except Exception:
            pass

        try:
            winsound.Beep(1200, 100)
        except Exception:
            pass
        self._refresh_state()

    def _on_cancel(self):
        # Cancelling must NOT wipe the customer's credit - there is no way to
        # give coins back, so keeping the balance lets them print another file
        # instead of losing their money. (Credit already persists across
        # returning to the welcome screen.)
        try:
            self.back_callback("file_browser")
        except Exception:
            pass

    def _on_back(self):
        self.back_callback("file_browser")

    def update_credit_display(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._refresh_state()
