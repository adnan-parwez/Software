import sys
from PySide6.QtWidgets import QApplication

MART_NAME   = "Printing World"
TAGLINE     = "A Complete Printing Solution"
ADDRESS     = "Balumath, Latehar, Jharkhand 829202"
GSTIN       = "20AAMPZ1694H1ZC"
PHONE       = "+91 9507695751"
LOGO_PATH   = "Icon.png"

BILL_COUNTER_FILE = "bill_counter.json"
SALES_DATA_FILE   = "daily_sales.json"
PURCHASES_FILE    = "purchases.json"
HELD_BILLS_FILE   = "held_bills.json"

C_BG       = "#0f1117"
C_SURFACE  = "#1a1d27"
C_SURFACE2 = "#21263a"
C_BORDER   = "#2d3350"
C_ACCENT   = "#798ef9"
C_GREEN    = "#2e7d32"
C_BLUE     = "#1565c0"
C_ORANGE   = "#e65100"
C_RED      = "#c62828"
C_TEXT     = "#e8eaf6"
C_MUTED    = "#b0b8cc"
C_GOLD     = "#FFD700"
C_SILVER   = "#C0C0C0"
C_BRONZE   = "#CD7F32"

DARK_PALETTE = {
    "C_BG":        "#0f1117",
    "C_SURFACE":   "#1a1d27",
    "C_SURFACE2":  "#21263a",
    "C_BORDER":    "#2d3350",
    "C_TEXT":      "#e8eaf6",
    "C_MUTED":     "#b0b8cc",
    "C_ACCENT":    "#798ef9",
    "C_ACCENT_DK": "#5a49d0",
    "C_ACCENT_LT": "#9fa8ff",
    "C_GREEN":     "#2e7d32",
    "C_GREEN_LT":  "#00c896",
    "C_GREEN_DK":  "#009e76",
    "C_BLUE":      "#1565c0",
    "C_BLUE_LT":   "#4fc3f7",
    "C_BLUE_DK":   "#0288d1",
    "C_ORANGE":    "#e65100",
    "C_ORANGE_LT": "#ff8a65",
    "C_ORANGE_DK": "#e64a19",
    "C_RED":       "#c62828",
    "C_RED_LT":    "#ef5350",
    "C_RED_DK":    "#b71c1c",
    "C_PURPLE_LT": "#ce93d8",
    "C_PURPLE_DK": "#8e24aa",
    "C_GOLD":      "#FFD700",
    "C_SILVER":    "#C0C0C0",
    "C_BRONZE":    "#CD7F32",
    "C_WA":        "#25D366",
    "C_WA_DK":     "#128C7E",
    "C_BAR_BG":    "#0a0a0f",
    "C_BAR_LINE":  "#7c6aff",
    "C_BTN_PRI":   "#7c6aff",
    "C_BTN_PRI_DK":"#5a49d0",
    "C_STATUS_1":  "#3d2f99",
    "C_STATUS_2":  "#7c6aff",
    "C_CALC_BTN":  "#3d3d5c",
    "C_CALC_HOV":  "#5a58ef",
    "C_CALC_PRS":  "#3d2f99",
    "C_RECEIPT_BG":"#fffde7",
    "C_RECEIPT_TX":"#111111",
    "C_POSITIVE":  "#69f0ae",
    "C_TOTAL_BLUE":"#90caf9",
    "C_WARN":      "#ffd54f",
    "C_DIAMOND":   "#b9f2ff",
    "C_PLATINUM":  "#e5e4e2",
}

