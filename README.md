# ECA Print

ECA Print is a Windows print kiosk. A customer adds a file by USB or phone, chooses the paper size and color mode, pays with coins, and prints.

This README explains how to:

1. Build the app into one Windows program.
2. Install it on another computer.
3. Run it, configure it, and fix common problems.

> The computer that runs the kiosk does **not** need Python installed. Python is only needed on the computer used to build the app.

---

## 1. What you need

| Item | Required? | Notes |
| --- | --- | --- |
| Windows 10 or 11, 64-bit | Yes | The app is Windows-only. |
| Microsoft Word | For DOC and DOCX files | PDF, JPG, and PNG files work without Word. |
| Printer and Windows printer driver | For real printing | The app prefers an Epson L120/L121. Otherwise it uses the default physical printer. |
| Coin slot and Arduino | Optional | Use Simulation Mode for demos without coin hardware. |
| Phone and Wi-Fi | For phone upload | The phone and kiosk must be on the same network. |
| Python 3.12 | Only for building | Not needed on the kiosk computer. |

The app ignores virtual printers such as **Microsoft Print to PDF**, **OneNote**, and **XPS**. A real printer must be installed in Windows.

---

## 2. Build the app (one time)

If someone already gave you `ECAPrint.exe`, skip to Part 3.

### Step 1: Install Python 3.12

Download Python 3.12 (64-bit) from <https://www.python.org/downloads/windows/> and install it.

### Step 2: Open PowerShell in the project folder

Open the folder that contains `main.py`, then type `powershell` in the address bar and press Enter. Or open PowerShell and run:

```powershell
cd "C:\Users\janne\OneDrive\Desktop\printease\print-vendo"
```

