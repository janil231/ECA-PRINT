import customtkinter as ctk
import os
import queue
import threading
from config import (
    BW_PRICE_PER_PAGE,
    COLOR_PRICE_PER_PAGE,
    PAPER_SIZES,
    PAPER_SIZE_DEFAULT,
    COLOR_APP_BG,
    COLOR_CARD_BG,
    COLOR_PRIMARY_TEXT,
    COLOR_SECONDARY_TEXT,
    COLOR_TERTIARY_TEXT,
    COLOR_PRIMARY_BLUE,
    COLOR_PRIMARY_BLUE_HOVER,
    COLOR_WARNING_RED,
    COLOR_BORDER_GRAY,
    COLOR_PILL_GRAY,
    COLOR_PILL_GRAY_HOVER,
    COLOR_LIGHT_BLUE_BG,
    COLOR_LIGHT_BLUE_HOVER,
    CARD_RADIUS,
    BTN_RADIUS,
    PILL_RADIUS,
    UI_FONT,
    FONT_HERO,
    FONT_H1,
    FONT_H2,
    FONT_TITLE,
    FONT_BODY,
    FONT_SMALL,
    FONT_TINY,
    FONT_LABEL,
    FONT_BUTTON,
    FONT_AMOUNT_SM,
    SPACE_XS,
    SPACE_SM,
    SPACE_MD,
    SPACE_LG,
)
from core.file_reader import FileReader
from ui.base_view import BaseView

ALERT_BG = "#FDE7E6"
PRINTER_RECHECK_MS = 5000
DOCX_PREPARE_TIMEOUT_MS = 60000


def _section(parent, title):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=(SPACE_MD, 0))
    ctk.CTkLabel(frame, text=title, font=FONT_LABEL, text_color=COLOR_TERTIARY_TEXT,
                 anchor="w").pack(fill="x", padx=(SPACE_XS, 0), pady=(0, SPACE_SM))
    return frame


