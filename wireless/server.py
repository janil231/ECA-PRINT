import os
import re
import sys
import json
import socket
from flask import Flask, render_template, request, jsonify
import threading


def _template_dir():
    # Works both when run from source and when bundled into one .exe.
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    packaged = os.path.join(base, "wireless", "templates")
    if os.path.isdir(packaged):
        return packaged
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


app = Flask(__name__, template_folder=_template_dir())
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "temp", "uploads")

# Phone uploads: only these file types, and never bigger than this.
ALLOWED_UPLOAD_EXT = {".pdf", ".docx", ".jpg", ".jpeg", ".png"}
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


def _safe_upload_name(name):
    """Turn a phone-supplied filename into a safe name inside temp/.

    Strips any folder parts and characters that could climb out of the
    upload folder (e.g. '..\\..\\main.py'), while keeping non-English
    letters so Filipino filenames still work.
    """
    raw = str(name or "").replace("\\", "/")
    raw = raw.split("/")[-1]
    raw = raw.replace("\x00", "")
    raw = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw).strip(" .")
    return raw


def get_hotspot_ip():
    # Windows Mobile Hotspot hands out 192.168.137.x and puts the gateway
    # (the kiosk itself) at .1. Phones on networks with AP isolation can
    # still reach this address, so prefer it whenever tethering is active.
    try:
        import psutil
    except Exception:
        return None
    try:
        stats = psutil.net_if_stats()
        for name, addrs in psutil.net_if_addrs().items():
            iface = stats.get(name)
            if iface is not None and not iface.isup:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address.startswith("192.168.137."):
                    return addr.address
    except Exception:
        pass
    return None


def get_local_ip():
    # Prefer a real LAN IP (phone can scan it). Fallback to 127.0.0.1 only if nothing else works.
    hotspot = get_hotspot_ip()
    if hotspot:
        return hotspot
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    # Fallback: scan common LAN subnets first, then 127.0.0.1
    for fallback in ["192.168.1.1", "192.168.0.1", "192.168.137.1", "10.0.0.1", "10.0.0.2"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((fallback, 1))
            ip = s.getsockname()[0]
            s.close()
            if ip.startswith(("192.168.", "10.")) or ip == "127.0.0.1":
                return ip
        except Exception:
            continue
    return "127.0.0.1"



@app.errorhandler(413)
def _too_large(_e):
    return jsonify({"error": "File is too big (50 MB max)"}), 413


def _qr_data_url(url):
    """QR code for the kiosk URL as an inline PNG data URL.

    Rendered locally so the page never depends on an external QR service
    and always encodes the real LAN address (the old page hard-coded
    localhost, which no phone could use).
    """
    try:
        import base64
        import io
        import qrcode
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


@app.route("/")
def index():
    ip = get_local_ip()
    return render_template("upload.html", ip=ip, port=5000,
                           qr=_qr_data_url(f"http://{ip}:5000"))


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    safe_name = _safe_upload_name(file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        return jsonify({"error": "Unsupported file type"}), 400

    folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.abspath(os.path.join(folder, safe_name))

    # Belt and braces: the saved path must stay inside the upload folder.
    try:
        if os.path.commonpath([folder, filepath]) != folder:
            return jsonify({"error": "Invalid path"}), 400
    except Exception:
        return jsonify({"error": "Invalid path"}), 400

    file.save(filepath)
    return jsonify({"success": True, "filename": safe_name})


if __name__ == "__main__":
    import socket
    app.run(host="0.0.0.0", port=5000, threaded=True)
