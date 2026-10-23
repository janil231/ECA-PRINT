import customtkinter as ctk
from config import (
    COLOR_APP_BG,
    COLOR_CARD_BG,
    COLOR_PRIMARY_BLUE,
    COLOR_SUCCESS_GREEN,
    COLOR_WARNING_RED,
    COLOR_AMBER_TEXT,
    COLOR_BORDER_GRAY,
    COLOR_PILL_GRAY,
    COLOR_PRIMARY_TEXT,
    COLOR_SECONDARY_TEXT,
    PILL_RADIUS,
    UI_FONT,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
    SPACE_LG,
)

TITLE_FONT = (UI_FONT, 20, "bold")
CREDIT_FONT = (UI_FONT, 18, "bold")
BADGE_FONT = (UI_FONT, 12, "bold")
WARN_BG = "#FDE7E6"


class HeaderBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=64, corner_radius=0, fg_color=COLOR_CARD_BG, **kwargs)
        # NOTE: do NOT pack here - main.py owns layout (single pack).
        self._last_credit = None
        self._base_status = None   # "sim" or "hw"
        self._printer_warning = None
        self._payment_warning = None

        # Left: logo + wordmark
        self.title_label = ctk.CTkLabel(
            self, text="\U0001F5A8\uFE0F  Print Vendo", font=TITLE_FONT, text_color=COLOR_PRIMARY_BLUE
        )
        self.title_label.pack(side="left", padx=SPACE_SM, pady=8)

        # Right: credit pill (dark, iOS style)
        self.credit_pill = ctk.CTkFrame(self, fg_color=COLOR_PRIMARY_TEXT, corner_radius=PILL_RADIUS)
        self.credit_pill.pack(side="right", padx=SPACE_SM, pady=6)
        self.credit_label = ctk.CTkLabel(
            self.credit_pill, text="\u20B10", font=CREDIT_FONT, text_color="#FFFFFF"
        )
        self.credit_label.pack(padx=SPACE_SM, pady=4)

        # Right: status badge (printer warning beats sim/ready)
        self.badge = ctk.CTkFrame(self, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        self.badge.pack(side="right", padx=SPACE_XS, pady=6)
        self.status_label = ctk.CTkLabel(
            self.badge, text="", font=BADGE_FONT, text_color=COLOR_SECONDARY_TEXT
        )
        self.status_label.pack(padx=SPACE_SM, pady=4)

        # Subtle bottom separator
        self.border = ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=COLOR_BORDER_GRAY)
        self.border.pack(side="bottom", fill="x")

        self._render_status()

    def update_credit(self, amount):
        if amount == self._last_credit:
            return
        self._last_credit = amount
        try:
            self.credit_label.configure(text=f"\u20B1{amount}")
        except Exception:
            pass

    def update_status(self, mode):
        is_sim = (mode is True) or (mode == "sim") or (mode == "simulation")
        self._base_status = "sim" if is_sim else "hw"
        self._render_status()

    def set_printer_warning(self, message):
        """Show a printer problem in the badge, or clear it with None."""
        new = message or None
        if new == self._printer_warning:
            return
        self._printer_warning = new
        self._render_status()

    def set_payment_warning(self, message):
        new = message or None
        if new == self._payment_warning:
            return
        self._payment_warning = new
        self._render_status()

    def _render_status(self):
        try:
            warnings = [w for w in (self._payment_warning, self._printer_warning) if w]
            if warnings:
                self.status_label.configure(
                    text=" \u2022 ".join(str(w).upper() for w in warnings),
                    text_color=COLOR_WARNING_RED)
                self.badge.configure(fg_color=WARN_BG)
            elif self._base_status == "sim":
                # Calm amber, not alarm red - sim mode is normal during demos.
                self.status_label.configure(text="SIMULATION", text_color=COLOR_AMBER_TEXT)
                self.badge.configure(fg_color=COLOR_PILL_GRAY)
            else:
                self.status_label.configure(text="READY", text_color=COLOR_SUCCESS_GREEN)
                self.badge.configure(fg_color=COLOR_PILL_GRAY)
        except Exception:
            pass
