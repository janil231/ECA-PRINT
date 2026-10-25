import customtkinter as ctk
import qrcode
from config import (
    COLOR_CARD_BG,
    COLOR_PRIMARY_TEXT,
    COLOR_SECONDARY_TEXT,
    COLOR_TERTIARY_TEXT,
    COLOR_PRIMARY_BLUE,
    COLOR_PRIMARY_BLUE_HOVER,
    COLOR_LIGHT_BLUE_BG,
    COLOR_BORDER_GRAY,
    COLOR_PILL_GRAY,
    COLOR_PILL_GRAY_HOVER,
    CARD_RADIUS,
    BTN_RADIUS,
    PILL_RADIUS,
    UI_FONT,
    FONT_H1,
    FONT_BODY,
    FONT_SMALL,
    FONT_TINY,
    FONT_BUTTON,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
    SPACE_LG,
    SPACE_XL,
    SPACE_2XL,
    HOTSPOT_SSID,
    HOTSPOT_PASSWORD,
)
from ui.base_view import BaseView
from wireless.server import get_local_ip

QR_URL_FMT = "http://{ip}:5000"
QR_SIZE = 320


def _step(parent, number, text):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=SPACE_XS)
    dot = ctk.CTkFrame(row, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=15,
                       width=30, height=30)
    dot.pack(side="left")
    dot.pack_propagate(False)
    ctk.CTkLabel(dot, text=str(number), font=(UI_FONT, 14, "bold"),
                 text_color=COLOR_PRIMARY_BLUE).pack(expand=True)
    ctk.CTkLabel(row, text=text, font=FONT_BODY, text_color=COLOR_SECONDARY_TEXT,
                 anchor="w").pack(side="left", padx=(SPACE_SM, 0))


class QRView(BaseView):
    def __init__(self, master, ip_address: str, back_callback):
        super().__init__(master)
        self.back_callback = back_callback

        local_ip = ip_address or ""
        if not local_ip or local_ip.startswith("127."):
            local_ip = get_local_ip()
        self.hotspot = local_ip.startswith("192.168.137.")
        self.url = QR_URL_FMT.format(ip=local_ip)

        page = ctk.CTkFrame(self, fg_color="transparent")
        page.pack(expand=True, fill="both", padx=SPACE_2XL, pady=SPACE_XL)

        holder = ctk.CTkFrame(page, fg_color="transparent")
        holder.place(relx=0.5, rely=0.5, anchor="center")
        content = ctk.CTkFrame(holder, fg_color="transparent")
        content.pack()

        # ---- Left: instructions + actions ----
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", anchor="n", padx=(0, SPACE_2XL))

        badge = ctk.CTkFrame(left, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=PILL_RADIUS,
                             width=76, height=76)
        badge.pack(anchor="w", pady=(0, SPACE_SM))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="\U0001F4F1", font=(UI_FONT, 36),
                     text_color=COLOR_PRIMARY_BLUE).pack(expand=True)

        ctk.CTkLabel(left, text="Upload from Your Phone", font=FONT_H1,
                     text_color=COLOR_PRIMARY_TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="No app needed \u2014 just scan and upload.",
                     font=FONT_BODY, text_color=COLOR_SECONDARY_TEXT).pack(
            anchor="w", pady=(2, SPACE_LG))

        steps = ctk.CTkFrame(left, fg_color="transparent")
        steps.pack(anchor="w")
        if self.hotspot:
            _step(steps, 1, f"Join Wi-Fi \u201C{HOTSPOT_SSID}\u201D on your phone")
        else:
            _step(steps, 1, "Open the Camera app on your phone")
        _step(steps, 2, "Scan the QR code on the right")
        _step(steps, 3, "Pick the file you want to print")
        _step(steps, 4, "Tap \u201CContinue to files\u201D below")

        if self.hotspot:
            hint = ctk.CTkFrame(left, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
            hint.pack(anchor="w", pady=(SPACE_MD, 0))
            ctk.CTkLabel(hint, text=f"Wi-Fi password: {HOTSPOT_PASSWORD}",
                         font=FONT_SMALL, text_color=COLOR_PRIMARY_TEXT).pack(
                padx=SPACE_MD, pady=SPACE_XS)

        ctk.CTkFrame(left, fg_color="transparent", height=SPACE_LG).pack()

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(anchor="w")
        ctk.CTkButton(
            actions, text="Continue to files  \u203A", width=300, height=60,
            font=FONT_BUTTON, corner_radius=BTN_RADIUS,
            fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER,
            text_color="#FFFFFF", command=self._on_continue,
        ).pack(side="left", padx=(0, SPACE_SM))
        ctk.CTkButton(
            actions, text="\u2039  Back", width=150, height=60,
            font=FONT_BUTTON, corner_radius=BTN_RADIUS,
            fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER,
            text_color=COLOR_PRIMARY_TEXT, command=self._on_back,
        ).pack(side="left")

        # ---- Right: address + QR card ----
        card = ctk.CTkFrame(content, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                            border_width=1, border_color=COLOR_BORDER_GRAY)
        card.pack(side="left", anchor="n")

        pill = ctk.CTkFrame(card, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        pill.pack(pady=(SPACE_XL, SPACE_SM), padx=SPACE_XL)
        ctk.CTkLabel(pill, text=f"\U0001F517  {self.url}", font=FONT_SMALL,
                     text_color=COLOR_PRIMARY_BLUE).pack(padx=SPACE_MD, pady=SPACE_XS)

        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(self.url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            qr_img = ctk.CTkImage(light_image=img, dark_image=img, size=(QR_SIZE, QR_SIZE))
            qr_label = ctk.CTkLabel(card, image=qr_img, text="")
            qr_label.image = qr_img
            qr_label.pack(pady=SPACE_SM)
        except Exception as e:
            print(f"[QRView] Could not render QR code: {e}")
            ctk.CTkLabel(card, text="QR code unavailable\nType the address above\nin your phone browser",
                         font=FONT_SMALL, text_color=COLOR_TERTIARY_TEXT,
                         justify="center").pack(pady=SPACE_XL, padx=SPACE_XL)

        ctk.CTkLabel(card, text="Scan to upload files to the kiosk", font=FONT_SMALL,
                     text_color=COLOR_SECONDARY_TEXT).pack(pady=(0, SPACE_XS))
        ctk.CTkLabel(card, text="PDF \u00B7 DOC \u00B7 DOCX \u00B7 JPG \u00B7 PNG  \u00B7  up to 50 MB",
                     font=FONT_TINY, text_color=COLOR_TERTIARY_TEXT).pack(pady=(0, SPACE_XL))

    def _on_continue(self):
        self.back_callback("file_browser")

    def _on_back(self):
        self.back_callback("welcome")
