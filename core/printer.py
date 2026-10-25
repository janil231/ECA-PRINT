try:
    import win32print
    import win32ui
except Exception:
    win32print = None
    win32ui = None
import os
import fitz
from PIL import Image, ImageDraw, ImageFont
import io
import winsound
from docx import Document as DocxDocument

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png'}


class Printer:
    # Virtual printers never print paper - they open a Save-As dialog or a
    # note window. Without this guard, a demo laptop with no Epson attached
    # would silently pick "Microsoft Print to PDF" as the default printer and
    # the kiosk would appear to hang behind a file dialog.
    _VIRTUAL_HINTS = (
        "print to pdf", "onenote", "fax", "xps", "send to onenote",
        "anydesk", "cutepdf", "adobe pdf", "pdf24", "dopdf",
        "microsoft print to", "microsoft xps",
    )

    @classmethod
    def _is_virtual_printer(cls, name):
        low = (name or "").lower()
        return any(hint in low for hint in cls._VIRTUAL_HINTS)

    def __init__(self):
        # Never throw when no printer is installed - fall back to file saves.
        self.default_printer = None
        self.printer_name = None
        try:
            if win32print is not None:
                try:
                    self.default_printer = win32print.GetDefaultPrinter()
                except Exception:
                    self.default_printer = None
                found = self._find_epson_l120()
                if found:
                    # A real Epson EcoTank is attached - print for real.
                    self.printer_name = found
                elif self.default_printer and not self._is_virtual_printer(self.default_printer):
                    # Some other physical printer - still usable.
                    self.printer_name = self.default_printer
                else:
                    # No physical printer (only PDF / OneNote drivers). Treat
                    # this as simulation so pages are saved instead of
                    # opening a Save-As dialog nobody is there to answer.
                    self.printer_name = None
        except Exception:
            self.default_printer = None
            self.printer_name = None

    def _find_epson_l120(self):
        # Match the Epson EcoTank family (L120 / L121 / ...) case-insensitively,
        # since Windows reports the name as e.g. "EPSON L121 Series".
        try:
            if win32print is None:
                return None
            ports = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            for printer in ports:
                name = (printer[2] or "")
                low = name.lower()
                if "epson" in low or "l120" in low or "l121" in low:
                    return name
        except Exception:
            pass
        return None

    def get_printer_name(self):
        return self.printer_name

    def get_job_count(self):
        """How many jobs are still waiting in the spooler queue for our printer."""
        try:
            if win32print is None or not self.printer_name:
                return 0
            handle = win32print.OpenPrinter(self.printer_name)
            try:
                jobs = win32print.EnumJobs(handle, 0, -1, 1)
            finally:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass
            return len(jobs)
        except Exception:
            return 0

    def queue_error(self):
        """True when a spooled job has flagged an error (paper out, jam, offline).

        This is the fast, reliable signal on Epson inkjets, whose printer-level
        status stays silent: the spooler marks the stuck job itself.
        """
        try:
            if win32print is None or not self.printer_name:
                return False
            handle = win32print.OpenPrinter(self.printer_name)
            try:
                jobs = win32print.EnumJobs(handle, 0, -1, 1)
            finally:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass
            # JOB_INFO_1: field 7 is the Status bitmask.
            bad = 0x00000002 | 0x00000020 | 0x00000040 | 0x00000200 | 0x00000400
            for job in jobs:
                try:
                    if isinstance(job, dict):
                        status = int(job.get("Status", 0) or 0)
                    else:
                        status = int(job[7] or 0)
                except Exception:
                    continue
                if status & bad:
                    return True
        except Exception:
            pass
        return False

    def clear_stuck_jobs(self, only_errored=False):
        """Cancel jobs clogging the spooler queue; return how many were cleared.

        A job left stuck after a paper-out or a crash keeps the printer's
        "paper out" status bit latched, so Windows then reports PAPER OUT even
        with paper loaded. Clearing the queue self-heals that. With no printer
        (simulation) this is a safe no-op.
        """
        cleared = 0
        try:
            if win32print is None or not self.printer_name:
                return 0
            handle = win32print.OpenPrinter(self.printer_name)
            try:
                jobs = win32print.EnumJobs(handle, 0, -1, 1)
                # JOB status bits (different meanings from printer status!):
                # 0x02 error, 0x20 offline, 0x40 paper out, 0x200 blocked,
                # 0x400 user intervention. 0x08 spooling and 0x10 printing are
                # NORMAL, so they must never count as trouble.
                bad = 0x00000002 | 0x00000020 | 0x00000040 | 0x00000200 | 0x00000400
                for job in jobs:
                    try:
                        if isinstance(job, dict):
                            jid = job.get("JobId")
                            status = int(job.get("Status", 0) or 0)
                        else:
                            jid = job[1]
                            status = int(job[7] or 0)
                        if only_errored and not (status & bad):
                            continue
                        if jid is None:
                            continue
                        win32print.SetJob(handle, jid, 0, None, win32print.JOB_CONTROL_CANCEL)
                        cleared += 1
                    except Exception:
                        continue
            finally:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass
        except Exception:
            pass
        return cleared

    def get_status(self):
        """Best-effort printer health as (state, message).

        state is "ok", "warning" or "error". Inkjet drivers often report no
        detail at all, so anything we cannot read is treated as ok.

        Epson inkjets LATCH their paper-out / jam / error bits after one bad
        job, so the bit stays set even once paper is loaded again. Trusting it
        alone caused a false "PAPER OUT" on a loaded printer, so those bits are
        only believed while a job is actually waiting in the queue.
        """
        if not self.printer_name or win32print is None:
            return ("warning", "No printer")
        try:
            handle = win32print.OpenPrinter(self.printer_name)
            try:
                info = win32print.GetPrinter(handle, 2)
                try:
                    queued = len(win32print.EnumJobs(handle, 0, -1, 1))
                except Exception:
                    queued = 0
            finally:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass
            status = 0
            try:
                status = int(info.get("Status", 0) or 0)
            except Exception:
                try:
                    status = int(info[18])
                except Exception:
                    status = 0
            # Work Offline (printer unplugged / powered off) is set in the
            # printer's Attributes, not its Status. Without this check a job
            # queues forever and the screen sits on "Printing..." for a minute.
            try:
                attrs = int(info.get("Attributes", 0) or 0)
            except Exception:
                try:
                    attrs = int(info[13])
                except Exception:
                    attrs = 0
            if attrs & 0x00000400:
                return ("error", "Printer offline")
            # Offline is trustworthy at any time (not latched by a bad job).
            if status & 0x00000080:
                return ("error", "Printer offline")
            # Everything else only counts while a job is really queued, so a
            # stale latched bit on an idle printer no longer false-alarms.
            if queued > 0:
                for bit, msg in (
                    (0x00000010, "Paper out"),
                    (0x00000008, "Paper jam"),
                    (0x00000002, "Printer error"),
                    (0x00100000, "Needs attention"),
                    (0x00040000, "Ink low"),
                    (0x00200000, "Door open"),
                ):
                    if status & bit:
                        return ("error", msg)
            return ("ok", "Ready")
        except Exception:
            return ("ok", "Ready")

    def wait_until_idle(self, timeout=240, poll=1.0, initial=1.5, stall_timeout=40,
                          on_tick=None):
        """Block until the printer queue is empty, i.e. printing really finished.

        Returns True when the queue drained, and False the moment the job is
        clearly stuck - a flagged job, or a queue that stops making progress.
        Never raises, and returns True at once with no printer (simulation).
        on_tick(elapsed_seconds, job_count) is called each poll so the UI can
        show a heartbeat instead of a frozen spinner.
        """
        try:
            if not self.printer_name:
                return True
            import time
            # Let the spooler register the job(s) we just submitted.
            time.sleep(initial)
            deadline = time.time() + max(30, int(timeout))
            empty_streak = 0
            last_count = None
            last_change = time.time()
            completed_any = False
            start_ts = time.time()
            while time.time() < deadline:
                count = self.get_job_count()
                try:
                    if on_tick is not None:
                        on_tick(time.time() - start_ts, count)
                except Exception:
                    pass
                if count == 0:
                    empty_streak += 1
                    if empty_streak >= 2:
                        return True
                    time.sleep(poll)
                    continue
                empty_streak = 0
                # A flagged job means no paper / jam / offline: fail at once.
                if self.queue_error():
                    return False
                # Stall guard: a queue that never drains is how an empty tray or
                # a jam shows up on these Epson inkjets, whose printer status
                # stays silent. Fire well before the full timeout, allowing the
                # first page extra room for inkjet warm-up.
                if last_count is None or count != last_count:
                    if last_count is not None and count < last_count:
                        completed_any = True
                    last_count = count
                    last_change = time.time()
                else:
                    limit = stall_timeout if completed_any else stall_timeout + 30
                    if time.time() - last_change > limit:
                        return False
                time.sleep(poll)
            return False
        except Exception:
            return False

    def render_pdf_to_image(self, filepath):
        try:
            doc = fitz.open(filepath)
            images = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pixmap = page.get_pixmap(dpi=300)
                img_data = pixmap.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)
            doc.close()
            return images
        except Exception as e:
            print(f"PDF render error: {e}")
            return []

    def render_docx_to_image(self, filepath):
        # Print exactly what the preview shows: the Word-converted PDF.
        try:
            from core.docx_converter import convert_docx_to_pdf
            pdf_path = convert_docx_to_pdf(filepath)
            if pdf_path and os.path.exists(pdf_path):
                try:
                    doc = fitz.open(pdf_path)
                    images = []
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pixmap = page.get_pixmap(dpi=300)
                        images.append(Image.open(io.BytesIO(pixmap.tobytes("png"))))
                    doc.close()
                    if images:
                        return images
                except Exception as e:
                    print(f"DOCX converted-PDF render error: {e}")
        except Exception as e:
            print(f"DOCX conversion error: {e}")
        print(f"DOCX print blocked: no converted PDF for {os.path.basename(filepath)}")
        return []

    def render_image_to_image(self, filepath):
        try:
            img = Image.open(filepath)
            if img.width > img.height:
                img = img.rotate(90, expand=True)
            return [img]
        except Exception as e:
            print(f"Image render error: {e}")
            return []

    def _render_range(self, filepath, start_page=1, end_page=None):
        """Render ONLY pages start_page..end_page (1-indexed, inclusive)."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            try:
                doc = fitz.open(filepath)
                total = len(doc)
                s = max(1, int(start_page or 1))
                e = int(end_page) if end_page else total
                s = max(1, min(s, total))
                e = max(s, min(e, total))
                images = []
                for p in range(s - 1, e):
                    page = doc.load_page(p)
                    pixmap = page.get_pixmap(dpi=300)
                    images.append(Image.open(io.BytesIO(pixmap.tobytes("png"))))
                doc.close()
                return images
            except Exception as e:
                print(f"PDF range render error: {e}")
                return []
        if ext in {'.docx', '.doc'}:
            # Converted-PDF pages first so range/copies match the preview.
            try:
                from core.docx_converter import convert_docx_to_pdf
                pdf_path = convert_docx_to_pdf(filepath)
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        doc = fitz.open(pdf_path)
                        total = len(doc)
                        s = max(1, int(start_page or 1))
                        e = int(end_page) if end_page else total
                        s = max(1, min(s, total))
                        e = max(s, min(e, total))
                        images = []
                        for p in range(s - 1, e):
                            page = doc.load_page(p)
                            pixmap = page.get_pixmap(dpi=300)
                            images.append(Image.open(io.BytesIO(pixmap.tobytes("png"))))
                        doc.close()
                        if images:
                            return images
                    except Exception as e:
                        print(f"DOCX range render error: {e}")
            except Exception as e:
                print(f"DOCX range conversion error: {e}")
            print(f"DOCX range print blocked: no converted PDF for {os.path.basename(filepath)}")
            return []
        if ext in {'.jpg', '.jpeg', '.png'}:
            return self.render_image_to_image(filepath)
        return []

    def _prepare_mode(self, image, print_mode="bw"):
        mode = (print_mode or "bw").lower()
        is_bw = mode in ("bw", "b&w", "black", "blackwhite", "black_white")
        try:
            if is_bw:
                return image.convert("L").convert("RGB")
            return image.convert("RGB")
        except Exception:
            return image

    def print_job(self, filepath, start_page=1, end_page=None, copies=1, print_mode="bw", paper_size=None):
        """Print pages start_page..end_page (1-indexed) repeated `copies` times.

        Simulation / no-printer fallback saves to
        temp/output/sim_print_page_<n>_<bw|color>.png without raising.
        """
        try:
            copies = max(1, min(int(copies or 1), 10))
        except Exception:
            copies = 1
        mode_tag = "bw" if (print_mode or "bw").lower() in ("bw", "b&w") else "color"
        color_arg = "B&W" if mode_tag == "bw" else "Color"

        images = self._render_range(filepath, start_page, end_page)
        if not images:
            return False

        # Simulation path (also used when no printer is configured).
        use_sim = False
        try:
            from config import SIMULATION_MODE
            use_sim = bool(SIMULATION_MODE)
        except Exception:
            use_sim = False
        if not self.printer_name:
            use_sim = True

        n = 0
        ok = 0
        for _ in range(copies):
            for img in images:
                n += 1
                prepared = self._prepare_mode(img, print_mode)
                if use_sim:
                    try:
                        os.makedirs("temp/output", exist_ok=True)
                        path = os.path.join("temp/output", f"sim_print_page_{n}_{mode_tag}.png")
                        prepared.save(path)
                        ok += 1
                    except Exception as e:
                        print(f"Simulation save error: {e}")
                else:
                    try:
                        if self.print_image(prepared, color_mode=color_arg, paper_size=paper_size):
                            ok += 1
                    except Exception as e:
                        print(f"print_job page error: {e}")
        return ok > 0

    def _fallback_save(self, image):
        """Graceful fallback: save a page to temp/output/ instead of raising."""
        try:
            import time
            os.makedirs("temp/output", exist_ok=True)
            stamp = int(time.time() * 1000) % 100000
            path = os.path.join("temp/output", f"printed_page_fallback_{stamp}.png")
            try:
                image.convert("RGB").save(path)
            except Exception:
                # Last resort placeholder
                Image.new("RGB", (800, 1124), "white").save(path)
            print(f"[Printer] No printer available - saved fallback: {path}")
            return True
        except Exception as e:
            print(f"[Printer] Fallback save failed: {e}")
            return False

    def _paper_win_code(self, paper_size):
        """Map a config paper key ('a4'/'long'/'short') to a Windows DMPAPER code."""
        try:
            from config import PAPER_SIZES
            meta = PAPER_SIZES.get(paper_size or "")
            if meta:
                return int(meta.get("win_code"))
        except Exception:
            pass
        return None

    def _make_printer_dc(self, paper_win_code=None):
        """Create a printer DC, applying the paper size via DEVMODE when possible.

        Returns (hdc, hwnd) where hwnd is the raw HDC handle PIL draws onto.
        """
        import win32ui
        devmode = None
        if paper_win_code is not None:
            try:
                import win32print
                hprinter = win32print.OpenPrinter(self.printer_name)
                try:
                    info = win32print.GetPrinter(hprinter, 2)
                    devmode = info["pDevMode"]
                    devmode.PaperSize = int(paper_win_code)
                    # Windows only honours the new page size when the matching
                    # DM_PAPERSIZE bit is set in Fields - without this the
                    # Long/Short choice was silently ignored.
                    dm_papersize = 0x00000002
                    try:
                        import win32con
                        dm_papersize = win32con.DM_PAPERSIZE
                    except Exception:
                        pass
                    try:
                        devmode.Fields = int(devmode.Fields) | dm_papersize
                    except Exception:
                        pass
                finally:
                    win32print.ClosePrinter(hprinter)
            except Exception:
                devmode = None
        if devmode is not None:
            try:
                import win32gui
                handle = win32gui.CreateDC("WINSPOOL", self.printer_name, devmode)
                return win32ui.CreateDCFromHandle(handle), handle
            except Exception:
                pass
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(self.printer_name)
        # Second chance to apply the paper size on a plain printer DC.
        if devmode is not None:
            try:
                hdc.ResetDC(devmode)
            except Exception:
                pass
        return hdc, hdc.GetHandleOutput()

    def print_image(self, image, color_mode="B&W", paper_size=None):
        # Prepare pixels first (works even with no printer installed).
        try:
            if color_mode == "B&W":
                prepared = image.convert("L").convert("RGB")
            else:
                prepared = image.convert("RGB")
        except Exception as e:
            print(f"Print prepare error: {e}")
            if self.printer_name:
                return False
            return self._fallback_save(image)

        # No printer configured -> fallback immediately, no exception.
        if not self.printer_name:
            return self._fallback_save(prepared)

        try:
            import win32print  # noqa: F401 (kept for OpenPrinter parity)
            import win32ui  # noqa: F401
            from PIL import ImageWin
        except Exception as e:
            print(f"Print backend missing ({e}) - print failed.")
            return False

        paper_win_code = self._paper_win_code(paper_size)

        hdc = None
        try:
            hdc, hwnd = self._make_printer_dc(paper_win_code)

            # Printable area via standard GDI caps (no SetViewportSize - it does not exist).
            try:
                HORZRES, VERTRES = 8, 10
                try:
                    import win32con
                    HORZRES, VERTRES = win32con.HORZRES, win32con.VERTRES
                except Exception:
                    pass
                page_w = hdc.GetDeviceCaps(HORZRES)
                page_h = hdc.GetDeviceCaps(VERTRES)
            except Exception:
                page_w, page_h = prepared.size

            # Fit the page inside the printable area WITHOUT stretching:
            # keep the image's real proportions and centre it on the sheet.
            try:
                img_w, img_h = prepared.size
                if img_w > 0 and img_h > 0 and page_w > 0 and page_h > 0:
                    scale = min(page_w / float(img_w), page_h / float(img_h))
                    draw_w = max(1, int(img_w * scale))
                    draw_h = max(1, int(img_h * scale))
                else:
                    draw_w, draw_h = page_w, page_h
            except Exception:
                draw_w, draw_h = page_w, page_h
            off_x = max(0, (page_w - draw_w) // 2)
            off_y = max(0, (page_h - draw_h) // 2)

            hdc.StartDoc("ECA Print Job")
            hdc.StartPage()
            # Render the PIL image onto the printer device context.
            dib = ImageWin.Dib(prepared)
            dib.draw(hwnd, (off_x, off_y, off_x + draw_w, off_y + draw_h))
            hdc.EndPage()
            hdc.EndDoc()
            return True
        except Exception as e:
            print(f"Print error ({e}) - job failed.")
            try:
                if hdc is not None:
                    try:
                        hdc.AbortDoc()
                    except Exception:
                        pass
            except Exception:
                pass
            return False
        finally:
            try:
                if hdc is not None:
                    hdc.DeleteDC()
            except Exception:
                pass

    def print_file(self, filepath, color_mode="B&W"):
        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.pdf':
            images = self.render_pdf_to_image(filepath)
        elif ext in {'.docx', '.doc'}:
            images = self.render_docx_to_image(filepath)
        elif ext in {'.jpg', '.jpeg', '.png'}:
            images = self.render_image_to_image(filepath)
        else:
            return False

        success_count = 0
        for img in images:
            if self.print_image(img, color_mode):
                success_count += 1

        return bool(images) and success_count == len(images)


def printer_block_reason(printer=None):
    try:
        from config import SIMULATION_MODE
        if SIMULATION_MODE:
            return None
    except Exception:
        pass
    try:
        p = printer if printer is not None else Printer()
    except Exception:
        return None
    try:
        if not p.get_printer_name():
            return "No printer connected"
    except Exception:
        pass
    try:
        state, message = p.get_status()
    except Exception:
        return None
    if state != "error":
        return None
    return message or "Printer error"