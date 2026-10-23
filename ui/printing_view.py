import customtkinter as ctk
import winsound
import threading
import time
import os
from config import (
    CARD_BG,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    PRIMARY_BLUE,
    SUCCESS_GREEN,
    WARNING_RED,
    BORDER_GRAY,
    PILL_GRAY,
    CARD_RADIUS,
    UI_FONT,
)
from ui.base_view import BaseView
from ui.animations import PrinterPaperAnimation
from core.file_reader import FileReader


class PrintingView(BaseView):
    def __init__(self, master, filepath, due, print_mode, coin_reader, back_callback,
                 start_page=1, end_page=None, copies=1, paper_size=None):
        super().__init__(master)
        self.filepath = filepath
        self.due = due
        self.print_mode = print_mode or "bw"
        self.paper_size = paper_size
        self.coin_reader = coin_reader
        self.back_callback = back_callback
        self.start_page = start_page or 1
        self.end_page = end_page
        try:
            self.copies = max(1, int(copies or 1))
        except Exception:
            self.copies = 1

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(expand=True, fill="both", padx=40, pady=16)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        center = ctk.CTkFrame(wrap, fg_color="transparent")
        center.grid(row=0, column=0)

        self.icon = ctk.CTkLabel(center, text="\U0001F5A8\uFE0F", font=(UI_FONT, 72),
                                 text_color=PRIMARY_TEXT)
        self.icon.pack(pady=(6, 2))
        ctk.CTkLabel(center, text="Printing", font=(UI_FONT, 38, "bold"),
                     text_color=PRIMARY_TEXT).pack()

        try:
            end_txt = self.end_page if self.end_page else "?"
            job_txt = f"Pages {self.start_page}\u2013{end_txt}  \u2022  {self.copies} cop{'y' if self.copies == 1 else 'ies'}"
        except Exception:
            job_txt = ""
        if job_txt:
            pill = ctk.CTkFrame(center, fg_color=PILL_GRAY, corner_radius=14)
            pill.pack(pady=8)
            ctk.CTkLabel(pill, text=job_txt, font=(UI_FONT, 16),
                         text_color=SECONDARY_TEXT).pack(padx=18, pady=6)

        # Auto-sized card: content defines its height, so there is never
        # dead space below the progress bar.
        card = ctk.CTkFrame(center, fg_color=CARD_BG, corner_radius=CARD_RADIUS,
                            border_width=1, border_color=BORDER_GRAY)
        card.pack(pady=10)
        self.card = card

        # Live printer animation: paper slides out as pages render/print.
        try:
            self.paper_anim = PrinterPaperAnimation(card, width=560, height=300)
            self.paper_anim.pack(pady=(12, 2))
        except Exception as e:
            print(f"Printer animation could not start: {e}")
            self.paper_anim = None

        self.spinner = ctk.CTkLabel(card, text="Preparing your document\u2026",
                                    font=(UI_FONT, 21), text_color=SECONDARY_TEXT,
                                    justify="center")
        self.spinner.pack(pady=(26, 10))
        self.progress = ctk.CTkProgressBar(card, width=560, height=14,
                                           fg_color=PILL_GRAY, progress_color=PRIMARY_BLUE,
                                           corner_radius=7)
        self.progress.set(0)
        self.progress.pack(pady=(6, 26))

        threading.Thread(target=self._do_print, daemon=True).start()

    def _do_print(self):
        from core.printer import Printer, printer_block_reason
        printer = Printer()
        try:
            problem = printer_block_reason(printer)
        except Exception:
            problem = None
        if problem:
            try:
                self.after(0, lambda p=problem: self._on_paper_stuck(p))
            except Exception:
                pass
            return
        try:
            total_all = (int(self.end_page) if self.end_page else
                         FileReader.get_total_pages_fast(self.filepath))
        except Exception:
            total_all = 1
        end_page = self.end_page or total_all
        try:
            start_page = max(1, int(self.start_page or 1))
            end_page = max(start_page, min(int(end_page), total_all))
        except Exception:
            start_page, end_page = 1, total_all

        pages_in_job = max(1, end_page - start_page + 1)
        total_steps = pages_in_job * max(1, self.copies)
        try:
            images = printer._render_range(self.filepath, start_page, end_page)
        except Exception as e:
            print(f"Range render error: {e}")
            images = []
        prepared = [printer._prepare_mode(img, self.print_mode) for img in images]
        mode_tag = "bw" if (self.print_mode or "bw").lower() in ("bw", "b&w") else "color"
        color_arg = "B&W" if mode_tag == "bw" else "Color"

        use_sim = False
        try:
            from config import SIMULATION_MODE
            use_sim = bool(SIMULATION_MODE)
        except Exception:
            pass
        try:
            if not printer.get_printer_name():
                use_sim = True
        except Exception:
            use_sim = True

        step = 0
        print_failed = False
        if prepared:
            for _ in range(max(1, self.copies)):
                for img in prepared:
                    step += 1
                    ok = True
                    try:
                        if use_sim:
                            os.makedirs("temp/output", exist_ok=True)
                            img.save(os.path.join("temp/output", f"sim_print_page_{step}_{mode_tag}.png"))
                        else:
                            ok = printer.print_image(img, color_mode=color_arg, paper_size=self.paper_size)
                    except Exception as e:
                        print(f"Print step error: {e}")
                        ok = False
                    try:
                        self.after(0, lambda v=step / total_steps: self._set_progress(v))
                    except Exception:
                        pass
                    if not ok:
                        print_failed = True
                        break
                if print_failed:
                    break
        else:
            # Nothing rendered at all - that is a real failure, not a success.
            print_failed = True
            try:
                os.makedirs("temp/output", exist_ok=True)
                from PIL import Image
                Image.new("RGB", (800, 1124), "white").save(
                    os.path.join("temp/output", f"sim_print_page_1_{mode_tag}.png"))
            except Exception:
                pass

        # Real printing: wait for the spooler queue to drain, so "Done" only
        # appears once the printer has actually finished, not when it accepted
        # the job. Simulation mode has no queue, so it is skipped there.
        if print_failed:
            # Do NOT charge and do NOT say "Done" when a page did not print.
            try:
                self.after(0, self._on_print_failure)
            except Exception:
                pass
            return
        if not use_sim:
            try:
                self.after(0, self._show_printing_state)
            except Exception:
                pass
            drained = True
            try:
                timeout = max(90, total_steps * 30)

                def _tick(elapsed, count):
                    try:
                        self.after(0, lambda e=elapsed, c=count: self._on_queue_tick(e, c))
                    except Exception:
                        pass

                drained = printer.wait_until_idle(timeout=timeout, stall_timeout=25,
                                                  on_tick=_tick)
            except Exception:
                drained = False
            if not drained:
                # The queue never emptied. On these Epson inkjets Windows never
                # reports "paper out", so a stuck queue is the reliable signal
                # that no paper / a jam / offline stopped the job. Do not charge.
                # Also cancel the clogged job(s): leaving them latches the
                # printer's "paper out" bit, which then shows a false PAPER OUT
                # warning even after paper is loaded again.
                try:
                    printer.clear_stuck_jobs()
                except Exception:
                    pass
                try:
                    self.after(0, self._on_paper_stuck)
                except Exception:
                    pass
                return
        try:
            self.after(0, lambda: self._on_print_success(pages_in_job))
        except Exception:
            pass

    def _show_printing_state(self):
        """Show an active (indeterminate) bar while the printer physically prints."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.spinner.configure(text="Printing your pages\u2026",
                                   text_color=SECONDARY_TEXT)
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            if getattr(self, "paper_anim", None) is not None:
                self.paper_anim.start_loop()
        except Exception:
            pass

    def _set_progress(self, value):
        try:
            if not self.winfo_exists():
                return
            self.progress.set(value)
            if getattr(self, "paper_anim", None) is not None:
                self.paper_anim.set_progress(value)
        except Exception:
            pass

    def _on_queue_tick(self, elapsed, count):
        """Heartbeat while the spooler drains: proves the screen is alive.

        Shows 'Waiting for printer (Ns)' so a slow-but-healthy queue never
        looks frozen like the stuck-loading screenshot.
        """
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            if count and count > 0:
                self.spinner.configure(
                    text=f"Printing your pages\u2026  (waiting {int(elapsed)}s)",
                    text_color=SECONDARY_TEXT)
        except Exception:
            pass

    def _on_print_success(self, pages):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.coin_reader.deduct_credit(self.due)
        except Exception:
            pass
        try:
            with open("vendo_log.txt", "a", encoding="utf-8") as f:
                fname = os.path.basename(self.filepath)
                f.write(f"{time.strftime('%Y-%m-%d %X')} | File: {fname} | Pages: {pages}x{self.copies} | Mode: {self.print_mode} | Paid: \u20B1{self.due}\n")
        except Exception:
            pass
        try:
            winsound.Beep(1200, 200)
            winsound.Beep(1600, 300)
        except Exception:
            pass
        try:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            if getattr(self, "paper_anim", None) is not None:
                self.paper_anim.stop()
                self.paper_anim.show_success()
        except Exception:
            pass
        self.progress.set(1)
        try:
            self.icon.configure(text="\u2705", text_color=SUCCESS_GREEN)
            self.spinner.configure(text="Done! Please collect your documents \U0001F4C4",
                                   text_color=SUCCESS_GREEN)
        except Exception:
            pass
        # Proof-of-print receipt: show the customer exactly what was printed.
        try:
            try:
                from config import PAPER_SIZES
                paper_label = PAPER_SIZES.get(self.paper_size or "", {}).get("label", "A4")
            except Exception:
                paper_label = "A4"
            mode_label = "B&W" if (self.print_mode or "bw").lower() in ("bw", "b&w") else "Color"
            receipt = (f"{pages} page{'s' if pages != 1 else ''}  \u2022  "
                       f"{self.copies} cop{'y' if self.copies == 1 else 'ies'}  \u2022  "
                       f"{mode_label}  \u2022  {paper_label} paper  \u2022  Paid \u20B1{self.due}")
            self.receipt_lbl = ctk.CTkLabel(
                self.card, text=receipt, font=(UI_FONT, 17, "bold"),
                text_color=PRIMARY_TEXT, fg_color=PILL_GRAY, corner_radius=14,
                padx=18, pady=10)
            self.receipt_lbl.pack(pady=(16, 18))
        except Exception:
            pass
        try:
            self.after(4000, self._reset_to_welcome)
        except Exception:
            pass

    def _on_print_failure(self):
        # A page failed: keep the customer's credit (no charge) and tell them.
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            if getattr(self, "paper_anim", None) is not None:
                self.paper_anim.stop()
                self.paper_anim.show_error()
        except Exception:
            pass
        try:
            self.progress.set(0)
            self.progress.pack_forget()  # no progress bar under an error
        except Exception:
            pass
        try:
            self.icon.configure(text="\u26A0\uFE0F", text_color=WARNING_RED)
            self.spinner.configure(
                text="Printing failed \u2014 please ask staff for help.\nYou were not charged.",
                text_color=WARNING_RED, font=(UI_FONT, 18, "bold"))
        except Exception:
            pass
        try:
            winsound.Beep(400, 300)
            winsound.Beep(300, 400)
        except Exception:
            pass
        try:
            self.after(6000, self._reset_to_welcome)
        except Exception:
            pass

    def _on_paper_stuck(self, reason=None):
        # The spooler never drained: no paper, a jam, or the printer is offline.
        # Keep the customer's credit and tell them to call staff.
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            if getattr(self, "paper_anim", None) is not None:
                self.paper_anim.stop()
                self.paper_anim.show_error()
        except Exception:
            pass
        try:
            self.progress.set(0)
            self.progress.pack_forget()  # no progress bar under an error
        except Exception:
            pass
        try:
            message = (f"{reason} \u2014 please ask staff.\nYou were not charged."
                       if reason else
                       "Out of paper, jam, or printer offline \u2014 please ask staff.\nYou were not charged.")
            self.icon.configure(text="\u26A0\uFE0F", text_color=WARNING_RED)
            self.spinner.configure(
                text=message, text_color=WARNING_RED, font=(UI_FONT, 18, "bold"))
        except Exception:
            pass
        try:
            winsound.Beep(400, 300)
            winsound.Beep(300, 400)
        except Exception:
            pass
        try:
            self.after(7000, self._reset_to_welcome)
        except Exception:
            pass

    def _reset_to_welcome(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.back_callback("welcome")
        except Exception:
            pass