LIGHT_PALETTE = {
    "C_BG":        "#f4f5fa",
    "C_SURFACE":   "#ffffff",
    "C_SURFACE2":  "#eef0f7",
    "C_BORDER":    "#d4d8e3",
    "C_TEXT":      "#161925",
    "C_MUTED":     "#5a6075",
    "C_ACCENT":    "#49d0ba",
    "C_ACCENT_DK": "#36b89e",
    "C_ACCENT_LT": "#6affe9",
    "C_GREEN":     "#2e7d32",
    "C_GREEN_LT":  "#00c896",
    "C_GREEN_DK":  "#009e76",
    "C_BLUE":      "#1565c0",
    "C_BLUE_LT":   "#0288d1",
    "C_BLUE_DK":   "#01579b",
    "C_ORANGE":    "#e65100",
    "C_ORANGE_LT": "#e64a19",
    "C_ORANGE_DK": "#bf360c",
    "C_RED":       "#c62828",
    "C_RED_LT":    "#d32f2f",
    "C_RED_DK":    "#b71c1c",
    "C_PURPLE_LT": "#8e24aa",
    "C_PURPLE_DK": "#6a1b9a",
    "C_GOLD":      "#b8860b",
    "C_SILVER":    "#808080",
    "C_BRONZE":    "#8b4513",
    "C_WA":        "#128C7E",
    "C_WA_DK":     "#075e54",
    "C_BAR_BG":    "#ffffff",
    "C_BAR_LINE":  "#5a49d0",
    "C_BTN_PRI":   "#5a49d0",
    "C_BTN_PRI_DK":"#4536b8",
    "C_STATUS_1":  "#4536b8",
    "C_STATUS_2":  "#5a49d0",
    "C_CALC_BTN":  "#eef0f7",
    "C_CALC_HOV":  "#d4d8e3",
    "C_CALC_PRS":  "#c5c8d6",
    "C_RECEIPT_BG":"#ffffff",
    "C_RECEIPT_TX":"#111111",
    "C_POSITIVE":  "#2e7d32",
    "C_TOTAL_BLUE":"#1565c0",
    "C_WARN":      "#e08e00",
    "C_DIAMOND":   "#0288d1",
    "C_PLATINUM":  "#616161",
}

CURRENT_THEME = "dark"

_p = DARK_PALETTE
C_BG       = _p["C_BG"]
C_SURFACE  = _p["C_SURFACE"]
C_SURFACE2 = _p["C_SURFACE2"]
C_BORDER   = _p["C_BORDER"]
C_ACCENT   = _p["C_ACCENT"]
C_GREEN    = _p["C_GREEN"]
C_BLUE     = _p["C_BLUE"]
C_ORANGE   = _p["C_ORANGE"]
C_RED      = _p["C_RED"]
C_TEXT     = _p["C_TEXT"]
C_MUTED    = _p["C_MUTED"]
C_GOLD     = _p["C_GOLD"]
C_SILVER   = _p["C_SILVER"]
C_BRONZE   = _p["C_BRONZE"]

RED_CLOSE_SS = (
    "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);"
    " border:none; border-radius:7px; color:white; font-weight:700; padding:0 16px; }"
    " QPushButton:hover { background:#b71c1c; }"
)

