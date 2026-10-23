import os
import io
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from PIL import Image, ImageDraw, ImageFont

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.jpg', '.jpeg', '.png'}

PREVIEW_BOX = (980, 680)
PREVIEW_ZOOM = 3.0


def _load_font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


class FileReader:
    @staticmethod
    def get_file_type(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return ext

    @staticmethod
    def read(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        metadata = {
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "detected_pages": 0,
            "file_type": ext
        }

        if ext == '.pdf':
            metadata.update(FileReader._read_pdf(filepath))
        elif ext == '.docx':
            metadata.update(FileReader._read_docx(filepath))
        elif ext in {'.jpg', '.jpeg', '.png'}:
            metadata.update(FileReader._read_image(filepath))

        return metadata

    @staticmethod
    def _read_pdf(filepath):
        page_count = 0
        try:
            doc = fitz.open(filepath)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1
        return {"detected_pages": page_count}

    @staticmethod
    def _read_docx(filepath):
        # Best: page count of the Word-converted PDF (matches preview/print).
        try:
            from core.docx_converter import convert_docx_to_pdf
            pdf_path = convert_docx_to_pdf(filepath)
            if pdf_path and os.path.exists(pdf_path):
                try:
                    doc = fitz.open(pdf_path)
                    n = len(doc)
                    doc.close()
                    if n > 0:
                        return {"detected_pages": n}
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback: paginate the real text layout so count matches preview.
        try:
            pages = FileReader._docx_fallback_page_count(filepath)
            return {"detected_pages": max(1, pages)}
        except Exception:
            pass
        try:
            doc = DocxDocument(filepath)
            paragraphs = len(doc.paragraphs)
            estimated_pages = max(1, (paragraphs + 29) // 30)
            return {"detected_pages": estimated_pages}
        except Exception:
            return {"detected_pages": 1}

    @staticmethod
    def _read_image(filepath):
        return {"detected_pages": 1}

    # ---- Preview engine (200 DPI, B&W toggle) ----
    @staticmethod
    def get_total_pages(filepath):
        try:
            return max(1, int(FileReader.read(filepath).get("detected_pages", 1)))
        except Exception:
            return 1

    @staticmethod
    def get_total_pages_fast(filepath):
        """Page count without starting Word.

        Building the file list must stay instant. The accurate DOCX count
        launches Microsoft Word, which can take many seconds per file and
        freezes the screen while it runs - so the list uses this cheap
        count instead. The exact count is still worked out when the file
        is opened, where a short wait is expected and the real page count
        is needed for pricing.
        """
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".pdf":
                doc = fitz.open(filepath)
                try:
                    return max(1, len(doc))
                finally:
                    doc.close()
            if ext in (".docx", ".doc"):
                try:
                    from core.docx_converter import get_converted_pdf
                    pdf_path = get_converted_pdf(filepath)
                    if pdf_path:
                        pdf = fitz.open(pdf_path)
                        try:
                            return max(1, len(pdf))
                        finally:
                            pdf.close()
                except Exception:
                    pass
                try:
                    return max(1, FileReader._docx_fallback_page_count(filepath))
                except Exception:
                    return 1
            return 1
        except Exception:
            return 1

    @staticmethod
    def _render_pdf_pil(filepath, page_num=0, zoom=None):
        doc = fitz.open(filepath)
        try:
            page_num = max(0, min(page_num, len(doc) - 1))
            page = doc.load_page(page_num)
            # High-res crisp render: 2.5x matrix = ~180 DPI, sharp at large size.
            mat = fitz.Matrix(zoom or PREVIEW_ZOOM, zoom or PREVIEW_ZOOM)
            pixmap = page.get_pixmap(matrix=mat)
            return Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
        finally:
            doc.close()

    @staticmethod
    def _render_image_pil(filepath):
        img = Image.open(filepath)
        return img.convert("RGB")

    @staticmethod
    def _render_docx_pil(filepath, page_num=0, allow_conversion=True):
        # Real Word layout first: convert via Word COM -> render that PDF page.
        if allow_conversion:
            try:
                from core.docx_converter import convert_docx_to_pdf
                pdf_path = convert_docx_to_pdf(filepath)
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        return FileReader._render_pdf_pil(pdf_path, page_num)
                    except Exception:
                        pass
            except Exception:
                pass
        # Fallback: high-quality Pillow text layout (A4 canvas, big fonts).
        try:
            return FileReader._docx_text_page_image(filepath, page_num)
        except Exception:
            return FileReader._docx_placeholder_card(filepath)

    # ---- Improved Pillow fallback: Word-like full page ----
    @staticmethod
    def _docx_wrap_paragraphs(filepath):
        """Return list of (text, kind) blocks: kind in ('title','h1','body','bullet')."""
        doc = DocxDocument(filepath)
        blocks = []
        try:
            for p in doc.paragraphs:
                text = (p.text or "").strip()
                if not text:
                    continue
                style = ""
                try:
                    style = (p.style.name or "").lower()
                except Exception:
                    style = ""
                if "title" in style:
                    blocks.append((text, "title"))
                elif "heading 1" in style:
                    blocks.append((text, "h1"))
                elif "heading" in style:
                    blocks.append((text, "h1"))
                elif text.startswith(("•", "-", "·")):
                    blocks.append((text.lstrip("•-· ").strip(), "bullet"))
                else:
                    # ALL-CAPS short line = likely a resume section header.
                    if len(text) <= 48 and text.isupper():
                        blocks.append((text, "h1"))
                    else:
                        blocks.append((text, "body"))
        finally:
            try:
                doc.close()
            except Exception:
                pass
        return blocks

    @staticmethod
    def _docx_layout_lines(filepath, max_width_px=660):
        """Wrap blocks into drawable lines. Returns (lines, total_pages_hint)."""
        title_font = _load_font("arialbd.ttf", 30)
        h1_font = _load_font("arialbd.ttf", 23)
        body_font = _load_font("arial.ttf", 21)
        probe = Image.new("RGB", (10, 10), "white")
        d = ImageDraw.Draw(probe)

        def wrap(text, font):
            words, lines, cur = text.split(), [], ""
            for w in words:
                trial = (cur + " " + w).strip()
                try:
                    width = d.textlength(trial, font=font)
                except Exception:
                    width = len(trial) * 10
                if width <= max_width_px:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        try:
            blocks = FileReader._docx_wrap_paragraphs(filepath)
        except Exception:
            blocks = []
        if not blocks:
            # Always return the same 4-tuple: callers unpack four values, so a
            # short tuple here used to crash on empty / image-only documents.
            return [], title_font, h1_font, body_font

        lines = []  # (text, kind)
        for text, kind in blocks:
            font = title_font if kind == "title" else (h1_font if kind == "h1" else body_font)
            prefix = "• " if kind == "bullet" else ""
            for ln in wrap(prefix + text, font):
                lines.append((ln, kind))
            lines.append(("", "gap"))
        return lines, title_font, h1_font, body_font

    @staticmethod
    def _docx_fallback_page_count(filepath):
        lines, _, _, _ = FileReader._docx_layout_lines(filepath)
        if not lines:
            return 1
        # A4 canvas 800x1130, margins: ~34 lines fit per page at these sizes.
        per_page = 34
        return max(1, (len(lines) + per_page - 1) // per_page)

    @staticmethod
    def _docx_text_page_image(filepath, page_num=0):
        """Word-like full page: A4 portrait canvas, proper margins, big fonts."""
        W, H = 800, 1130
        MARGIN_X, TOP, BOTTOM = 70, 60, 80
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)
        # Paper edge
        draw.rectangle([0, 0, W - 1, H - 1], outline="#E5E7EB", width=3)

        lines, title_font, h1_font, body_font = FileReader._docx_layout_lines(
            filepath, max_width_px=W - 2 * MARGIN_X)
        if not lines:
            return FileReader._docx_placeholder_card(filepath)

        per_page = 34
        total_pg = max(1, (len(lines) + per_page - 1) // per_page)
        page_num = max(0, min(page_num, total_pg - 1))
        chunk = lines[page_num * per_page:(page_num + 1) * per_page]

        y = TOP
        for ln, kind in chunk:
            if y > H - BOTTOM:
                break
            if ln == "":
                y += 12
                continue
            if kind == "title":
                try:
                    w_txt = draw.textlength(ln, font=title_font)
                except Exception:
                    w_txt = len(ln) * 14
                draw.text(((W - w_txt) / 2, y), ln, fill="#1F3A5F", font=title_font)
                y += 44
            elif kind == "h1":
                draw.text((MARGIN_X, y), ln.upper(), fill="#1F3A5F", font=h1_font)
                y += 30
                draw.line([(MARGIN_X, y), (W - MARGIN_X, y)], fill="#1F3A5F", width=2)
                y += 14
            else:
                draw.text((MARGIN_X, y), ln, fill="#111827", font=body_font)
                y += 30
        # Footer page number
        try:
            foot = f"Page {page_num + 1} of {total_pg}"
            fw = draw.textlength(foot, font=body_font)
            draw.text(((W - fw) / 2, H - 48), foot, fill="#9CA3AF", font=body_font)
        except Exception:
            pass
        return img

    @staticmethod
    def _docx_placeholder_card(filepath):
        w, h = 600, 780
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w - 1, h - 1], outline="#E5E7EB", width=4)
        draw.rectangle([40, 40, w - 40, 200], fill="#EFF6FF", outline="#2563EB", width=2)
        title_font = _load_font("arialbd.ttf", 28)
        body_font = _load_font("arial.ttf", 20)
        fname = os.path.basename(filepath)
        if len(fname) > 28:
            fname = fname[:25] + "..."
        try:
            total = FileReader._docx_fallback_page_count(filepath)
        except Exception:
            total = 1
        draw.text((60, 70), "DOCX Document", fill="#111827", font=title_font)
        draw.text((60, 115), fname, fill="#4B5563", font=body_font)
        draw.text((60, 260), f"Approx. {total} page(s)", fill="#111827", font=body_font)
        draw.text((60, 300), "Preview not available.", fill="#4B5563", font=body_font)
        draw.text((60, 330), "File will print from", fill="#4B5563", font=body_font)
        draw.text((60, 360), "the original document.", fill="#4B5563", font=body_font)
        return img

    @staticmethod
    def render_page_pil(filepath, page_num=0, is_bw=False, allow_docx_conversion=True):
        """Render one page (0-based) as a PIL image at 200 DPI."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".pdf":
            pil = FileReader._render_pdf_pil(filepath, page_num)
        elif ext in {".jpg", ".jpeg", ".png"}:
            pil = FileReader._render_image_pil(filepath)
        elif ext == ".docx":
            pil = FileReader._render_docx_pil(filepath, page_num, allow_conversion=allow_docx_conversion)
        else:
            pil = Image.new("RGB", (600, 780), "white")
        if is_bw:
            pil = pil.convert("L")
        return pil

    @staticmethod
    def render_page_preview(filepath, page_num=0, is_bw=False, box=None, paper=None,
                            allow_docx_conversion=True):
        """Render page_num (0-based) as a CTkImage laid on a sheet of paper.

        The white sheet takes the aspect ratio of the chosen paper size
        (A4 / Long / Short), so switching size visibly changes the sheet's
        shape: Long is taller/narrower, Short is shorter/wider. The page
        content is scaled to fit inside it. B&W applies grayscale so the
        toggle updates in real time.
        """
        import customtkinter as ctk
        try:
            pil = FileReader.render_page_pil(
                filepath, page_num, is_bw,
                allow_docx_conversion=allow_docx_conversion)
        except Exception:
            pil = Image.new("RGB", (600, 780), "white")
            if is_bw:
                pil = pil.convert("L")
        box_w, box_h = box or PREVIEW_BOX
        box_w, box_h = max(200, int(box_w)), max(200, int(box_h))
        try:
            if pil.mode == "L":
                # CTkImage displays RGB reliably; image stays grayscale.
                pil = pil.convert("RGB")
            # Sheet aspect ratio from the selected paper (fall back to page).
            if paper and paper[0] and paper[1]:
                pw_mm, ph_mm = float(paper[0]), float(paper[1])
            else:
                sw0, sh0 = pil.size
                pw_mm, ph_mm = float(sw0), float(sh0)
            ratio = ph_mm / max(1.0, pw_mm)  # height / width

            # The white sheet fills the box height (narrower for Long,
            # wider for Short), so the change in shape is obvious.
            sheet_h = max(40, box_h - 16)
            sheet_w = int(sheet_h / ratio)
            if sheet_w > box_w - 16:
                sheet_w = max(40, box_w - 16)
                sheet_h = int(sheet_w * ratio)
            sheet_h = max(40, sheet_h)

            sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
            # Fit the page content inside the sheet with a small print margin.
            margin = max(6, int(min(sheet_w, sheet_h) * 0.035))
            inner_w = max(1, sheet_w - margin * 2)
            inner_h = max(1, sheet_h - margin * 2)
            iw, ih = pil.size
            scale = min(inner_w / max(1, iw), inner_h / max(1, ih))
            tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
            content = pil.resize((tw, th), Image.LANCZOS)
            sheet.paste(content, ((sheet_w - tw) // 2, margin))

            # Thin paper edge so the sheet reads as paper on the grey panel.
            ImageDraw.Draw(sheet).rectangle(
                [0, 0, sheet_w - 1, sheet_h - 1], outline="#D1D5DB", width=2)

            buf = io.BytesIO()
            sheet.save(buf, format="PNG")
            buf.seek(0)
            owned = Image.open(buf)
            owned.load()
            return ctk.CTkImage(light_image=owned, dark_image=owned, size=(sheet_w, sheet_h))
        except Exception:
            try:
                rgb = pil.convert("RGB")
            except Exception:
                rgb = Image.new("RGB", (box_w, box_h), "white")
            return ctk.CTkImage(light_image=rgb, dark_image=rgb, size=(box_w, box_h))
