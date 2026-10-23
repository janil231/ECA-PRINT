"""Read vendo_log.txt and summarise sales for the admin panel.

The printing screen writes one line per finished job in this shape:

    2025-01-02 14:03:11 | File: resume.docx | Pages: 2x1 | Mode: bw | Paid: ₱4

This module parses those lines so the staff panel can show jobs, pages and
revenue for today (and all time) without anyone opening the file by hand.
"""
import re
from datetime import date

try:
    from config import LOG_FILE
except Exception:
    LOG_FILE = "vendo_log.txt"

# Tolerant matcher: extra spaces, and files with " | " in the name still work
# because the filename is captured lazily up to the first " | Pages:".
_LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*File:\s*(?P<file>.*?)\s*\|"
    r"\s*Pages:\s*(?P<pages>\d+)x(?P<copies>\d+)\s*\|\s*Mode:\s*(?P<mode>.*?)\s*\|"
    r"\s*Paid:\s*\u20B1(?P<paid>\d+(?:\.\d+)?)"
)


def read_entries(log_path=None):
    """Return every parsed sale, oldest first. Missing file -> empty list."""
    path = log_path or LOG_FILE
    entries = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = _LINE.match(line.strip())
                if not m:
                    continue
                d = m.groupdict()
                try:
                    paid = float(d["paid"])
                except Exception:
                    paid = 0.0
                entries.append({
                    "date": d["ts"][:10],
                    "time": d["ts"][11:],
                    "file": d["file"],
                    "pages": int(d["pages"]),
                    "copies": int(d["copies"]),
                    "mode": d["mode"],
                    "paid": paid,
                })
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return entries


def summarise(entries):
    return {
        "jobs": len(entries),
        "pages": sum(e["pages"] * e["copies"] for e in entries),
        "revenue": sum(e["paid"] for e in entries),
    }


def today_summary(log_path=None):
    today = date.today().strftime("%Y-%m-%d")
    s = summarise([e for e in read_entries(log_path) if e["date"] == today])
    s["date"] = today
    return s


def all_time_summary(log_path=None):
    return summarise(read_entries(log_path))


def recent(n=5, log_path=None):
    return read_entries(log_path)[-n:][::-1]
