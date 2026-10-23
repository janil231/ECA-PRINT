# config.py - ECA Print Kiosk Configuration (iOS Pro Light Theme, Full HD)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Pricing
BW_PRICE_PER_PAGE = 2
COLOR_PRICE_PER_PAGE = 4

# Paper sizes for printing (Philippine bond sizes + A4)
# win_code = Windows DMPAPER_* constant (9=A4, 14=Folio/Long, 1=Letter/Short)
PAPER_SIZES = {
    "a4":    {"label": "A4",    "width_mm": 210, "height_mm": 297, "win_code": 9},
    "long":  {"label": "Long",  "width_mm": 216, "height_mm": 330, "win_code": 14},
    "short": {"label": "Short", "width_mm": 216, "height_mm": 279, "win_code": 1},
}
PAPER_SIZE_DEFAULT = "a4"

# Serial communication
BAUD_RATE = 9600

# File paths
LOG_FILE = "vendo_log.txt"
TEMP_DIR = "temp"
OUTPUT_DIR = "temp/output"

# Simulation
SIMULATION_MODE = False
ADD_CREDIT_KEY = "c"

# Kiosk behaviour
CREDIT_EXPIRY_SECONDS = 300     # idle credit is cleared after 5 minutes
VIEW_RESET_SECONDS = 60         # return to welcome after 1 minute with no activity
QR_RESET_SECONDS = 300          # QR screen stays up longer while the phone uploads
ADMIN_RESET_SECONDS = 300       # lock an unattended staff panel after 5 minutes
LOCK_ESCAPE = True              # Esc no longer exits the kiosk (staff use the admin PIN)
ADMIN_PIN = "1234"              # staff PIN for the admin panel - change this!
PRINTER_STATUS_POLL = 20        # seconds between printer paper/ink checks
VIEW_TRANSITION_MS = 280        # fade duration between screens

# Phone upload hotspot (used when the venue Wi-Fi isolates clients)
HOTSPOT_SSID = "ECA Print"
HOTSPOT_PASSWORD = "ecaprint123"

# iOS Pro light theme palette (Full HD touch monitor)
APP_BG = "#F2F2F7"            # iOS grouped background
CARD_BG = "#FFFFFF"           # pure white cards
PRIMARY_TEXT = "#111827"      # almost black titles
SECONDARY_TEXT = "#6B7280"    # medium gray subtitles
TERTIARY_TEXT = "#8E8E93"     # iOS secondary gray
PRIMARY_BLUE = "#007AFF"      # iPhone blue
PRIMARY_BLUE_HOVER = "#0063D1"
SUCCESS_GREEN = "#34C759"     # iOS green
SUCCESS_DARK = "#248A3D"
WARNING_RED = "#FF3B30"       # iOS red
WARNING_RED_HOVER = "#E03228"
BORDER_GRAY = "#E5E5EA"       # iOS separator
CARD_BORDER = "#E5E7EB"
AMBER_TEXT = "#B45309"
AMBER_BG = "#FEF3C7"
LIGHT_BLUE_BG = "#EAF2FF"
LIGHT_BLUE_HOVER = "#D8E8FF"
PILL_GRAY = "#E9E9EE"
PILL_GRAY_HOVER = "#D9D9DE"
UI_FONT = "Segoe UI"

# Shape language
CARD_RADIUS = 20
BTN_RADIUS = 16
PILL_RADIUS = 22

# ---------------------------------------------------------------------------
# Design system tokens - single source of truth for scale.
# Use these instead of ad-hoc font sizes / paddings in the views.
# ---------------------------------------------------------------------------

# Spacing scale (px)
SPACE_XXS = 4
SPACE_XS = 6
SPACE_SM = 10
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32
SPACE_2XL = 48

# Typography scale (family, size, weight)
# Note: Tkinter may not recognize 'regular' weight on all systems;
# weight is omitted by default and defaults to normal.
FONT_HERO = (UI_FONT, 42, "bold")     # screen titles (welcome, printing)
FONT_H1 = (UI_FONT, 32, "bold")       # page headings
FONT_H2 = (UI_FONT, 24, "bold")       # card headings
FONT_TITLE = (UI_FONT, 19, "bold")    # row / item titles
FONT_BODY = (UI_FONT, 16,)              # body copy
FONT_SMALL = (UI_FONT, 14,)             # secondary copy
FONT_TINY = (UI_FONT, 12,)              # caption / metadata
FONT_LABEL = (UI_FONT, 13, "bold")    # uppercase section labels
FONT_BUTTON = (UI_FONT, 18, "bold")   # standard button label
FONT_AMOUNT = (UI_FONT, 48, "bold")   # large price display
FONT_AMOUNT_SM = (UI_FONT, 36, "bold") # medium price display

# Color palette - iOS Pro Light, accessible, contrast-checked
# All colors are #RRGGBB format
COLOR_APP_BG = "#F2F2F7"              # main background
COLOR_CARD_BG = "#FFFFFF"              # card surfaces
COLOR_PRIMARY_TEXT = "#111827"         # primary text (near-black)
COLOR_SECONDARY_TEXT = "#6B7280"       # secondary text (medium gray)
COLOR_TERTIARY_TEXT = "#8E8E93"       # tertiary text (light gray)
COLOR_PRIMARY_BLUE = "#007AFF"        # primary action blue
COLOR_PRIMARY_BLUE_HOVER = "#0063D1"  # blue on hover
COLOR_SUCCESS_GREEN = "#34C759"       # success / OK green
COLOR_SUCCESS_DARK = "#248A3D"        # success dark state
COLOR_WARNING_RED = "#FF3B30"         # error / warning red
COLOR_WARNING_RED_HOVER = "#E03228"   # red on hover
COLOR_BORDER_GRAY = "#E5E5EA"         # dividers / borders
COLOR_CARD_BORDER = "#E5E7EB"         # card border
COLOR_AMBER_TEXT = "#B45309"          # amber warning text
COLOR_AMBER_BG = "#FEF3C7"            # amber background (info)
COLOR_LIGHT_BLUE_BG = "#EAF2FF"       # light blue background
COLOR_LIGHT_BLUE_HOVER = "#D8E8FF"    # light blue on hover
COLOR_PILL_GRAY = "#E9E9EE"           # pill-shaped backgrounds
COLOR_PILL_GRAY_HOVER = "#D9D9DE"     # pill on hover
COLOR_WHITE = "#FFFFFF"               # pure white

# Shape language - consistent border radii
CARD_RADIUS = 20
BTN_RADIUS = 16
PILL_RADIUS = 22

# ---------------------------------------------------------------------------
# Component visual states
# ---------------------------------------------------------------------------

# Button states
BTN_IDLE = "#FFFFFF"       # default button bg
BTN_HOVER = "#F2F2F7"      # hover state (subtle)
BTN_ACTIVE = "#E5E7EB"     # pressed state

# Pill states
PILL_IDLE = "#E9E9EE"
PILL_HOVER = "#D9D9DE"
PILL_PAID = "#FFFFFF"       # when payment is complete

# Progress bar
PROG_BG = "#E5E5EA"
PROG_FG = "#007AFF"        # progress fill color
PROG_HOVER = "#D8E8FF"
