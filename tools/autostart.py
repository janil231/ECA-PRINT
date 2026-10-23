"""Auto-start helper for the ECA Print kiosk.

Running the app from a USB/copy folder is fine for a demo, but a real kiosk
must come back by itself after a brownout or a reboot. This script adds or
removes a shortcut in the current user's Startup folder.

Usage (from the print-vendo folder):
    python tools/autostart.py install     # start the kiosk at login
    python tools/autostart.py remove      # stop starting it at login
    python tools/autostart.py status      # show whether it is installed

It uses the frozen ECAPrint.exe only when it is at least as new as the
source, otherwise it launches "main.py" with pythonw. This prevents a stale
dist/ build from silently running old kiosk code. No admin rights needed,
because it only writes to the current user's Startup folder.
"""
import os
import sys

SHORTCUT_NAME = "ECAPrintKiosk.lnk"
SOURCE_ENTRIES = ("main.py", "config.py", "ui", "core", "wireless")


def _project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _startup_dir():
    return os.path.join(os.environ.get("APPDATA", ""),
                        "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _newest_source_mtime(base):
    newest = 0.0
    for entry in SOURCE_ENTRIES:
        path = os.path.join(base, entry)
        paths = [path]
        if os.path.isdir(path):
            paths = [os.path.join(root, name)
                     for root, dirs, files in os.walk(path)
                     for name in files if name.endswith(".py")]
        for candidate in paths:
            try:
                newest = max(newest, os.path.getmtime(candidate))
            except OSError:
                pass
    return newest


def _target():
    """Return (exe_path, arguments, working_dir) for the shortcut."""
    base = _project_dir()
    exe = None
    for candidate in (
        os.path.join(base, "dist", "ECAPrint.exe"),
        os.path.join(base, "ECAPrint.exe"),
    ):
        if os.path.isfile(candidate):
            exe = candidate
            break
    if exe is not None:
        try:
            if os.path.getmtime(exe) >= _newest_source_mtime(base):
                return exe, "", base
        except OSError:
            pass
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    launcher = pythonw if os.path.isfile(pythonw) else sys.executable
    return launcher, "main.py", base


def install():
    import win32com.client  # from pywin32, already a project dependency
    exe, args, wd = _target()
    path = os.path.join(_startup_dir(), SHORTCUT_NAME)
    shell = win32com.client.Dispatch("WScript.Shell")
    lnk = shell.CreateShortCut(path)
    lnk.TargetPath = exe
    lnk.Arguments = args
    lnk.WorkingDirectory = wd
    lnk.WindowStyle = 7  # minimized console window (app goes fullscreen itself)
    lnk.Save()
    print(f"Installed auto-start: {path}")
    print(f"  -> runs: {exe} {args}".rstrip())


def remove():
    path = os.path.join(_startup_dir(), SHORTCUT_NAME)
    try:
        os.remove(path)
        print(f"Removed auto-start: {path}")
    except FileNotFoundError:
        print("Auto-start was not installed.")
    except Exception as e:
        print(f"Could not remove auto-start: {e}")


def status():
    path = os.path.join(_startup_dir(), SHORTCUT_NAME)
    print("Auto-start installed." if os.path.isfile(path) else "Auto-start NOT installed.")
    exe, args, wd = _target()
    print(f"Would run: {exe} {args}".rstrip())


def main():
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if cmd == "install":
        install()
    elif cmd == "remove":
        remove()
    else:
        status()


if __name__ == "__main__":
    main()