def build_stylesheet():
    return f"""
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}
QFrame#surface {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
}}
QLabel#heading {{
    font-size: 20px;
    font-weight: 700;
    color: {C_TEXT};
}}
QLabel#subheading {{
    font-size: 13px;
    color: {C_MUTED};
}}
QLabel#martName {{
    font-size: 26px;
    font-weight: 800;
    color: {C_TEXT};
    letter-spacing: 2px;
}}
QLabel#tagline {{
    font-size: 11px;
    color: {C_MUTED};
}}
QLabel#clock {{
    font-size: 18px;
    font-weight: 700;
    color: {C_TEXT};
    font-family: 'Consolas', monospace;
}}
QLabel#billNo {{
    font-size: 12px;
    color: {C_MUTED};
}}
QLineEdit {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    color: {C_TEXT};
    font-size: 13px;
}}
QLineEdit:focus {{
    border: 1px solid {C_ACCENT};
}}
QLineEdit::placeholder {{
    color: {C_MUTED};
}}
QPushButton {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {C_TEXT};
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background: {C_SURFACE};
    border-color: {C_ACCENT};
}}
QPushButton:pressed {{
    background: {C_ACCENT};
    color: white;
}}
QPushButton#accentBtn {{
    background: {C_ACCENT};
    border: none;
    color: white;
    font-weight: 700;
    font-size: 14px;
    border-radius: 9px;
}}
QPushButton#accentBtn:hover {{
    background: #6a59e0;
}}
QPushButton#accentBtn:pressed {{
    background: #5a49d0;
}}
QPushButton#greenBtn {{
    background: {C_GREEN};
    border: none;
    color: white;
    font-weight: 700;
    border-radius: 8px;
}}
QPushButton#greenBtn:hover {{ background: #1b5e20; }}
QPushButton#redBtn {{
    background: {C_RED};
    border: none;
    color: white;
    font-weight: 700;
    border-radius: 8px;
}}
QPushButton#redBtn:hover {{ background: #b71c1c; }}
QPushButton#orangeBtn {{
    background: {C_ORANGE};
    border: none;
    color: white;
    font-weight: 700;
    border-radius: 8px;
}}
QPushButton#orangeBtn:hover {{ background: #bf360c; }}
QPushButton#payBtn {{
    background: {C_SURFACE2};
    border: 2px solid {C_BORDER};
    border-radius: 8px;
    color: {C_TEXT};
    font-weight: 700;
    font-size: 13px;
    min-height: 40px;
}}
QPushButton#payBtn:checked {{
    border-color: {C_ACCENT};
    background: rgba(124, 106, 255, 0.18);
    color: #a99fff;
}}
QTableWidget {{
    background: {C_SURFACE};
    border: none;
    gridline-color: {C_BORDER};
    alternate-background-color: {C_SURFACE2};
    selection-background-color: rgba(124,106,255,0.25);
    selection-color: {C_TEXT};
    border-radius: 6px;
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QHeaderView::section {{
    background: {C_SURFACE2};
    color: {C_MUTED};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    padding: 6px 8px;
    text-transform: uppercase;
}}
QTabWidget::pane {{
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    background: {C_SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background: {C_SURFACE2};
    color: {C_MUTED};
    border: 1px solid {C_BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
    margin-right: 2px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {C_SURFACE};
    color: {C_TEXT};
    border-bottom: 1px solid {C_SURFACE};
}}
QTabBar::tab:hover:!selected {{
    color: {C_TEXT};
}}
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: {C_BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QComboBox {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 7px;
    padding: 5px 10px;
    color: {C_TEXT};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_ACCENT};
}}
QStatusBar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3d2f99,stop:1 #7c6aff);
    color: white;
    font-size: 12px;
    font-weight: 700;
    border-top: 1px solid {C_ACCENT};
    min-height: 28px;
    padding: 4px 8px;
}}
QGroupBox {{
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 6px;
}}
QGroupBox::title {{
    color: {C_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    subcontrol-origin: margin;
    left: 12px;
}}
QTextEdit {{
    background: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    color: {C_TEXT};
    font-family: 'Courier New', monospace;
    font-size: 12px;
}}
QListWidget {{
    background: {C_SURFACE2};
    border: none;
    color: {C_TEXT};
    font-size: 13px;
}}
QListWidget::item {{
    padding: 7px 12px;
    border-radius: 5px;
}}
QListWidget::item:selected {{
    background: {C_ACCENT};
    color: white;
}}
QListWidget::item:hover {{
    background: rgba(124,106,255,0.3);
}}
"""
STYLESHEET = build_stylesheet()

def apply_theme(theme):
    global CURRENT_THEME, STYLESHEET
    global C_BG, C_SURFACE, C_SURFACE2, C_BORDER, C_ACCENT
    global C_GREEN, C_BLUE, C_ORANGE, C_RED
    global C_TEXT, C_MUTED, C_GOLD, C_SILVER, C_BRONZE

    CURRENT_THEME = theme
    p = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE

    C_BG       = p["C_BG"]
    C_SURFACE  = p["C_SURFACE"]
    C_SURFACE2 = p["C_SURFACE2"]
    C_BORDER   = p["C_BORDER"]
    C_ACCENT   = p["C_ACCENT"]
    C_GREEN    = p["C_GREEN"]
    C_BLUE     = p["C_BLUE"]
    C_ORANGE   = p["C_ORANGE"]
    C_RED      = p["C_RED"]
    C_TEXT     = p["C_TEXT"]
    C_MUTED    = p["C_MUTED"]
    C_GOLD     = p["C_GOLD"]
    C_SILVER   = p["C_SILVER"]
    C_BRONZE   = p["C_BRONZE"]

    STYLESHEET = build_stylesheet()
    QApplication.instance().setStyleSheet(STYLESHEET)

    for w in QApplication.topLevelWidgets():
        w.setStyleSheet(STYLESHEET)
    QApplication.instance().setStyleSheet(STYLESHEET)