### Step 3: Install the build tools

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller
```

If `py -3.12` is not found, install Python 3.12 again and make sure it is added to PATH.

### Step 4: Build the exe

```powershell
.\.venv\Scripts\python.exe -m PyInstaller build.spec --noconfirm
```

The result is:

```text
dist\ECAPrint.exe
```

This one file contains Python, the user interface, the phone-upload page, and all libraries. It is usually about 60-70 MB.

### Step 5: Test it

You can run the app from source before building:

```powershell
.\.venv\Scripts\python.exe main.py
```

To test the built exe, double-click `dist\ECAPrint.exe`.

> If you change `config.py` or any other source file, rebuild the exe. The exe contains its own copy of the settings.

---

## 3. Install on another computer

### Step 1: Copy the app

Create a folder the kiosk user can write to, for example:

```text
C:\ECAPrint\
```

Copy `dist\ECAPrint.exe` into that folder.

Do **not** put it in `C:\Program Files` unless you also give the kiosk user write permission there. The app creates `temp\` and `vendo_log.txt` next to the exe.

### Step 2: Install Microsoft Word and the printer

- Install Microsoft Word for DOC and DOCX support.
- Install the printer driver.
- Print a Windows test page to confirm the printer works.

### Step 3: Run the app

Double-click `ECAPrint.exe`.

On first launch, Windows may show a SmartScreen warning because the exe is not code-signed. Click **More info** and then **Run anyway**.

The app opens fullscreen.

### Step 4: Allow phone uploads through the firewall

When Windows asks whether to allow the app through the firewall, allow it on **Private networks**.

If no prompt appears, open PowerShell as Administrator and run:

```powershell
New-NetFirewallRule -DisplayName "ECA Print Phone Upload" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Private
```

### Step 5: Make it start automatically (optional)

1. Right-click `ECAPrint.exe` and choose **Create shortcut**.
2. Press `Win + R`, type `shell:startup`, and press Enter.
3. Move the shortcut into the Startup folder that opens.

The kiosk will start when that Windows user signs in.

The included `tools\autostart.py` helper is for development machines that have Python installed. For a normal kiosk deployment, the Startup shortcut above is simpler.

### Step 6: Lock down Windows (optional)

For a public kiosk, consider:

- A dedicated Windows user for the kiosk.
- Automatic sign-in for that user.
- Windows **Assigned Access** to lock the computer to ECA Print.
- Disabling sleep and automatic updates during business hours.
- A surge protector or small UPS.

Test these settings before leaving the kiosk unattended.

---

## 4. Using the kiosk

1. Choose **Choose USB** or **Scan QR**.
2. Select a file:
   - PDF
   - DOC
   - DOCX
   - JPG / JPEG
   - PNG
3. Choose paper size: **A4**, **Long**, or **Short**.
4. Choose **B&W** or **Color**.
5. Choose the number of copies.
6. Insert coins.
7. Confirm and print.

Default prices:

| Mode | Price per page |
| --- | --- |
| B&W | PHP 2 |
| Color | PHP 4 |

Payment is exact-amount only. The kiosk does not give change.

---

## 5. Staff / admin panel

Open the admin panel in either way:

- Press `Ctrl + Shift + A`.
- Click the **ECA Print** title in the header 5 times quickly.

Default PIN:

```text
1234
```

Change the PIN in `config.py` before building the app.

The admin panel can:

- View today's sales and all-time sales.
- Check printer and coin-slot status.
- Send a test print.
- Turn **Simulation** on or off.
- Clear temporary files.
- Reset customer credit.
- Restart or exit the kiosk.

To stop the kiosk for maintenance, open the admin panel and choose **Exit kiosk**.

---

## 6. Phone upload

1. Connect the phone and the kiosk to the same Wi-Fi network.
2. On the kiosk, choose **Scan QR**.
3. Scan the QR code with the phone.
4. Upload a file.
5. Tap **Continue to files** on the kiosk.

Phone uploads are limited to 50 MB per file.

### If the school Wi-Fi blocks phone-to-computer connections

Many school Wi-Fi networks isolate clients from each other. In that case, use one of these:

- Windows Mobile Hotspot on the kiosk computer.
- A small travel router.
- A separate Wi-Fi network for the kiosk and phones.

ECA Print turns on Windows Mobile Hotspot automatically when it starts. If the hotspot cannot start, it falls back to the normal Wi-Fi network. The kiosk PC must support Windows Mobile Hotspot; if it does not, use a travel router.

The hotspot name and password in `config.py` are shown on the QR screen when the kiosk is running on the hotspot network:

```python
HOTSPOT_SSID = "ECA Print"
HOTSPOT_PASSWORD = "ecaprint123"
```

The first deployment also needs an inbound firewall rule for the upload port. Run this once in an Administrator PowerShell:

```powershell
netsh advfirewall firewall add rule name="ECA Print Phone Upload" dir=in action=allow protocol=TCP localport=5000 remoteip=localsubnet profile=any
```

---

## 7. Settings

All settings are in `config.py`. After changing them, rebuild `ECAPrint.exe`.

| Setting | Default | What it does |
| --- | --- | --- |
| `BW_PRICE_PER_PAGE` | `2` | Price per black-and-white page. |
| `COLOR_PRICE_PER_PAGE` | `4` | Price per color page. |
| `PAPER_SIZE_DEFAULT` | `"a4"` | Default paper size. |
| `ADMIN_PIN` | `"1234"` | Staff panel PIN. Change this before deployment. |
| `SIMULATION_MODE` | `False` | Starts the app without coin or printer hardware. |
| `HOTSPOT_SSID` | `"ECA Print"` | Hotspot name shown on the QR screen. |
| `HOTSPOT_PASSWORD` | `"ecaprint123"` | Hotspot password shown on the QR screen. |
| `LOCK_ESCAPE` | `True` | Prevents Esc from closing the kiosk. |
| `VIEW_RESET_SECONDS` | `60` | Returns to Welcome after inactivity. |
| `CREDIT_EXPIRY_SECONDS` | `300` | Clears unused credit after 5 minutes. |

The **Simulation** button in the admin panel changes the mode at runtime. That change is not saved; after restart the app uses `SIMULATION_MODE` from `config.py` again.

---

## 8. Simulation mode (demo without hardware)

Use Simulation Mode when there is no coin slot or printer.

Turn it on in the admin panel. The header shows **SIMULATION** instead of printer and payment warnings.

In Simulation Mode:

- Press `C` to add PHP 1 of credit.
- Printed pages are saved as PNG files in `temp\output\`.
- No physical printing and no coin hardware are needed.

Turn Simulation Mode off for real payments.

---

## 9. Coin slot hardware (optional)

The coin-slot firmware is in:

```text
arduino\coin_slot\coin_slot.ino
```

The wiring and test guide is in:

```text
arduino\WIRING_GUIDE.md
```

Basic steps:

1. Wire the coin acceptor to the Arduino as described in the guide.
2. Open the sketch in Arduino IDE and upload it.
3. Close the Arduino Serial Monitor.
4. Connect the Arduino to the kiosk by USB.
5. Make sure `SIMULATION_MODE = False` in `config.py`.
6. Start ECA Print. It detects the Arduino automatically at 9600 baud.

Only one program can use the Arduino COM port at a time. Close the Serial Monitor before starting the kiosk.

---

## 10. Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Header says **PRINTER OFFLINE** | No physical printer, or the printer is offline | Install the printer driver, check power and USB, and set it as the Windows default printer. For a demo, turn on Simulation Mode. |
| DOC or DOCX preview or print fails | Microsoft Word is missing or busy | Install Word, close any open Word windows, or upload a PDF instead. |
| DOC or DOCX takes a long time | Word is converting the file to PDF | Wait 10-30 seconds. Large documents can take longer. |
| Phone cannot open the upload page | Phone and kiosk are on different networks, or the firewall blocks port 5000 | Connect the phone to the **ECA Print** hotspot, allow TCP 5000, or use a travel router. |
| App opens and closes immediately | The folder is not writable, or a required library is missing | Put the exe in `C:\ECAPrint\`, and check `temp\app_log.txt` next to the exe. |
| SmartScreen blocks the app | The exe is not code-signed | Click **More info** > **Run anyway**. For public deployment, sign the exe with a code-signing certificate. |
| Coin slot is not detected | Arduino is not connected, the wrong COM port is used, or Serial Monitor is open | Reconnect the Arduino, close Serial Monitor, and check the wiring guide. Use Simulation Mode for a demo. |
| App shows an old name or old version | You are running an old exe | Rebuild with `PyInstaller build.spec --noconfirm` and use `dist\ECAPrint.exe`. |
| Port 5000 is already in use | Another program is using the phone-upload port | Close the other program and restart ECA Print. |

Logs:

- `temp\app_log.txt` - app startup and error log when running the built exe.
- `vendo_log.txt` - sales log.

---

## 11. Updating and uninstalling

### Update

1. Open the admin panel and choose **Exit kiosk**.
2. Replace `ECAPrint.exe` with the new build.
3. Start the app again.

Keep `vendo_log.txt` if you want to keep the sales history. The `temp\` folder can be deleted safely.

### Uninstall

1. Exit the kiosk from the admin panel.
2. Delete the Startup shortcut if you created one.
3. Delete the `C:\ECAPrint\` folder.

The app does not use a Windows installer and does not write registry entries.

---

## 12. Project files

| Path | Purpose |
| --- | --- |
| `main.py` | Main app and screen routing. |
| `config.py` | Prices, PIN, hotspot, simulation, and timing settings. |
| `core/` | Printer, coin reader, Word conversion, file reading, sales log. |
| `ui/` | CustomTkinter screens and branding assets. |
| `wireless/` | Flask phone-upload server and upload page. |
| `arduino/` | Coin-slot firmware and wiring guide. |
| `build.spec` | PyInstaller build recipe. |
| `requirements.txt` | Python packages needed to build/run from source. |
| `tools/` | Auto-start helper and screenshot tool. |
| `dist/ECAPrint.exe` | Built app (created by PyInstaller). |
| `temp/` | Runtime files: uploads, previews, simulation output, logs. |
| `vendo_log.txt` | Sales log. |

---

## 13. Security notes

Before using the kiosk in public:

- Change `ADMIN_PIN` from `1234`.
- Change `HOTSPOT_PASSWORD` from `ecaprint123`.
- Use a trusted Wi-Fi network or a dedicated travel router.
- Remember that the phone-upload page has no login. Anyone on the same network can upload while the kiosk is running.
- Keep Windows and Microsoft Word updated.
- Use a surge protector or UPS.
- For public distribution, consider signing `ECAPrint.exe` so Windows SmartScreen trusts it.
