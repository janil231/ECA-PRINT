"""DOCX -> PDF conversion via Microsoft Word COM, with caching.

- Converts .docx to temp/converted/<name>_<mtime>.pdf using Word (FileFormat=17).
- Caches: if the cached PDF is newer than the docx, reuse it (no reconvert).
- All failures return None so callers can block printing instead of using a
  reformatted text fallback.
"""
import os
import hashlib
import threading

CONVERT_DIR = os.path.join("temp", "converted")
_CONVERT_LOCK = threading.Lock()


def _cache_path(docx_path):
    try:
        base = os.path.splitext(os.path.basename(docx_path))[0]
        try:
            mtime = str(int(os.path.getmtime(docx_path)))
        except Exception:
            mtime = "0"
        key = hashlib.md5(f"{os.path.abspath(docx_path)}|{mtime}".encode()).hexdigest()[:10]
        safe_base = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in base)[:40]
        return os.path.join(CONVERT_DIR, f"{safe_base}_{key}.pdf")
    except Exception:
        return None


def _valid_pdf(pdf_path):
    try:
        return bool(pdf_path) and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0
    except Exception:
        return False


def _remove_partial(pdf_path):
    try:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
    except Exception:
        pass


def get_converted_pdf(docx_path):
    """Return cached converted PDF path if it exists, else None."""
    pdf_path = _cache_path(docx_path)
    if _valid_pdf(pdf_path):
        return pdf_path
    return None


def convert_docx_to_pdf(docx_path):
    """Convert docx -> PDF via Word COM. Returns pdf path or None.

    Cached: skips Word entirely when a fresh converted PDF already exists.
    Never raises - returns None on any failure.
    """
    try:
        os.makedirs(CONVERT_DIR, exist_ok=True)
    except Exception:
        return None

    cached = get_converted_pdf(docx_path)
    if cached:
        return cached

    pdf_path = _cache_path(docx_path)
    if not pdf_path:
        return None

    with _CONVERT_LOCK:
        cached = get_converted_pdf(docx_path)
        if cached:
            return cached

        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:
            print(f"[DOCX] Word COM unavailable: {exc}")
            return None

        com_initialized = False
        word = None
        doc = None
        try:
            pythoncom.CoInitialize()
            com_initialized = True
            try:
                word = win32com.client.DispatchEx("Word.Application")
            except Exception:
                word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            try:
                word.ScreenUpdating = False
            except Exception:
                pass
            try:
                word.AutomationSecurity = 3
            except Exception:
                pass

            abs_docx = os.path.abspath(docx_path)
            abs_pdf = os.path.abspath(pdf_path)
            doc = word.Documents.Open(
                abs_docx, ReadOnly=True, AddToRecentFiles=False,
                ConfirmConversions=False)
            doc.SaveAs(abs_pdf, FileFormat=17)
        except Exception as exc:
            print(f"[DOCX] conversion failed for {os.path.basename(docx_path)}: {exc}")
            _remove_partial(pdf_path)
            return None
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        if _valid_pdf(pdf_path):
            return pdf_path
        _remove_partial(pdf_path)
        print(f"[DOCX] Word produced no PDF for {os.path.basename(docx_path)}")
        return None
