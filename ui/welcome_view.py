import customtkinter as ctk
from config import (
    BW_PRICE_PER_PAGE,
    COLOR_PRICE_PER_PAGE,
    COLOR_CARD_BG,
    COLOR_PRIMARY_TEXT,
    COLOR_SECONDARY_TEXT,
    COLOR_TERTIARY_TEXT,
    COLOR_PRIMARY_BLUE,
    COLOR_PRIMARY_BLUE_HOVER,
    COLOR_LIGHT_BLUE_BG,
    COLOR_BORDER_GRAY,
    COLOR_PILL_GRAY,
    CARD_RADIUS,
    BTN_RADIUS,
    PILL_RADIUS,
    UI_FONT,
    FONT_HERO,
    FONT_H1,
    FONT_TITLE,
    FONT_BODY,
    FONT_BUTTON,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
    SPACE_LG,
    SPACE_XL,
    SPACE_2XL,
)
from core.coin_reader import CoinReader
from ui.base_view import BaseView


def _icon_badge(parent, glyph, size=88, glyph_size=42):
    badge = ctk.CTkFrame(parent, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=size // 2,
                         width=size, height=size)
    badge.pack(pady=(0, SPACE_SM))
    badge.pack_propagate(False)
    ctk.CTkLabel(badge, text=glyph, font=(UI_FONT, glyph_size),
                 text_color=COLOR_PRIMARY_BLUE).pack(expand=True)


def _check_row(parent, text):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=3)
    ctk.CTkLabel(row, text="\u2713", font=(UI_FONT, 17, "bold"),
                 text_color=COLOR_PRIMARY_BLUE).pack(side="left", padx=(0, SPACE_XS))
    ctk.CTkLabel(row, text=text, font=(UI_FONT, 17), text_color=COLOR_SECONDARY_TEXT,
                 anchor="w").pack(side="left")


