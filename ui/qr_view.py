import threading
import time
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
    COLOR_AMBER_TEXT,
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
    label = ctk.CTkLabel(row, text=text, font=FONT_BODY, text_color=COLOR_SECONDARY_TEXT,
                         anchor="w", justify="left", wraplength=560)
    label.pack(side="left", padx=(SPACE_SM, 0))
    return label


class QRView(BaseView):
    def __init__(self, master, ip_address: str, back_callback):
        super().__init__(master)
        self.back_callback = back_callback
        self._poll_after = None
        self._poll_count = 0
        self._hotspot_attempt_inflight = False
        self._last_hotspot_attempt = 0.0

        local_ip = ip_address or ""
        if not local_ip or local_ip.startswith("127."):
            local_ip = get_local_ip()
        self.local_ip = local_ip
        self.hotspot = local_ip.startswith("192.168.137.")
        self.url = QR_URL_FMT.format(ip=local_ip)

        page = ctk.CTkFrame(self, fg_color="transparent")
        page.pack(expand=True, fill="both", padx=SPACE_2XL, pady=SPACE_XL)

        holder = ctk.CTkFrame(page, fg_color="transparent")
        holder.place(relx=0.5, rely=0.5, anchor="center")
        content = ctk.CTkFrame(holder, fg_color="transparent")
        content.pack()

        # ---- Left: connection directions + actions ----
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
        ctk.CTkLabel(left, text="No app needed \u2014 connect to Wi-Fi, then scan and upload.",
                     font=FONT_BODY, text_color=COLOR_SECONDARY_TEXT).pack(
            anchor="w", pady=(2, SPACE_LG))

        steps = ctk.CTkFrame(left, fg_color="transparent")
        steps.pack(anchor="w")
        _step(steps, 1, "Open Wi-Fi settings on your phone")
        self.join_label = _step(steps, 2, self._join_text())
        _step(steps, 3, "Scan the QR code on the right")
        _step(steps, 4, "Pick the file you want to print")
        _step(steps, 5, "Tap \u201CContinue to files\u201D below")

        hint = ctk.CTkFrame(left, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        hint.pack(anchor="w", pady=(SPACE_MD, 0))
        ctk.CTkLabel(
            hint,
            text=f"Wi-Fi: {HOTSPOT_SSID}  \u00B7  Password: {HOTSPOT_PASSWORD}",
            font=FONT_SMALL,
            text_color=COLOR_PRIMARY_TEXT,
        ).pack(anchor="w", padx=SPACE_MD, pady=(SPACE_XS, 0))
        self.status_label = ctk.CTkLabel(
            hint,
            text=self._status_text(),
            font=FONT_TINY,
            text_color=self._status_color(),
            justify="left",
            wraplength=520,
        )
        self.status_label.pack(anchor="w", padx=SPACE_MD, pady=(0, SPACE_XS))

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
        self.url_label = ctk.CTkLabel(pill, text=f"\U0001F517  {self.url}", font=FONT_SMALL,
                                      text_color=COLOR_PRIMARY_BLUE)
        self.url_label.pack(padx=SPACE_MD, pady=SPACE_XS)

        self.qr_label = ctk.CTkLabel(card, text="")
        self.qr_label.pack(pady=SPACE_SM)
        self._render_qr()

        ctk.CTkLabel(card, text="Scan to upload files to the kiosk", font=FONT_SMALL,
                     text_color=COLOR_SECONDARY_TEXT).pack(pady=(0, SPACE_XS))
        ctk.CTkLabel(card, text="PDF \u00B7 DOC \u00B7 DOCX \u00B7 JPG \u00B7 PNG  \u00B7  up to 50 MB",
                     font=FONT_TINY, text_color=COLOR_TERTIARY_TEXT).pack(pady=(0, SPACE_XL))

        # The hotspot can take a few seconds to appear after launch. Retry it
        # here and refresh the QR/instructions if the address changes.
        if not self.hotspot:
            self._start_hotspot_attempt()
        self._poll_after = self.after(1000, self._poll_network)

    def _join_text(self):
        if self.hotspot:
            return f"Join Wi-Fi \u201C{HOTSPOT_SSID}\u201D (password: {HOTSPOT_PASSWORD})"
        return f"Join Wi-Fi \u201C{HOTSPOT_SSID}\u201D if it appears, or the kiosk\u2019s Wi-Fi"

    def _status_text(self):
        if self.hotspot:
            return "Hotspot is on. Connect your phone to this Wi-Fi, then scan the QR."
        if self._poll_count >= 15:
            return "Hotspot not detected. Connect your phone to the same Wi-Fi as the kiosk, or ask staff."
        return "Starting the ECA Print hotspot... You can also connect to the kiosk's current Wi-Fi."

    def _status_color(self):
        return COLOR_PRIMARY_BLUE if self.hotspot else COLOR_AMBER_TEXT

    def _render_qr(self):
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(self.url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            qr_img = ctk.CTkImage(light_image=img, dark_image=img, size=(QR_SIZE, QR_SIZE))
            self.qr_label.configure(image=qr_img, text="")
            self.qr_label.image = qr_img
        except Exception as e:
            print(f"[QRView] Could not render QR code: {e}")
            self.qr_label.configure(
                image=None,
                text="QR code unavailable\nType the address above\nin your phone browser",
                font=FONT_SMALL,
                text_color=COLOR_TERTIARY_TEXT,
                justify="center",
            )

    def _start_hotspot_attempt(self):
        if self._hotspot_attempt_inflight:
            return
        now = time.time()
        if now - self._last_hotspot_attempt < 10:
            return
        self._last_hotspot_attempt = now
        self._hotspot_attempt_inflight = True
        try:
            threading.Thread(target=self._try_start_hotspot, daemon=True).start()
        except Exception:
            self._hotspot_attempt_inflight = False

    def _try_start_hotspot(self):
        try:
            from core.hotspot import ensure_hotspot
            ensure_hotspot()
        except Exception as exc:
            print(f"[QRView] Hotspot start failed: {exc}")
        finally:
            self._hotspot_attempt_inflight = False

    def _poll_network(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._poll_count += 1
        current_ip = get_local_ip()
        if current_ip != self.local_ip:
            self._apply_network(current_ip)
        if not self.hotspot:
            self._start_hotspot_attempt()
            try:
                self.status_label.configure(text=self._status_text(),
                                            text_color=self._status_color())
            except Exception:
                pass
        try:
            self._poll_after = self.after(2000, self._poll_network)
        except Exception:
            self._poll_after = None

    def _apply_network(self, ip):
        was_hotspot = self.hotspot
        self.local_ip = ip
        self.hotspot = ip.startswith("192.168.137.")
        if was_hotspot and not self.hotspot:
            self._poll_count = 0
        self.url = QR_URL_FMT.format(ip=ip)
        try:
            self.url_label.configure(text=f"\U0001F517  {self.url}")
            self.join_label.configure(text=self._join_text())
            self.status_label.configure(text=self._status_text(),
                                        text_color=self._status_color())
            self._render_qr()
        except Exception as exc:
            print(f"[QRView] Could not refresh network details: {exc}")

    def _on_continue(self):
        self.back_callback("file_browser")

    def _on_back(self):
        self.back_callback("welcome")

    def destroy(self):
        try:
            if self._poll_after is not None:
                self.after_cancel(self._poll_after)
        except Exception:
            pass
        super().destroy()
