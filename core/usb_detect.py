import os
import psutil

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.jpg', '.jpeg', '.png'}

class USBDetector:
    def __init__(self):
        self.files = []

    def get_removable_drives(self):
        drives = []
        partitions = psutil.disk_partitions()
        for partition in partitions:
            if partition.opts and 'removable' in str(partition.opts):
                drive_letter = partition.mountpoint
                if drive_letter:
                    drives.append(drive_letter)
        return drives

    def scan_supported_files(self, drives=None):
        self.files = []
        if drives is None:
            drives = self.get_removable_drives()

        for drive in drives:
            try:
                for root, dirs, filenames in os.walk(drive):
                    for filename in filenames:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            self.files.append(os.path.join(root, filename))
            except Exception:
                continue

        # Also scan temp directory
        temp_files = self._scan_folder(os.path.join(os.getcwd(), "temp"))
        self.files.extend(temp_files)

        return self.files

    def _scan_folder(self, folder_path):
        files = []
        if not os.path.exists(folder_path):
            return files
        try:
            for root, dirs, filenames in os.walk(folder_path):
                # Internal cache/output are never customer files.
                dirs[:] = [d for d in dirs if d.lower() not in ("converted", "output")]
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        files.append(os.path.join(root, filename))
        except Exception:
            pass
        return files

    def get_files(self):
        return self.files