class WelcomeView(BaseView):
    def __init__(self, master, coin_reader: CoinReader, switch_view):
        super().__init__(master)
        self.coin_reader = coin_reader
        self.switch_view = switch_view

        page = ctk.CTkFrame(self, fg_color="transparent")
        page.pack(fill="both", expand=True, padx=SPACE_2XL, pady=(SPACE_XL, SPACE_LG))
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        # ---- Hero ----
        hero = ctk.CTkFrame(page, fg_color="transparent")
        hero.grid(row=0, column=0, pady=(0, SPACE_LG))

        badge = ctk.CTkFrame(hero, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=PILL_RADIUS,
                             width=96, height=96)
        badge.pack(pady=(0, SPACE_SM))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="\U0001F5A8\uFE0F", font=(UI_FONT, 42),
                     text_color=COLOR_PRIMARY_BLUE).pack(expand=True)

        ctk.CTkLabel(hero, text="Print in Seconds", font=FONT_HERO,
                     text_color=COLOR_PRIMARY_TEXT).pack()
        ctk.CTkLabel(hero, text="Choose how to add your file, set your options, then pay at the kiosk",
                     font=(UI_FONT, 20), text_color=COLOR_SECONDARY_TEXT).pack(pady=(0, SPACE_MD))

        steps = ctk.CTkFrame(hero, fg_color="transparent")
        steps.pack()
        for i, label in enumerate(("Add file", "Choose settings", "Pay & print"), 1):
            if i > 1:
                ctk.CTkLabel(steps, text="\u2192", font=FONT_BODY,
                             text_color=COLOR_TERTIARY_TEXT).pack(side="left", padx=SPACE_XS)
            chip = ctk.CTkFrame(steps, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
            chip.pack(side="left")
            ctk.CTkLabel(chip, text=str(i), font=(UI_FONT, 15, "bold"),
                         text_color=COLOR_PRIMARY_BLUE).pack(side="left", padx=(14, 4), pady=6)
            ctk.CTkLabel(chip, text=label, font=FONT_BODY,
                         text_color=COLOR_SECONDARY_TEXT).pack(side="left", padx=(0, 14), pady=6)

        # ---- Action cards ----
        cards = ctk.CTkFrame(page, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=180)
        cards.grid_columnconfigure(0, weight=1, uniform="cards")
        cards.grid_columnconfigure(1, weight=1, uniform="cards")

        usb = self._action_card(
            cards,
            icon="\U0001F4BE",
            title="USB Drive",
            subtitle="Plug in your flash drive and pick a file",
            features=("PDF, DOCX, JPG and PNG files", "Page count and preview built in", "Works even without internet"),
            hint="Plug into the kiosk's USB port to get started",
            button_text="Choose USB  \u203A",
            command=self._on_usb,
        )
        usb.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_MD))

        phone = self._action_card(
            cards,
            icon="\U0001F4F1",
            title="Phone / QR",
            subtitle="Scan the code and upload from your phone",
            features=("No app to install", "Phone and kiosk on the same Wi-Fi", "Upload up to 50 MB"),
            hint="Open your camera, scan the next screen's code, and upload",
            button_text="Scan QR  \u203A",
            command=self._on_qr,
        )
        phone.grid(row=0, column=1, sticky="nsew", padx=(SPACE_MD, 0))

        # ---- Footer price bar ----
        footer = ctk.CTkFrame(page, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                              border_width=1, border_color=COLOR_BORDER_GRAY)
        footer.grid(row=2, column=0, sticky="ew", padx=180)
        items = (
            ("BLACK & WHITE", f"\u20B1{BW_PRICE_PER_PAGE} / page", COLOR_PRIMARY_BLUE),
            ("COLOR", f"\u20B1{COLOR_PRICE_PER_PAGE} / page", COLOR_PRIMARY_BLUE),
            ("PAPER SIZES", "A4 \u00B7 Long \u00B7 Short", COLOR_PRIMARY_TEXT),
            ("PAYMENT", "Coins", COLOR_PRIMARY_TEXT),
        )
        for i, (label, value, color) in enumerate(items):
            footer.grid_columnconfigure(i, weight=1, uniform="foot")
            cell = ctk.CTkFrame(footer, fg_color="transparent")
            cell.grid(row=0, column=i, pady=SPACE_MD)
            ctk.CTkLabel(cell, text=label, font=(UI_FONT, 15),
                         text_color=COLOR_TERTIARY_TEXT).pack()
            ctk.CTkLabel(cell, text=value, font=FONT_TITLE,
                         text_color=color).pack(pady=(2, 0))

    def _action_card(self, parent, icon, title, subtitle, features, hint, button_text, command):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                            border_width=1, border_color=COLOR_BORDER_GRAY)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_XL, pady=SPACE_XL)

        _icon_badge(inner, icon, size=88, glyph_size=42)
        ctk.CTkLabel(inner, text=title, font=FONT_H1,
                     text_color=COLOR_PRIMARY_TEXT).pack(pady=(SPACE_SM, 2))
        ctk.CTkLabel(inner, text=subtitle, font=FONT_BODY,
                     text_color=COLOR_SECONDARY_TEXT).pack()

        feats = ctk.CTkFrame(inner, fg_color="transparent")
        feats.pack(pady=(SPACE_MD, 0))
        for text in features:
            _check_row(feats, text)

        hint_box = ctk.CTkFrame(inner, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=BTN_RADIUS)
        hint_box.pack(pady=(SPACE_MD, 0))
        ctk.CTkLabel(hint_box, text=hint, font=(UI_FONT, 15), text_color=COLOR_PRIMARY_BLUE,
                     wraplength=480, justify="center").pack(padx=SPACE_MD, pady=SPACE_XS + 4)

        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)
        ctk.CTkButton(inner, text=button_text, font=FONT_BUTTON, width=340, height=64,
                      corner_radius=BTN_RADIUS,
                      fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER,
                      text_color="#FFFFFF", command=command).pack(pady=(SPACE_MD, 0))
        return card

    def _on_usb(self):
        self.switch_view("file_browser")

    def _on_qr(self):
        self.switch_view("qr")

    def update_credit_display(self):
        return
