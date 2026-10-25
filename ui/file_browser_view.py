import customtkinter as ctk
import os
import threading
from config import (
    COLOR_APP_BG,
    COLOR_CARD_BG,
    COLOR_PRIMARY_TEXT,
    COLOR_SECONDARY_TEXT,
    COLOR_TERTIARY_TEXT,
    COLOR_PRIMARY_BLUE,
    COLOR_LIGHT_BLUE_HOVER,
    COLOR_BORDER_GRAY,
    COLOR_PILL_GRAY,
    COLOR_PILL_GRAY_HOVER,
    COLOR_WHITE,
    CARD_RADIUS,
    BTN_RADIUS,
    PILL_RADIUS,
    UI_FONT,
    FONT_H1,
    FONT_H2,
    FONT_TITLE,
    FONT_BODY,
    FONT_SMALL,
    FONT_TINY,
    FONT_BUTTON,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
    SPACE_LG,
)
from core.usb_detect import USBDetector
from ui.base_view import BaseView

FILE_ICONS = {".pdf": "\U0001F4D5", ".docx": "\U0001F4DD", ".doc": "\U0001F4DD",
              ".jpg": "\U0001F5BC\uFE0F", ".jpeg": "\U0001F5BC\uFE0F", ".png": "\U0001F5BC\uFE0F"}


class FileBrowserView(BaseView):
    def __init__(self, master, back_callback, coin_reader):
        super().__init__(master)
        self.back_callback = back_callback
        self.coin_reader = coin_reader
        self.detector = USBDetector()
        self._page_token = 0
        self._meta_labels = {}
        self._files = []
        self._counts_started = False

        # Header with consistent spacing
        ctk.CTkLabel(self, text="Your Files", font=FONT_H1, text_color=COLOR_PRIMARY_TEXT).pack(pady=(SPACE_LG, 0))
        ctk.CTkLabel(self, text="Select a file to print", font=FONT_BODY, text_color=COLOR_SECONDARY_TEXT).pack(pady=(0, SPACE_SM))

        # List card with consistent padding
        self.list_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                                      border_width=1, border_color=COLOR_BORDER_GRAY)
        self.list_card.pack(pady=SPACE_SM, padx=SPACE_LG, fill="both", expand=True)

        self.list_frame = ctk.CTkScrollableFrame(
            self.list_card, fg_color="transparent", corner_radius=PILL_RADIUS,
            scrollbar_button_color=COLOR_BORDER_GRAY,
            scrollbar_button_hover_color=COLOR_PRIMARY_BLUE,
        )
        self.list_frame.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_MD)

        # Bottom navigation is built BEFORE the file scan, so Back is always
        # on screen even if scanning or page counting is slow.
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(pady=SPACE_LG, side="bottom")
        ctk.CTkButton(
            bottom, text="\u2039  Back", command=self._on_back,
            width=220, height=64, font=FONT_BUTTON,
            fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER,
            text_color=COLOR_PRIMARY_TEXT, corner_radius=BTN_RADIUS,
        ).pack()

        self._load_files()

    def _load_files(self):
        self._page_token += 1
        self._meta_labels = {}
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        files = sorted(self.detector.scan_supported_files())
        self._files = files
        self._counts_started = False
        if not files:
            empty = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty.pack(pady=SPACE_LG)
            ctk.CTkLabel(empty, text="\U0001F4C2", font=(UI_FONT, 48)).pack()
            ctk.CTkLabel(empty, text="No files found", font=FONT_H2, text_color=COLOR_PRIMARY_TEXT).pack(pady=(SPACE_SM, 2))
            ctk.CTkLabel(empty, text="Plug in a USB drive or upload from your phone", font=FONT_TINY, text_color=COLOR_TERTIARY_TEXT).pack()
            return

        for fpath in files:
            fname = os.path.basename(fpath)
            ext = os.path.splitext(fname)[1].lower()
            icon = FILE_ICONS.get(ext, "\U0001F4C4")
            meta = ext.replace(".", "").upper()

            row = ctk.CTkButton(
                self.list_frame, corner_radius=BTN_RADIUS,
                text="",  # no default label: children carry the content
                fg_color=COLOR_WHITE, hover_color=COLOR_LIGHT_BLUE_HOVER,
                border_width=1, border_color=COLOR_BORDER_GRAY,
                height=76, anchor="w",
                command=lambda fp=fpath: self._on_select(fp),
            )
            row.pack(pady=SPACE_SM, padx=SPACE_SM, fill="x")

            # Build cell content inside the button frame
            try:
                row.grid_columnconfigure(2, weight=1)
                ctk.CTkLabel(row, text=icon, font=(UI_FONT, 24),
                             text_color=COLOR_PRIMARY_BLUE).grid(row=0, column=0, rowspan=2, padx=(SPACE_MD, 0), pady=SPACE_SM)
                ctk.CTkLabel(row, text=fname[:52], font=(UI_FONT, 17, "bold"),
                             text_color=COLOR_PRIMARY_TEXT, anchor="w").grid(
                    row=0, column=1, sticky="w", padx=(0, 6), pady=(SPACE_SM, 0))
                meta_label = ctk.CTkLabel(row, text=meta, font=(UI_FONT, 13),
                                          text_color=COLOR_TERTIARY_TEXT, anchor="w")
                meta_label.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(0, 0))
                self._meta_labels[fpath] = meta_label
                ctk.CTkLabel(row, text="\u203A", font=(UI_FONT, 24, "bold"),
                             text_color=COLOR_PRIMARY_BLUE).grid(row=0, column=3, rowspan=2, padx=(0, SPACE_LG))
            except Exception:
                row.configure(text=f"{icon}   {fname}")

    def on_view_shown(self):
        if self._counts_started or not self._files:
            return
        self._counts_started = True
        threading.Thread(
            target=self._load_page_counts,
            args=(self._page_token, list(self._files)),
            daemon=True,
        ).start()

    def _load_page_counts(self, token, files):
        from core.file_reader import FileReader
        counts = {}
        for fpath in files:
            try:
                counts[fpath] = FileReader.get_total_pages_fast(fpath)
            except Exception:
                pass
        try:
            self.after(0, lambda: self._apply_page_counts(token, counts))
        except Exception:
            pass

    def _apply_page_counts(self, token, counts):
        if token != self._page_token:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        for fpath, pages in counts.items():
            label = self._meta_labels.get(fpath)
            if label is None:
                continue
            try:
                if not label.winfo_exists():
                    continue
                ext = os.path.splitext(fpath)[1].replace(".", "").upper()
                suffix = "page" if pages == 1 else "pages"
                prefix = "~" if ext in {"DOCX", "DOC"} else ""
                label.configure(text=f"{ext}  \u2022  {prefix}{pages} {suffix}")
            except Exception:
                pass

    def _on_select(self, filepath):
        self.back_callback("pricing", filepath)

    def _on_back(self):
        self.back_callback("welcome")

    def update_credit_display(self):
        return