class PricingView(BaseView):
    """Interactive Print Settings & Preview — iOS Pro, Full HD.

    LEFT ~400px: grouped settings (mode, copies, pages, total, actions).
    RIGHT: LARGE document preview, the dominant element.
    Forwards (filepath, start_page, end_page, copies, print_mode, total_due).
    """

    def __init__(self, master, filepath, back_callback, coin_reader):
        super().__init__(master)
        self.filepath = filepath
        self.back_callback = back_callback
        self.coin_reader = coin_reader

        ext = os.path.splitext(filepath)[1].lower()
        self._is_docx = ext in {".docx", ".doc"}
        self._docx_preparing = self._is_docx
        self._docx_failed = False
        self._docx_results = queue.Queue()
        self._docx_poll_after = None
        self._docx_timeout_after = None
        if self._is_docx:
            self.total_pages = max(1, FileReader.get_total_pages_fast(filepath))
        else:
            self.total_pages = max(1, FileReader.get_total_pages(filepath))
        self.preview_idx = 0
        self.print_mode = "bw"
        self.copies = 1
        self.paper_size = PAPER_SIZE_DEFAULT
        self._preview_img_ref = None
        self._preview_loading_active = False
        self._shown_started = False
        self._preview_after_id = None
        self._printer_problem = None
        self._printer_check_running = False
        self._printer_poll_after = None
        self._printer_results = queue.Queue()

        if ext in {".jpg", ".jpeg", ".png"}:
            self.total_pages = 1

        short = os.path.basename(filepath)
        if len(short) > 42:
            short = short[:40] + "\u2026"
        
        # Header with app branding
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=SPACE_LG, pady=(SPACE_LG, 4))
        ctk.CTkLabel(header, text="Print Settings", font=FONT_H1, text_color=COLOR_PRIMARY_TEXT).pack(side="left")
        # File name pill
        pill = ctk.CTkFrame(header, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        pill.pack(side="left", padx=(12, 0), pady=4)
        ctk.CTkLabel(pill, text=f"\U0001F4C4  {short}", font=FONT_BODY,
                     text_color=COLOR_SECONDARY_TEXT).pack(padx=12, pady=4)

        # Main content area
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=SPACE_LG, pady=4)

        # ---- LEFT: settings card ----
        left = ctk.CTkFrame(body, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                            border_width=1, border_color=COLOR_BORDER_GRAY, width=380)
        left.pack(side="left", padx=(0, 12), pady=4, fill="y")
        left.pack_propagate(False)
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_LG, pady=SPACE_LG)

        # Color section
        _section(inner, "COLOR")
        seg = ctk.CTkFrame(inner, fg_color=COLOR_PILL_GRAY, corner_radius=BTN_RADIUS)
        seg.pack(fill="x", pady=(0, SPACE_SM))
        self.bw_btn = ctk.CTkButton(seg, text=f"\u25CF  B&W  \u20B1{BW_PRICE_PER_PAGE}/pg",
                                    height=44, font=FONT_BUTTON,
                                    corner_radius=12, command=lambda: self._set_mode("bw"))
        self.bw_btn.pack(side="left", fill="x", expand=True, padx=4, pady=2)
        self.color_btn = ctk.CTkButton(seg, text=f"\u25CF  Color  \u20B1{COLOR_PRICE_PER_PAGE}/pg",
                                       height=44, font=FONT_BUTTON,
                                       corner_radius=12, command=lambda: self._set_mode("color"))
        self.color_btn.pack(side="left", fill="x", expand=True, padx=4, pady=2)

        # Copies section
        _section(inner, "COPIES")
        crow = ctk.CTkFrame(inner, fg_color="transparent")
        crow.pack(fill="x", pady=(0, SPACE_SM))
        ctk.CTkButton(crow, text="\u2212", width=44, height=44, font=FONT_SMALL,
                      fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT,
                      corner_radius=BTN_RADIUS,
                      command=lambda: self._change_copies(-1)).pack(side="left")
        self.copies_lbl = ctk.CTkLabel(crow, text="1", font=FONT_H2, text_color=COLOR_PRIMARY_TEXT, width=36)
        self.copies_lbl.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(crow, text="copies", font=FONT_TINY, text_color=COLOR_SECONDARY_TEXT).pack(side="left", padx=(4, 8))
        ctk.CTkButton(crow, text="+", width=44, height=44, font=FONT_SMALL,
                      fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER, text_color="#FFFFFF",
                      corner_radius=BTN_RADIUS,
                      command=lambda: self._change_copies(1)).pack(side="left")
        ctk.CTkLabel(crow, text="max 10", font=FONT_TINY, text_color=COLOR_TERTIARY_TEXT).pack(side="left", padx=(4, 0))

        # Paper size section
        _section(inner, "PAPER SIZE")
        prow = ctk.CTkFrame(inner, fg_color=COLOR_PILL_GRAY, corner_radius=BTN_RADIUS)
        prow.pack(fill="x", pady=(0, SPACE_SM))
        for _c in range(3):
            prow.grid_columnconfigure(_c, weight=1, uniform="paper")
        self.paper_btns = {}
        for _i, (_key, _label) in enumerate((("a4", "A4"), ("long", "Long"), ("short", "Short"))):
            _btn = ctk.CTkButton(prow, text=_label, height=40, width=1,
                                 font=(UI_FONT, 14, "bold"), corner_radius=10,
                                 command=lambda k=_key: self._set_paper(k))
            _btn.grid(row=0, column=_i, sticky="ew", padx=3, pady=3)
            self.paper_btns[_key] = _btn

        # Total breakdown
        _section(inner, "TOTAL")
        tcard = ctk.CTkFrame(inner, fg_color=COLOR_LIGHT_BLUE_BG, corner_radius=BTN_RADIUS)
        tcard.pack(fill="x", pady=(0, SPACE_SM))
        self.breakdown_lbl = ctk.CTkLabel(tcard, text="", font=FONT_SMALL, text_color=COLOR_SECONDARY_TEXT)
        self.breakdown_lbl.pack(pady=(SPACE_SM, 0))
        self.total_lbl = ctk.CTkLabel(tcard, text="Total  \u20B10", font=FONT_AMOUNT_SM,
                                      text_color=COLOR_PRIMARY_BLUE)
        self.total_lbl.pack(pady=(0, 0))

        # Spacer to push actions to bottom
        flex = ctk.CTkFrame(inner, fg_color="transparent")
        flex.pack(fill="both", expand=True)

        self.printer_alert = ctk.CTkFrame(inner, fg_color=ALERT_BG, corner_radius=BTN_RADIUS)
        self.printer_alert_lbl = ctk.CTkLabel(
            self.printer_alert, text="", font=(UI_FONT, 15, "bold"),
            text_color=COLOR_WARNING_RED, anchor="w", justify="left",
            wraplength=300)
        self.printer_alert_lbl.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

        # Actions row at the bottom
        act = ctk.CTkFrame(inner, fg_color="transparent")
        act.pack(fill="x", pady=(0, SPACE_LG))
        self.actions_row = act
        ctk.CTkButton(act, text="\u2039  Back", width=96, height=48, font=FONT_BUTTON,
                      fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT,
                      corner_radius=BTN_RADIUS, command=self._on_back).pack(side="left")
        self.proceed_btn = ctk.CTkButton(act, text="Continue  \u203A", height=48,
                                         font=FONT_BUTTON,
                                         fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER,
                                         text_color="#FFFFFF", corner_radius=BTN_RADIUS,
                                         command=self._on_proceed)
        self.proceed_btn.pack(side="left", padx=(SPACE_MD, 0), fill="x", expand=True)

        # ---- RIGHT: large document preview ----
        right = ctk.CTkFrame(body, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
                             border_width=1, border_color=COLOR_BORDER_GRAY)
        right.pack(side="left", pady=4, fill="both", expand=True)

        # Preview header
        rhead = ctk.CTkFrame(right, fg_color="transparent")
        rhead.pack(fill="x", padx=SPACE_LG, pady=(SPACE_LG, 6))
        ctk.CTkLabel(rhead, text="\U0001F441  Document Preview", font=FONT_TITLE,
                     text_color=COLOR_PRIMARY_TEXT).pack(side="left")
        self.page_pill = ctk.CTkFrame(rhead, fg_color=COLOR_PILL_GRAY, corner_radius=PILL_RADIUS)
        self.page_pill.pack(side="right")
        pages_text = "\u2026" if self._docx_preparing else str(self.total_pages)
        self.page_lbl = ctk.CTkLabel(self.page_pill, text="Page 1 of {}".format(pages_text),
                                     font=FONT_SMALL, text_color=COLOR_SECONDARY_TEXT)
        self.page_lbl.pack(padx=12, pady=6)

        # Preview sheet area
        self.sheet = ctk.CTkFrame(right, fg_color="#F2F2F7", corner_radius=PILL_RADIUS,
                                  border_width=1, border_color=COLOR_BORDER_GRAY)
        self.sheet.pack(padx=SPACE_LG, pady=4, fill="both", expand=True)
        preview_text = ("Preparing preview\u2026" if self._docx_preparing
                        else "Loading preview\u2026")
        self.preview_lbl = ctk.CTkLabel(self.sheet, text=preview_text,
                                        font=FONT_SMALL, text_color=COLOR_SECONDARY_TEXT,
                                        fg_color="#F2F2F7")
        self.preview_lbl.pack(fill="both", expand=True, padx=0, pady=0)

        self.preview_loading = ctk.CTkFrame(
            self.sheet, fg_color=COLOR_CARD_BG, corner_radius=CARD_RADIUS,
            border_width=1, border_color=COLOR_BORDER_GRAY)
        ctk.CTkLabel(
            self.preview_loading, text="Preparing preview\u2026",
            font=FONT_TITLE, text_color=COLOR_PRIMARY_TEXT
        ).pack(padx=48, pady=(28, 4))
        ctk.CTkLabel(
            self.preview_loading,
            text="Converting the Word document. This may take a few seconds.",
            font=FONT_SMALL, text_color=COLOR_SECONDARY_TEXT
        ).pack(padx=48, pady=(0, 18))
        self.preview_progress = ctk.CTkProgressBar(
            self.preview_loading, width=360, height=10, corner_radius=5,
            mode="indeterminate", indeterminate_speed=1.2,
            fg_color=COLOR_PILL_GRAY, progress_color=COLOR_PRIMARY_BLUE)
        self.preview_progress.set(0)
        self.preview_progress.pack(padx=48, pady=(0, 28))

        try:
            self.sheet.bind("<Configure>", lambda _e: self._schedule_preview())
        except Exception:
            pass

        # Navigation bar below preview
        nav = ctk.CTkFrame(right, fg_color="transparent")
        nav.pack(pady=(0, SPACE_LG))
        ctk.CTkButton(nav, text="\u25C0  Prev", width=110, height=44, font=FONT_SMALL,
                      fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT,
                      corner_radius=BTN_RADIUS, command=self._on_prev).pack(side="left", padx=6)
        ctk.CTkButton(nav, text="Next  \u25B6", width=110, height=44, font=FONT_SMALL,
                      fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT,
                      corner_radius=BTN_RADIUS, command=self._on_next).pack(side="left", padx=6)

        self._refresh_all()

    def on_view_shown(self):
        if self._shown_started:
            return
        self._shown_started = True
        try:
            if self._is_docx:
                self._show_preview_loading()
                self._start_docx_prepare()
            else:
                self.after(20, self._refresh_preview)
            self.after(150, self._check_printer)
        except Exception:
            pass

    # ---- pricing math ----
    def _rate(self):
        return BW_PRICE_PER_PAGE if self.print_mode == "bw" else COLOR_PRICE_PER_PAGE

    def _pages_to_print(self):
        return self.total_pages

    def _total_due(self):
        return self._pages_to_print() * self.copies * self._rate()

    def _job_pages(self):
        return (1, self.total_pages)

    # ---- UI refresh ----
    def _refresh_all(self):
        self._paint_mode_buttons()
        self._paint_paper_buttons()
        self.copies_lbl.configure(text=str(self.copies))
        if self._docx_preparing:
            self.breakdown_lbl.configure(text="Preparing document\u2026")
            self.total_lbl.configure(text="Total  \u20B1\u2014")
        elif self._docx_failed:
            self.breakdown_lbl.configure(text="Word document could not be prepared")
            self.total_lbl.configure(text="Total  \u20B1\u2014")
        else:
            pages = self._pages_to_print()
            rate_str = f"\u20B1{self._rate()}/pg"
            paper_name = self._paper_label()
            self.breakdown_lbl.configure(
                text=f"{pages} page{'s' if pages != 1 else ''}  \u2022  {self.copies} cop{'y' if self.copies == 1 else 'ies'}  \u2022  {rate_str}  \u2022  {paper_name}"
            )
            total = self._total_due()
            self.total_lbl.configure(text=f"Total  \u20B1{total}")
        self._paint_proceed()
        if self._shown_started:
            self._refresh_preview()

    def _paint_proceed(self):
        total = self._total_due()
        try:
            if self._docx_preparing:
                self.proceed_btn.configure(
                    state="disabled", text="Preparing document\u2026",
                    fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY,
                    text_color=COLOR_TERTIARY_TEXT)
            elif self._docx_failed:
                self.proceed_btn.configure(
                    state="disabled", text="Document unavailable",
                    fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY,
                    text_color=COLOR_TERTIARY_TEXT)
            elif self._printer_problem:
                self.proceed_btn.configure(
                    state="disabled", text="Printer offline",
                    fg_color=COLOR_PILL_GRAY, hover_color=COLOR_PILL_GRAY,
                    text_color=COLOR_TERTIARY_TEXT)
            else:
                self.proceed_btn.configure(
                    state="normal", text=f"Continue  \u203A  \u20B1{total}",
                    fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER,
                    text_color="#FFFFFF")
        except Exception:
            pass

    def _apply_printer_problem(self, problem):
        problem = problem or None
        if problem == self._printer_problem:
            return
        self._printer_problem = problem
        try:
            if problem:
                self.printer_alert_lbl.configure(
                    text=f"\u26A0\uFE0F  {problem} \u2014 printing is unavailable. Please ask staff.")
                if not self.printer_alert.winfo_ismapped():
                    self.printer_alert.pack(fill="x", pady=(0, SPACE_SM),
                                            before=self.actions_row)
            else:
                self.printer_alert.pack_forget()
        except Exception:
            pass
        self._paint_proceed()

    def _schedule_printer_check(self):
        try:
            if self._printer_poll_after:
                self.after_cancel(self._printer_poll_after)
        except Exception:
            pass
        try:
            self._printer_poll_after = self.after(
                PRINTER_RECHECK_MS, self._check_printer)
        except Exception:
            self._printer_poll_after = None

    def _check_printer(self):
        self._printer_poll_after = None
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self._printer_check_running:
            self._schedule_printer_check()
            return
        self._printer_check_running = True

        def work():
            try:
                from core.printer import printer_block_reason
                problem = printer_block_reason()
            except Exception:
                problem = None
            try:
                self._printer_results.put(problem)
            except Exception:
                pass

        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            self._printer_check_running = False
            self._schedule_printer_check()
            return
        self._poll_printer_result()

    def _poll_printer_result(self):
        try:
            problem = self._printer_results.get_nowait()
        except queue.Empty:
            try:
                self.after(100, self._poll_printer_result)
            except Exception:
                pass
            return
        self._printer_checked(problem)

    def _printer_checked(self, problem):
        self._printer_check_running = False
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._apply_printer_problem(problem)
        self._schedule_printer_check()

    def _start_docx_prepare(self):
        def work():
            pdf_path = None
            pages = None
            try:
                from core.docx_converter import convert_docx_to_pdf
                pdf_path = convert_docx_to_pdf(self.filepath)
                if pdf_path:
                    try:
                        pages = FileReader.get_total_pages(self.filepath)
                    except Exception:
                        pages = None
                    if not pages:
                        import fitz
                        pdf = fitz.open(pdf_path)
                        try:
                            pages = len(pdf)
                        finally:
                            pdf.close()
            except Exception as exc:
                print(f"[Pricing] DOCX preparation failed: {exc}")
            try:
                self._docx_results.put((pdf_path, pages))
            except Exception:
                pass

        try:
            self._docx_timeout_after = self.after(
                DOCX_PREPARE_TIMEOUT_MS, self._docx_prepare_timeout)
        except Exception:
            self._docx_timeout_after = None
        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            self._finish_docx_prepare(None, None)
            return
        self._poll_docx_prepare()

    def _poll_docx_prepare(self):
        self._docx_poll_after = None
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            pdf_path, pages = self._docx_results.get_nowait()
        except queue.Empty:
            try:
                self._docx_poll_after = self.after(100, self._poll_docx_prepare)
            except Exception:
                pass
            return
        self._finish_docx_prepare(pdf_path, pages)

    def _docx_prepare_timeout(self):
        self._docx_timeout_after = None
        if self._docx_preparing:
            print("[Pricing] DOCX preparation timed out")
            self._finish_docx_prepare(None, None)

    def _finish_docx_prepare(self, pdf_path, pages):
        if not self._docx_preparing:
            return
        self._docx_preparing = False
        self._docx_failed = not bool(pdf_path) or not bool(pages)
        if pages:
            try:
                self.total_pages = max(1, int(pages))
                self.preview_idx = min(self.preview_idx, self.total_pages - 1)
            except Exception:
                pass
        for attr in ("_docx_poll_after", "_docx_timeout_after"):
            handle = getattr(self, attr, None)
            if handle:
                try:
                    self.after_cancel(handle)
                except Exception:
                    pass
                setattr(self, attr, None)
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._refresh_all()

    def _paint_mode_buttons(self):
        if self.print_mode == "bw":
            self.bw_btn.configure(fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER, text_color="#FFFFFF")
            self.color_btn.configure(fg_color="transparent", hover_color=COLOR_LIGHT_BLUE_BG, text_color=COLOR_PRIMARY_TEXT)
        else:
            self.color_btn.configure(fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER, text_color="#FFFFFF")
            self.bw_btn.configure(fg_color="transparent", hover_color=COLOR_LIGHT_BLUE_BG, text_color=COLOR_PRIMARY_TEXT)

    def _paper_label(self):
        return PAPER_SIZES.get(self.paper_size, PAPER_SIZES.get(PAPER_SIZE_DEFAULT, {})).get("label", "A4")

    def _paint_paper_buttons(self):
        for key, btn in getattr(self, "paper_btns", {}).items():
            if key == self.paper_size:
                btn.configure(fg_color=COLOR_PRIMARY_BLUE, hover_color=COLOR_PRIMARY_BLUE_HOVER, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", hover_color=COLOR_PILL_GRAY_HOVER, text_color=COLOR_PRIMARY_TEXT)

    def _set_paper(self, key):
        self.paper_size = key
        self._refresh_all()

    def _get_preview_box(self):
        try:
            w = self.sheet.winfo_width()
            h = self.sheet.winfo_height()
            if w < 100 or h < 100:
                return (1100, 760)
            return (max(200, w - 4), max(200, h - 4))
        except Exception:
            return (1100, 760)

    def _schedule_preview(self):
        if not self._shown_started:
            return
        try:
            if self._preview_after_id:
                self.after_cancel(self._preview_after_id)
        except Exception:
            pass
        try:
            self._preview_after_id = self.after(150, self._refresh_preview)
        except Exception:
            pass

    def _show_preview_loading(self):
        if self._preview_loading_active or not self._docx_preparing:
            return
        self._preview_loading_active = True
        try:
            self.preview_lbl.configure(image=None, text="")
            self.preview_loading.place(relx=0.5, rely=0.5, anchor="center")
            self.preview_loading.lift()
            self.preview_progress.start()
        except Exception:
            pass

    def _hide_preview_loading(self):
        self._preview_loading_active = False
        try:
            self.preview_progress.stop()
        except Exception:
            pass
        try:
            self.preview_loading.place_forget()
        except Exception:
            pass

    def _refresh_preview(self):
        try:
            self._preview_after_id = None
            if not self.winfo_exists():
                return
            if self._docx_preparing:
                self._show_preview_loading()
                self.page_lbl.configure(text="Page 1 of \u2026")
                return
            self._hide_preview_loading()
            if self._docx_failed:
                self._preview_img_ref = None
                self.preview_lbl.configure(
                    image=None,
                    text="Preview unavailable.\nThis Word file could not be prepared.")
                self.page_lbl.configure(text="Page \u2014 of \u2014")
                return
            is_bw = (self.print_mode == "bw")
            box = self._get_preview_box()
            _paper = PAPER_SIZES.get(self.paper_size, {})
            img = FileReader.render_page_preview(
                self.filepath, self.preview_idx, is_bw, box=box,
                paper=(_paper.get("width_mm"), _paper.get("height_mm")),
                allow_docx_conversion=True)
            self._preview_img_ref = img
            self.preview_lbl.configure(image=img, text="")
            self.page_lbl.configure(text=f"Page {self.preview_idx + 1} of {self.total_pages}")
        except Exception:
            self._hide_preview_loading()
            try:
                self.preview_lbl.configure(text="Preview unavailable")
            except Exception:
                pass

    # ---- handlers ----
    def _on_prev(self):
        if self._docx_preparing or self._docx_failed or self.total_pages < 1:
            return
        self.preview_idx = (self.preview_idx - 1) % self.total_pages
        self._refresh_preview()

    def _on_next(self):
        if self._docx_preparing or self._docx_failed or self.total_pages < 1:
            return
        self.preview_idx = (self.preview_idx + 1) % self.total_pages
        self._refresh_preview()

    def _set_mode(self, mode):
        self.print_mode = mode
        self._refresh_all()

    def _change_copies(self, delta):
        self.copies = max(1, min(10, self.copies + delta))
        self._refresh_all()

    def _on_proceed(self):
        if self._docx_preparing or self._docx_failed:
            return
        try:
            from core.printer import printer_block_reason
            problem = printer_block_reason()
        except Exception:
            problem = None
        self._apply_printer_problem(problem)
        if problem:
            return
        start_page, end_page = self._job_pages()
        total = self._total_due()
        self.back_callback("payment", self.filepath, total, self.print_mode,
                           start_page, end_page, self.copies, self.paper_size)

    def _on_back(self):
        self.back_callback("file_browser")

    def destroy(self):
        self._hide_preview_loading()
        super().destroy()
