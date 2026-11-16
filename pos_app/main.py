import sys
import json
import csv
import os
import hashlib
import calendar
import tempfile
from datetime import datetime, date
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTabWidget,
    QComboBox, QMessageBox, QFileDialog, QTextEdit, QAbstractItemView,
    QSizePolicy, QGroupBox, QDoubleSpinBox, QSpinBox, QCheckBox,
    QStackedWidget, QButtonGroup, QRadioButton, QFormLayout, QStatusBar,
    QToolButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import (
    Qt, QTimer, QDateTime, Signal, QSize, QThread, QPropertyAnimation,
    QEasingCurve, QPoint, QRect
)
from PySide6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QBrush, QPen,
    QLinearGradient, QShortcut, QKeySequence, QFontMetrics, QCursor
)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    from PIL import Image as PILImage
    PIL_OK = True
except ImportError:
    PIL_OK = False

from config import *
from data_manager import *
from auth import UserManager
from login_window import LoginWindow
from dialogs import CustomerDialog, BillPreviewDialog, HeldBillsDialog

class POSWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.user_manager = UserManager()

        self.products = load_products()
        self.customers = load_customers()
        self.cart_items = []
        self._cart_updating = False
        self.current_bill_no = get_next_bill_number()

        self.setWindowTitle("Billing System")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumSize(1024, 600)

        self._build_ui()
        self._setup_shortcuts()
        self._tick()

    # ──────────────────────────────────────────────────────────────────
    #  UI BUILD
    # ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_l = QVBoxLayout(central)
        main_l.setContentsMargins(0, 0, 0, 0)
        main_l.setSpacing(0)

        main_l.addWidget(self._build_header())
        main_l.addWidget(self._build_menu_bar())

        body = QWidget()
        body_l = QHBoxLayout(body)
        body_l.setContentsMargins(8, 8, 8, 8)
        body_l.setSpacing(8)

        left = self._build_left_panel()
        right = self._build_right_panel()

        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        body_l.addWidget(left, 1)
        body_l.addWidget(right, 0)

        main_l.addWidget(body, 1)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("READY — Scan/type item code  |  F1: Focus cart  |  Ctrl+P: Print  |  Ctrl+V: Preview")
        self.setStatusBar(self.status_bar)

    def _build_header(self):
        header = QFrame()
        header.setMaximumHeight(72)
        header.setMinimumHeight(56)
        header.setStyleSheet(f"background:{C_SURFACE}; border-bottom:1px solid {C_BORDER};")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        bill_w = QWidget()
        bill_w.setStyleSheet("background:transparent;border:none;")
        bill_l = QVBoxLayout(bill_w)
        bill_l.setContentsMargins(0,0,0,0)
        bill_l.setSpacing(2)
        self.bill_lbl = QLabel(f"BILL # {self.current_bill_no}")
        self.bill_lbl.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:800;background:transparent;border:none;")
        bill_l.addWidget(self.bill_lbl)
        self.user_lbl = QLabel(f"👤 {self.current_user['name']}")
        self.user_lbl.setStyleSheet(f"color:{C_MUTED};font-size:11px;background:transparent;border:none;")
        self.user_lbl.setVisible(False)
        bill_l.addWidget(self.user_lbl)
        hl.addWidget(bill_w)

        hl.addStretch()

        center_w = QWidget()
        center_l = QHBoxLayout(center_w)
        center_l.setContentsMargins(0,0,0,0)
        center_l.setSpacing(10)
        center_l.setAlignment(Qt.AlignCenter)

        try:
            logo_lbl = QLabel()
            logo_lbl.setStyleSheet("border:none;background:transparent;")
            raw_pix = QPixmap(LOGO_PATH)
            if not raw_pix.isNull():
                display_pix = raw_pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_lbl.setPixmap(display_pix)
                logo_lbl.setFixedSize(64, 64)
                logo_lbl.setAlignment(Qt.AlignCenter)
            center_l.addWidget(logo_lbl)
        except Exception:
            pass

        title_col = QWidget()
        title_col.setStyleSheet("background:transparent;border:none;")
        tc_l = QVBoxLayout(title_col)
        tc_l.setContentsMargins(0,0,0,0)
        tc_l.setSpacing(0)
        tc_l.setAlignment(Qt.AlignCenter)

        mart_lbl = QLabel(MART_NAME.upper())
        mart_lbl.setObjectName("martName")
        mart_lbl.setAlignment(Qt.AlignCenter)
        mart_lbl.setStyleSheet(f"font-size:26px;font-weight:800;color:{C_TEXT};letter-spacing:2px;background:transparent;border:none;")
        tc_l.addWidget(mart_lbl)

        tag_lbl = QLabel(TAGLINE)
        tag_lbl.setObjectName("tagline")
        tag_lbl.setAlignment(Qt.AlignCenter)
        tag_lbl.setStyleSheet(f"font-size:11px;color:{C_MUTED};background:transparent;border:none;")
        tc_l.addWidget(tag_lbl)

        center_l.addWidget(title_col)
        hl.addWidget(center_w)

        hl.addStretch()

        self.clock_lbl = QLabel()
        self.clock_lbl.setObjectName("clock")
        self.clock_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(self.clock_lbl)

        return header

    def _build_menu_bar(self):
        bar = QFrame()
        bar.setMaximumHeight(52)
        bar.setMinimumHeight(46)
        bar.setStyleSheet(f"background: {C_SURFACE}; border-bottom: 2px solid {C_ACCENT};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 6, 8, 6)
        bl.setSpacing(4)

        self.menu_btn = QPushButton("☰  Menu  ▾")
        self.menu_btn.setFixedHeight(38)
        self.menu_btn.setFocusPolicy(Qt.StrongFocus)
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE};
                border: 2px solid {C_BORDER};
                color: {C_TEXT}; font-weight: 700; font-size: 12px;
                padding: 0 14px; border-radius: 8px;
            }}
            QPushButton:hover  {{ border: 2px solid {C_ACCENT}; }}
            QPushButton:pressed {{ background:{C_SURFACE2}; }}
            QPushButton:focus  {{ border: 2px solid {C_ACCENT}; outline:none; }}
        """)
        self.menu_btn.clicked.connect(self._show_menu_dropdown)
        self.menu_btn.installEventFilter(self)
        bl.addWidget(self.menu_btn)

        taskbar_items = [
            ("📦 Inventory",  self._manage_products),
            ("📊 Reports",    self._show_reports),
            ("💸 Expenses",   self._expense_tracker),
            ("⏸ Held Bills",  self._show_held_bills),
        ]

        self._taskbar_buttons = []
        for text, fn in taskbar_items:
            btn = QPushButton(text)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(130)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                    border: 2px solid #5a49d0;
                    color: white; font-weight: 700; font-size: 12px;
                    padding: 0 18px; border-radius: 8px;
                }}
                QPushButton:hover  {{ border: 2px solid white; background:#6a58ef; }}
                QPushButton:pressed {{ background:#4a38d0; border:3px solid white; }}
                QPushButton:focus  {{ border: 3px solid white; outline:none; }}
            """)
            btn.clicked.connect(fn)
            btn.installEventFilter(self)
            bl.addWidget(btn)
            self._taskbar_buttons.append(btn)

        bl.addStretch()

        self.admin_btn = QPushButton(f"⚙  {self.current_user['name']}  ▾")
        self.admin_btn.setFixedHeight(38)
        self.admin_btn.setFocusPolicy(Qt.StrongFocus)
        self.admin_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE};
                border: 2px solid {C_BORDER};
                color: {C_TEXT}; font-weight: 700; font-size: 12px;
                padding: 0 14px; border-radius: 8px;
            }}
            QPushButton:hover  {{ border: 2px solid {C_ACCENT}; }}
            QPushButton:pressed {{ background:{C_SURFACE2}; }}
            QPushButton:focus  {{ border: 2px solid {C_ACCENT}; outline:none; }}
        """)
        self.admin_btn.clicked.connect(self._admin_menu)
        self.admin_btn.installEventFilter(self)
        bl.addWidget(self.admin_btn)

        self.theme_btn = QPushButton("☀️  Light" if CURRENT_THEME == "dark" else "🌙  Dark")
        self.theme_btn.setFixedHeight(38)
        self.theme_btn.setMinimumWidth(90)
        self.theme_btn.setFocusPolicy(Qt.StrongFocus)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE};
                border: 2px solid {C_BORDER};
                color: {C_TEXT}; font-weight: 700; font-size: 12px;
                padding: 0 12px; border-radius: 8px;
            }}
            QPushButton:hover  {{ border: 2px solid {C_ACCENT}; }}
            QPushButton:pressed {{ background:{C_SURFACE2}; }}
            QPushButton:focus  {{ border: 2px solid {C_ACCENT}; outline:none; }}
        """)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.installEventFilter(self)
        bl.addWidget(self.theme_btn)

        return bar

    def _show_menu_dropdown(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C_SURFACE2}; 
                border: 2px solid {C_ACCENT};
                border-radius: 8px;
                padding: 4px;
                color: {C_TEXT};
                font-size: 13px;
                font-weight: 600;
            }}
            QMenu::item {{ padding: 9px 22px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {C_ACCENT}; color: white; }}
            QMenu::separator {{ height:1px; background:{C_BORDER}; margin:4px 8px; }}
        """)
        menu.addAction("🏠 Dashboard",      self._show_dashboard)
        menu.addSeparator()
        menu.addAction("💳 Dues",            self._manage_dues)
        menu.addAction("🛒 Purchases",       self._manage_purchases)
        menu.addAction("👤 Customers",       self._manage_customers)
        menu.addSeparator()
        menu.addAction("📢 Send Offer to All Customers", self._send_offer_all_dialog)
        pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        menu.exec(pos)

    def _toggle_theme(self):
        new_theme = "light" if CURRENT_THEME == "dark" else "dark"
        
        apply_theme(new_theme)
        
        saved_cart = list(self.cart_items)
        saved_name = self.cust_name.text()
        saved_phone = self.cust_phone.text()
        saved_disc = self.extra_disc_edit.text()

        old_central = self.centralWidget()
        self.setCentralWidget(None)
        if old_central is not None:
            old_central.deleteLater()

        self._build_ui()
        self._setup_shortcuts()

        self.cart_items = saved_cart
        self.cust_name.setText(saved_name)
        self.cust_phone.setText(saved_phone)
        self.extra_disc_edit.setText(saved_disc)
        
        self._rebuild_cart()
        self._update_totals()
        
        self.theme_btn.setText("☀️  Light" if new_theme == "dark" else "🌙  Dark")
        self.status_bar.showMessage(f"Theme: {new_theme.title()}")

    def _build_left_panel(self):
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0,0,0,0)
        ll.setSpacing(6)

        cust_frame = QFrame()
        cust_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;")
        cust_frame.setFixedHeight(65)
        cl = QHBoxLayout(cust_frame)
        cl.setContentsMargins(12, 6, 12, 6)
        cl.setSpacing(10)

        lbl_cu = QLabel("👤")
        lbl_cu.setStyleSheet(f"color:{C_ACCENT};font-size:18px;background:transparent;border:none;")
        cl.addWidget(lbl_cu)

        self.cust_name = QLineEdit()
        self.cust_name.setPlaceholderText("Customer name")
        self.cust_name.setFixedHeight(45)
        self.cust_name.setMinimumWidth(160) 
        cl.addWidget(self.cust_name)

        lbl_ph = QLabel("📞")
        lbl_ph.setStyleSheet(f"color:#e91e63;font-size:17px;background:transparent;border:none;")
        cl.addWidget(lbl_ph)

        self.cust_phone = QLineEdit()
        self.cust_phone.setPlaceholderText("Phone number")
        self.cust_phone.setFixedHeight(45)
        self.cust_phone.setMaximumWidth(150)
        self.cust_phone.textChanged.connect(self._phone_autofill)
        cl.addWidget(self.cust_phone)

        self.pts_lbl = QLabel("⭐ —")
        self.pts_lbl.setStyleSheet(f"color:{C_GOLD};font-weight:700;font-size:13px;background:transparent;border:none;")
        cl.addWidget(self.pts_lbl)

        cl.addStretch()

        disc_lbl = QLabel("Extra Disc:")
        disc_lbl.setStyleSheet(f"color:{C_MUTED};font-size:12px;background:transparent;border:none;")
        cl.addWidget(disc_lbl)

        self.extra_disc_edit = QLineEdit()
        self.extra_disc_edit.setPlaceholderText("₹0")
        self.extra_disc_edit.setFixedWidth(65)
        self.extra_disc_edit.setFixedHeight(30)
        self.extra_disc_edit.setToolTip("Additional ₹ discount on Grand Total")
        self.extra_disc_edit.textChanged.connect(self._update_totals)
        cl.addWidget(self.extra_disc_edit)

        rs_lbl = QLabel("₹")
        rs_lbl.setStyleSheet(f"color:{C_MUTED};background:transparent;border:none;")
        cl.addWidget(rs_lbl)

        ll.addWidget(cust_frame)

        self.cart_table = QTableWidget(0, 8)
        self.cart_table.setHorizontalHeaderLabels(["ITEM NAME", "MRP", "PRICE", "DISC", "QTY", "TOTAL", "CODE", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(1, 90)
        self.cart_table.setColumnWidth(2, 90)
        self.cart_table.setColumnWidth(3, 80)
        self.cart_table.setColumnWidth(4, 65)
        self.cart_table.setColumnWidth(5, 90)
        self.cart_table.setColumnWidth(6, 0)
        self.cart_table.setColumnHidden(6, True)
        self.cart_table.setColumnWidth(7, 65)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setMinimumHeight(200)
        self.cart_table.setStyleSheet(f"""
            QTableWidget {{
                background: {C_SURFACE};
                border: none;
                gridline-color: {C_BORDER};
                alternate-background-color: {C_SURFACE2};
                selection-background-color: rgba(124,106,255,0.25);
                selection-color: {C_TEXT};
                border-radius: 6px;
            }}
            QTableWidget::item {{ padding: 4px 8px; border: none; font-size: 14px;}}
            QHeaderView::section {{
                background: {C_SURFACE2};
                color: {C_TEXT};
                font-weight: 800;
                font-size: 14px;
                letter-spacing: 1px;
                border: none;
                border-bottom: 2px solid {C_ACCENT};
                padding: 6px 8px;
                text-transform: uppercase;
            }}
        """)
        self.cart_table.itemChanged.connect(self._on_cart_item_changed)
        ll.addWidget(self.cart_table, 1)

        input_frame = QFrame()
        input_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;")
        input_frame.setFixedHeight(50)
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(10, 6, 10, 6)
        il.setSpacing(6)

        self.item_entry   = QLineEdit(); self.item_entry.setPlaceholderText("Scan / Type item code or name")
        self.mrp_entry    = QLineEdit(); self.mrp_entry.setPlaceholderText("MRP")
        self.price_entry  = QLineEdit(); self.price_entry.setPlaceholderText("Price")
        self.qty_entry    = QLineEdit(); self.qty_entry.setPlaceholderText("Qty"); self.qty_entry.setText("1")
        self.qty_entry.focusInEvent = lambda e: (QTimer.singleShot(0, self.qty_entry.selectAll), type(self.qty_entry).focusInEvent(self.qty_entry, e))
        self.disc_show    = QLabel(""); self.disc_show.setStyleSheet(f"color:#69f0ae;font-weight:700;min-width:60px;background:transparent;border:none;")

        self._setup_item_completer()

        self._barcode_timer = QTimer(self)
        self._barcode_timer.setSingleShot(True)
        self._barcode_timer.timeout.connect(self._try_barcode_auto_add)
        self.item_entry.textChanged.connect(self._on_barcode_input)

        for w, mw in [(self.item_entry, 380),(self.mrp_entry,75),(self.price_entry,75),(self.disc_show,55),(self.qty_entry,55)]:
            if isinstance(w, QLineEdit):
                w.setFixedHeight(36)
                if mw: w.setMaximumWidth(mw)
            il.addWidget(w)

        add_row_btn = QPushButton("✚  Add to Cart")
        add_row_btn.setFixedHeight(36)
        add_row_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                border: 2px solid transparent;
                border-radius: 8px; color: white; font-weight: 800; font-size: 13px;
            }}
            QPushButton:hover  {{ border: 2px solid white; background:#6a58ef; }}
            QPushButton:pressed {{ background:#4a38d0; border:2px solid white; }}
            QPushButton:focus  {{ border: 2px solid white; outline:none; }}
        """)
        add_row_btn.clicked.connect(self._add_item)
        il.addWidget(add_row_btn)

        ll.addWidget(input_frame)

        total_frame = QFrame()
        total_frame.setFixedHeight(50)
        total_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;")
        tl = QHBoxLayout(total_frame)
        tl.setContentsMargins(16, 0, 16, 0)

        self.items_count_lbl = QLabel("Items: 0")
        self.items_count_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:700;background:transparent;border:none;")
        tl.addWidget(self.items_count_lbl)

        tl.addStretch()

        self.subtotal_lbl = QLabel("Subtotal: ₹0")
        self.subtotal_lbl.setStyleSheet(f"color:{C_TEXT};font-size:12px;font-weight:700;background:transparent;border:none;")
        tl.addWidget(self.subtotal_lbl)

        sep1 = QLabel(" | ")
        sep1.setStyleSheet(f"color:{C_BORDER};background:transparent;border:none;")
        tl.addWidget(sep1)

        self.discount_lbl = QLabel("Discount: ₹0")
        self.discount_lbl.setStyleSheet(f"color:#69f0ae;font-size:12px;background:transparent;border:none;")
        tl.addWidget(self.discount_lbl)

        sep2 = QLabel(" | ")
        sep2.setStyleSheet(f"color:{C_BORDER};background:transparent;border:none;")
        tl.addWidget(sep2)

        self.grand_total_lbl = QLabel("GRAND TOTAL: ₹0")
        self.grand_total_lbl.setStyleSheet(f"color:{C_TEXT};font-size:18px;font-weight:800;background:transparent;border:none;")
        tl.addWidget(self.grand_total_lbl)

        ll.addWidget(total_frame)

        pay_frame = QFrame()
        pay_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:8px;")
        pay_frame.setMaximumHeight(120)
        pay_frame.setMinimumHeight(80)
        pl = QVBoxLayout(pay_frame)
        pl.setContentsMargins(12, 6, 12, 6)
        pl.setSpacing(4)

        row1 = QHBoxLayout()
        pay_lbl = QLabel("PAYMENT:")
        pay_lbl.setStyleSheet(f"color:{C_TEXT};font-size:11px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        row1.addWidget(pay_lbl)

        self.pay_group = QButtonGroup(self)
        self.pay_buttons = {}
        pay_options = [
            ("💰 CASH", "CASH"),
            ("📱 UPI",  "UPI"),
            ("💳 CARD", "CARD"),
            ("🔴 DUE",  "DUE"),
        ]
        for i, (label, val) in enumerate(pay_options):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(88)
            btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C_SURFACE2};
                    border: 2px solid {C_BORDER};
                    border-radius: 8px;
                    color: {C_TEXT};
                    font-weight: 700; font-size: 12px;
                    outline: none;
                }}
                QPushButton:checked {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                    border: 2px solid {C_ACCENT};
                    color: white;
                }}
                QPushButton:focus   {{ border: 3px solid white; outline:none; }}
                QPushButton:hover   {{ border: 3px solid white; background:{C_SURFACE}; }}
                QPushButton:checked:focus {{ border: 3px solid white; }}
                QPushButton:checked:hover {{ border: 3px solid white; }}
            """)
            if val == "CASH":
                btn.setChecked(True)
            self.pay_group.addButton(btn, i)
            self.pay_buttons[val] = btn
            btn.clicked.connect(self._update_pay_display)
            row1.addWidget(btn)
        pl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        split_lbl = QLabel("SPLIT:")
        split_lbl.setStyleSheet(f"color:{C_TEXT};font-size:11px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        row2.addWidget(split_lbl)

        self.split_check = QPushButton("⚡ Split")
        self.split_check.setCheckable(True)
        self.split_check.setFixedHeight(34)
        self.split_check.setMinimumWidth(88)
        self.split_check.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.split_check.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE2};
                border: 2px solid {C_BORDER};
                border-radius: 8px; color: {C_MUTED};
                font-weight: 700; font-size: 12px; outline: none;
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                border: 2px solid {C_ACCENT};
                color: white;
            }}
            QPushButton:checked:focus {{ border: 3px solid white; }}
            QPushButton:checked:hover {{ border: 3px solid white; }}
            QPushButton:focus {{ border: 3px solid white; outline: none; }}
            QPushButton:hover {{ border: 3px solid white; color: {C_TEXT}; }}
        """)
        self.split_check.toggled.connect(self._toggle_split)
        row2.addWidget(self.split_check)

        self.split_pay_group = QButtonGroup(self)
        self.split_pay_buttons = {}

        self.split_amount_edit = QLineEdit()
        self.split_amount_edit.setPlaceholderText("₹ Amt")
        self.split_amount_edit.setFixedHeight(34)
        self.split_amount_edit.setMinimumWidth(80)
        self.split_amount_edit.setEnabled(False)
        self.split_amount_edit.setStyleSheet(f"background:{C_SURFACE2};border:2px solid {C_BORDER};border-radius:8px;color:{C_TEXT};font-size:12px;padding:2px 8px;")
        self.split_amount_edit.installEventFilter(self)
        self.split_amount_edit.textChanged.connect(self._update_pay_display)
        row2.addWidget(self.split_amount_edit)

        split_pay_opts = [("📱 UPI","UPI2"), ("💳 CARD","CARD2"), ("💰 CASH","CASH2")]
        for i, (label, val) in enumerate(split_pay_opts):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setEnabled(False)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(88)
            btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{C_SURFACE2};border:2px solid {C_BORDER};border-radius:8px;
                    color:{C_MUTED};font-size:12px;font-weight:700; outline:none;
                }}
                QPushButton:checked {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                    border:2px solid {C_ACCENT}; color:white;
                }}
                QPushButton:checked:focus {{ border:3px solid white; outline:none; }}
                QPushButton:checked:hover {{ border:3px solid white; }}
                QPushButton:focus {{ border:3px solid white; outline:none; }}
                QPushButton:enabled:hover {{ border:3px solid white; color:{C_TEXT}; }}
            """)
            self.split_pay_group.addButton(btn, i)
            self.split_pay_buttons[val] = btn
            btn.installEventFilter(self)
            btn.clicked.connect(self._update_pay_display)
            row2.addWidget(btn)

        row2.addStretch()
        pl.addLayout(row2)

        self._pay_vals_list = list(self.pay_buttons.keys())

        for val, btn in self.pay_buttons.items():
            btn.installEventFilter(self)

        ll.addWidget(pay_frame)
        return left

    def _build_right_panel(self):
        right = QFrame()
        right.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        right.setMinimumWidth(230)
        right.setMaximumWidth(360)
        right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 10, 12, 10)
        rl.setSpacing(6)

        title = QLabel("⚡  ACTIONS")
        title.setStyleSheet(f"font-size:13px;font-weight:800;color:{C_TEXT};letter-spacing:1px;")
        title.setAlignment(Qt.AlignCenter)
        rl.addWidget(title)

        ACT_BTNS = [
            ("📄  Preview  (Ctrl+V)",   "#7c6aff", "#5a49d0",  self._preview_bill),
            ("📱  Send WhatsApp",        "#25D366", "#128C7E",  self._whatsapp_dialog),
            ("⏸  Hold Bill  (F4)",      "#ff8a65", "#e64a19",  self._hold_bill),
            ("🔄  Clear All  (Ctrl+C)", "#ce93d8", "#8e24aa",  self._clear_all),
        ]
        self._action_buttons = []
        for text, color, dark, fn in ACT_BTNS:
            btn = QPushButton(text)
            btn.setFixedHeight(44)
            btn.setMinimumWidth(180)
            btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {color},stop:1 {dark});
                    border: 2px solid transparent;
                    border-radius: 9px;
                    color: white;
                    font-weight: 700;
                    font-size: 12px;
                    outline: none;
                }}
                QPushButton:hover  {{ border: 2px solid rgba(255,255,255,0.8); background:{dark}; }}
                QPushButton:pressed {{ background:{dark}; border: 3px solid white; }}
                QPushButton:focus  {{ border: 3px solid white; outline:none; }}
            """)
            btn.clicked.connect(fn)
            rl.addWidget(btn)
            self._action_buttons.append(btn)

        rl.addSpacing(8)

        gt_box = QFrame()
        gt_box.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(124,106,255,0.15), stop:1 rgba(124,106,255,0.05));
                border:1px solid {C_ACCENT};
                border-radius:10px;
            }}
        """)
        gt_l = QVBoxLayout(gt_box)
        gt_l.setContentsMargins(12, 10, 12, 10)
        gt_l.setSpacing(4)

        gt_header = QLabel("AMOUNT TO PAY")
        gt_header.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:2px;background:transparent;border:none;")
        gt_header.setAlignment(Qt.AlignCenter)
        gt_l.addWidget(gt_header)

        self.gt_display = QLabel("₹ 0")
        self.gt_display.setStyleSheet(f"color:{C_TEXT};font-size:28px;font-weight:800;background:transparent;border:none;")
        self.gt_display.setAlignment(Qt.AlignCenter)
        gt_l.addWidget(self.gt_display)

        self.pay_mode_display = QLabel("CASH")
        self.pay_mode_display.setStyleSheet(f"color:{C_MUTED};font-size:12px;font-weight:600;background:transparent;border:none;")
        self.pay_mode_display.setAlignment(Qt.AlignCenter)
        gt_l.addWidget(self.pay_mode_display)

        rl.addWidget(gt_box)

        calc_box = QFrame()
        calc_box.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(124,106,255,0.15), stop:1 rgba(124,106,255,0.05));
                border:1px solid {C_ACCENT};
                border-radius:10px;
            }}
        """)
        calc_l = QVBoxLayout(calc_box)
        calc_l.setContentsMargins(4, 4, 4, 4)
        calc_l.setSpacing(2)

        calc_hdr = QLabel("CALCULATOR")
        calc_hdr.setStyleSheet(f"color:{C_MUTED};font-size:8px;font-weight:600;letter-spacing:1px;background:transparent;border:none;")
        calc_hdr.setAlignment(Qt.AlignCenter)
        calc_hdr.setFixedHeight(15)
        calc_l.addWidget(calc_hdr)

        self.calc_display = QLineEdit("0")
        self.calc_display.setReadOnly(True)
        self.calc_display.setAlignment(Qt.AlignRight)
        self.calc_display.setMinimumHeight(30)
        self.calc_display.setMaximumHeight(40)
        self.calc_display.setStyleSheet(f"""
            background:{C_BG}; border:1px solid {C_ACCENT}; border-radius:6px;
            color:{C_TEXT}; font-size:18px; font-weight:800; padding:0 8px;
        """)
        calc_l.addWidget(self.calc_display)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(3)
        for row in range(5):
            btn_grid.setRowStretch(row, 1)
        for col in range(4):
            btn_grid.setColumnStretch(col, 1)

        calc_btn_ss = lambda color=None: f"""
            QPushButton {{
                background:{color if color else C_SURFACE2}; border:2px solid transparent; border-radius:6px;
                color:{C_TEXT}; font-size:11px; font-weight:700;
            }}
            QPushButton:hover {{ background:{C_ACCENT}; border:2px solid rgba(255,255,255,0.6); }}
            QPushButton:pressed {{ background:{C_BORDER}; }}
            QPushButton:focus {{ border:2px solid transparent; outline:none; }}
        """
        op_ss  = calc_btn_ss(C_ACCENT)
        clr_ss = calc_btn_ss(C_RED)
        eq_ss  = calc_btn_ss(C_GREEN)
        pay_ss = calc_btn_ss(C_ACCENT)

        self._calc_expr = ""
        self._calc_new  = True

        calc_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def calc_press(val):
            if val == "C":
                self._calc_expr = ""
                self._calc_new  = True
                self.calc_display.setText("0")
            elif val == "⌫":
                self._calc_expr = self._calc_expr[:-1] or "0"
                self.calc_display.setText(self._calc_expr or "0")
            elif val == "=":
                try:
                    result = eval(self._calc_expr.replace("×","*").replace("÷","/"))
                    result = round(result, 2)
                    self._calc_expr = str(result)
                    self.calc_display.setText(str(result))
                    self._calc_new = True
                except Exception:
                    self.calc_display.setText("Error")
                    self._calc_expr = ""
            elif val == "GT":
                try:
                    grand, _, _ = self._get_grand_total()
                    self._calc_expr = str(round(grand, 2))
                    self.calc_display.setText(self._calc_expr)
                    self._calc_new = False
                except Exception:
                    pass
            else:
                if self._calc_new and val not in "+-×÷.":
                    self._calc_expr = val
                    self._calc_new = False
                else:
                    if self._calc_expr == "0" and val not in "+-×÷.":
                        self._calc_expr = val
                    else:
                        self._calc_expr += val
                self.calc_display.setText(self._calc_expr)

        calc_buttons = [
            ("GT",  pay_ss), ("C",   clr_ss), ("⌫",  op_ss),  ("÷",  op_ss),
            ("7",   None),   ("8",   None),   ("9",  None),   ("×",  op_ss),
            ("4",   None),   ("5",   None),   ("6",  None),   ("-",  op_ss),
            ("1",   None),   ("2",   None),   ("3",  None),   ("+",  op_ss),
            ("0",   None),   (".",   None),   ("00", None),   ("=",  eq_ss),
        ]

        self._calc_buttons = []
        for i, (label, ss) in enumerate(calc_buttons):
            b = QPushButton(label)
            b.setMinimumHeight(24)
            b.setMaximumHeight(36)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            b.setFocusPolicy(Qt.StrongFocus)
            b.setStyleSheet(ss if ss else calc_btn_ss())
            b.clicked.connect(lambda _, v=label: calc_press(v))
            b.installEventFilter(self)
            btn_grid.addWidget(b, i // 4, i % 4)
            self._calc_buttons.append(b)

        calc_l.addLayout(btn_grid)
        rl.addWidget(calc_box, 1)

        def _update_calc_box_border(focused):
            if focused:
                calc_box.setStyleSheet(f"""
                    QFrame {{
                        background: {C_SURFACE2};
                        border: 2px solid white;
                        border-radius: 10px;
                    }}
                """)
            else:
                calc_box.setStyleSheet(f"""
                    QFrame {{
                        background: {C_SURFACE2};
                        border: 1px solid {C_BORDER};
                        border-radius: 10px;
                    }}
                """)
    
        btn_grid.setRowMinimumHeight(0, 0) 

        for row_i in range(5):
            btn_grid.setRowStretch(row_i, 1)
        for col_i in range(4):
            btn_grid.setColumnStretch(col_i, 1)

        credit_box = QFrame()
        credit_box.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3d2f99,stop:1 #7c6aff);
                border-radius: 10px;
                border: none;
            }}
        """)
        cl = QVBoxLayout(credit_box)
        cl.setContentsMargins(10, 12, 10, 12)
        cl.setSpacing(4)
        cl.setAlignment(Qt.AlignCenter)

        designed_lbl = QLabel("Designed by")
        designed_lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 11px; font-weight: 600; background: transparent; border: none;")
        designed_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(designed_lbl)

        logo_lbl = QLabel()
        logo_pix = QPixmap("logo.png")
        if not logo_pix.isNull():
            logo_lbl.setPixmap(logo_pix.scaled(180, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("adaptare UI")
            logo_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: 900; background: transparent; border: none;")
        
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        cl.addWidget(logo_lbl)

        email_lbl = QLabel("adnan.uc3m@gmail.com")
        email_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: 700; background: transparent; border: none;")
        email_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(email_lbl)

        rl.addWidget(credit_box)

        return right

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.clock_lbl.setText(now.toString("hh:mm:ss AP\ndd MMM yyyy"))
        QTimer.singleShot(1000, self._tick)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F1"),      self).activated.connect(lambda: self.item_entry.setFocus())
        QShortcut(QKeySequence("F2"),      self).activated.connect(lambda: self._calc_buttons[0].setFocus() if hasattr(self, '_calc_buttons') else None)
        QShortcut(QKeySequence("Ctrl+P"),  self).activated.connect(self._print_bill)
        QShortcut(QKeySequence("Ctrl+V"),  self).activated.connect(self._preview_bill)
        QShortcut(QKeySequence("Ctrl+C"),  self).activated.connect(self._clear_all)
        QShortcut(QKeySequence("Delete"),  self).activated.connect(self._remove_selected)
        QShortcut(QKeySequence("F4"),      self).activated.connect(self._hold_bill)

        self.item_entry.returnPressed.connect(self._on_item_return)
        self.mrp_entry.returnPressed.connect(self.price_entry.setFocus)
        self.mrp_entry.editingFinished.connect(self._calc_discount)
        self.price_entry.returnPressed.connect(self.qty_entry.setFocus)
        self.price_entry.editingFinished.connect(self._calc_discount)
        self.qty_entry.returnPressed.connect(self._add_item)

        for val, btn in self.pay_buttons.items():
            btn.installEventFilter(self)

        self.split_check.installEventFilter(self)
        self.split_amount_edit.installEventFilter(self)
        for btn in self.split_pay_buttons.values():
            btn.installEventFilter(self)

        for btn in self._action_buttons:
            btn.installEventFilter(self)

        self.qty_entry.installEventFilter(self)
        self.item_entry.installEventFilter(self)
        self.cart_table.installEventFilter(self)

        self.cust_name.returnPressed.connect(self.cust_phone.setFocus)
        self.cust_phone.returnPressed.connect(self.item_entry.setFocus)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            key = event.key()

            popup = getattr(self, '_suggest_popup', None)
            if obj == self.item_entry and popup and popup.isVisible():
                if key == Qt.Key_Down:
                    row = self._suggest_list.currentRow()
                    self._suggest_list.setCurrentRow(min(row + 1, self._suggest_list.count() - 1))
                    self._on_suggest_select()
                    return True
                if key == Qt.Key_Up:
                    row = self._suggest_list.currentRow()
                    if row <= 0:
                        popup.hide()
                    else:
                        self._suggest_list.setCurrentRow(max(row - 1, 0))
                        self._on_suggest_select()
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    if self._suggest_list.currentRow() >= 0:
                        self._on_suggest_confirm()
                        return True
                if key == Qt.Key_Escape:
                    popup.hide()
                    return True

        if event.type() == QEvent.KeyPress:
            key = event.key()

            all_tb = [self.menu_btn, self.admin_btn] + getattr(self, '_taskbar_buttons', []) + [self.theme_btn]
            if obj in all_tb:
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    obj.click()
                    return True
                if key in (Qt.Key_Right, Qt.Key_Tab):
                    idx = all_tb.index(obj)
                    all_tb[(idx + 1) % len(all_tb)].setFocus()
                    return True
                if key == Qt.Key_Left:
                    idx = all_tb.index(obj)
                    all_tb[(idx - 1) % len(all_tb)].setFocus()
                    return True

            if obj == self.item_entry and key == Qt.Key_Down:
                self.pay_buttons["CASH"].setFocus()
                return True

            if obj == self.cart_table and key == Qt.Key_Down:
                self.pay_buttons["CASH"].setFocus()
                return True

            if obj == self.qty_entry and key == Qt.Key_Down:
                self.pay_buttons["CASH"].setFocus()
                return True

            if obj in self.pay_buttons.values():
                if key in (Qt.Key_Tab, Qt.Key_Right):
                    vals = self._pay_vals_list
                    cur = next((v for v,b in self.pay_buttons.items() if b == obj), None)
                    if cur:
                        nxt = vals[(vals.index(cur)+1) % len(vals)]
                        self.pay_buttons[nxt].setFocus()
                        return True
                if key == Qt.Key_Left:
                    vals = self._pay_vals_list
                    cur = next((v for v,b in self.pay_buttons.items() if b == obj), None)
                    if cur:
                        prv = vals[(vals.index(cur)-1) % len(vals)]
                        self.pay_buttons[prv].setFocus()
                        return True
                if key == Qt.Key_Down:
                    self.split_check.setFocus()
                    return True
                if key == Qt.Key_Up:
                    self.cart_table.setFocus()
                    return True
                if key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
                    obj.setChecked(True)
                    self.pay_group.setExclusive(True)
                    self._update_pay_display()
                    return True

            if obj == self.split_check:
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    obj.toggle()
                    return True
                if key == Qt.Key_Down:
                    if self.split_check.isChecked():
                        self.split_amount_edit.setFocus()
                        self.split_amount_edit.selectAll()
                    else:
                        if self._action_buttons:
                            self._action_buttons[0].setFocus()
                    return True
                if key == Qt.Key_Up:
                    self.pay_buttons["CASH"].setFocus()
                    return True

            if obj == self.split_amount_edit:
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down):
                    split_btns = list(self.split_pay_buttons.values())
                    if split_btns:
                        split_btns[0].setFocus()
                    return True
                if key == Qt.Key_Up:
                    self.split_check.setFocus()
                    return True

            if obj in self.split_pay_buttons.values():
                split_btns = list(self.split_pay_buttons.values())
                if key in (Qt.Key_Tab, Qt.Key_Right):
                    cur_idx = split_btns.index(obj) if obj in split_btns else 0
                    nxt = (cur_idx + 1) % len(split_btns)
                    split_btns[nxt].setFocus()
                    return True
                if key == Qt.Key_Left:
                    cur_idx = split_btns.index(obj) if obj in split_btns else 0
                    prv = (cur_idx - 1) % len(split_btns)
                    split_btns[prv].setFocus()
                    return True
                if key == Qt.Key_Down:
                    if self._action_buttons:
                        self._action_buttons[0].setFocus()
                    return True
                if key == Qt.Key_Up:
                    self.split_amount_edit.setFocus()
                    return True
                if key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
                    obj.setChecked(True)
                    self.split_pay_group.setExclusive(True)
                    self._update_pay_display()
                    return True

            if obj in self._action_buttons:
                idx = self._action_buttons.index(obj)
                if key == Qt.Key_Down:
                    if idx == len(self._action_buttons) - 1:
                        if hasattr(self, '_calc_buttons') and self._calc_buttons:
                            self._calc_buttons[0].setFocus()
                    else:
                        self._action_buttons[idx + 1].setFocus()
                    return True
                if key == Qt.Key_Up:
                    if idx == 0:
                        if self.split_check.isChecked():
                            split_btns = list(self.split_pay_buttons.values())
                            if split_btns:
                                split_btns[0].setFocus()
                        else:
                            self.split_check.setFocus()
                    else:
                        self._action_buttons[idx - 1].setFocus()
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    obj.click()
                    return True

            if hasattr(self, '_calc_buttons') and obj in self._calc_buttons:
                key_map = {
                    Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
                    Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
                    Qt.Key_8: "8", Qt.Key_9: "9",
                    Qt.Key_Plus: "+", Qt.Key_Minus: "-",
                    Qt.Key_Asterisk: "×", Qt.Key_Slash: "÷",
                    Qt.Key_Period: ".", Qt.Key_Comma: ".",
                    Qt.Key_Return: "=", Qt.Key_Enter: "=",
                    Qt.Key_Backspace: "⌫", Qt.Key_Delete: "C",
                    Qt.Key_Escape: "C",
                }
                if key in key_map:
                    val = key_map[key]
                    for b in self._calc_buttons:
                        if b.text() == val:
                            b.click(); return True
                if key == Qt.Key_Up:
                    if self._action_buttons:
                        self._action_buttons[-1].setFocus()
                    return True
                if key in (Qt.Key_Tab, Qt.Key_Right):
                    idx = self._calc_buttons.index(obj) if obj in self._calc_buttons else -1
                    nxt = (idx + 1) % len(self._calc_buttons)
                    self._calc_buttons[nxt].setFocus()
                    return True
                if key == Qt.Key_Left:
                    idx = self._calc_buttons.index(obj) if obj in self._calc_buttons else 0
                    prv = (idx - 1) % len(self._calc_buttons)
                    self._calc_buttons[prv].setFocus()
                    return True

        from PySide6.QtCore import QEvent as _QE
        if event.type() in (_QE.FocusIn, _QE.FocusOut):
            if hasattr(self, '_calc_buttons') and obj in self._calc_buttons:
                if hasattr(self, '_update_calc_box_border'):
                    self._update_calc_box_border(event.type() == _QE.FocusIn)

        return super().eventFilter(obj, event)

    def _setup_item_completer(self):
        self._suggest_popup = QFrame(self, Qt.ToolTip | Qt.FramelessWindowHint)
        self._suggest_popup.setStyleSheet(f"""
            QFrame {{
                background: {C_SURFACE2};
                border: 2px solid {C_ACCENT};
                border-radius: 8px;
            }}
        """)
        self._suggest_popup.hide()

        popup_layout = QVBoxLayout(self._suggest_popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(0)

        self._suggest_list = QListWidget()
        self._suggest_list.setFixedHeight(200)
        self._suggest_list.setFocusPolicy(Qt.NoFocus)
        self._suggest_list.setStyleSheet(f"""
            QListWidget {{
                background: {C_SURFACE2}; border: none;
                color: {C_TEXT}; font-size: 13px;
            }}
            QListWidget::item {{ padding: 7px 12px; border-radius: 5px; }}
            QListWidget::item:selected {{ background: {C_ACCENT}; color: white; }}
            QListWidget::item:hover {{ background: rgba(124,106,255,0.3); }}
        """)
        popup_layout.addWidget(self._suggest_list)

        self._suggest_list.itemClicked.connect(self._on_suggest_confirm)
        self.item_entry.textChanged.connect(self._update_suggestions)
        self.item_entry.installEventFilter(self)

        self._suggest_matches = []

    def _update_suggestions(self, text):
        text = text.strip()
        if len(text) < 1:
            self._suggest_popup.hide()
            return
        tl = text.lower()
        matches = [(code, p) for code, p in self.products.items()
                   if tl in p['name'].lower() or tl in code.lower()]
        matches = matches[:12]
        self._suggest_matches = matches
        if not matches:
            self._suggest_popup.hide()
            return
        self._suggest_list.clear()
        for code, p in matches:
            item = QListWidgetItem(p['name'])
            item.setData(Qt.UserRole, code)
            self._suggest_list.addItem(item)

        ge = self.item_entry.mapToGlobal(self.item_entry.rect().bottomLeft())
        self._suggest_popup.move(ge)
        self._suggest_popup.setFixedWidth(max(400, self.item_entry.width()))
        self._suggest_popup.show()
        self._suggest_popup.raise_()

    def _on_suggest_select(self):
        item = self._suggest_list.currentItem()
        if not item: return
        code = item.data(Qt.UserRole)
        if code and code in self.products:
            p = self.products[code]
            self.item_entry.blockSignals(True)
            self.item_entry.setText(p['name'])
            self.item_entry.blockSignals(False)
            self.mrp_entry.setText(fmt(p['mrp']))
            self.price_entry.setText(fmt(p['price']))
            self._calc_discount()

    def _on_suggest_confirm(self, item=None):
        if item is None:
            item = self._suggest_list.currentItem()
        if not item: return
        code = item.data(Qt.UserRole)
        if code and code in self.products:
            p = self.products[code]
            self.item_entry.blockSignals(True)
            self.item_entry.setText(p['name'])
            self.item_entry.blockSignals(False)
            self.mrp_entry.setText(fmt(p['mrp']))
            self.price_entry.setText(fmt(p['price']))
            self._calc_discount()
        self._suggest_popup.hide()
        QTimer.singleShot(10, self.qty_entry.setFocus)
        QTimer.singleShot(10, self.qty_entry.selectAll)

    def _refresh_completer(self):
        pass

    def _on_cart_item_changed(self, item):
        if getattr(self, '_cart_updating', False):
            return
        row = item.row()
        col = item.column()
        if row >= len(self.cart_items):
            return
        cart_item = self.cart_items[row]
        try:
            val = float(item.text())
        except ValueError:
            return
        self._cart_updating = True
        if col == 1:
            cart_item['mrp'] = val
        elif col == 2:
            cart_item['base_price'] = val
        elif col == 4:
            if val > 0:
                cart_item['qty'] = val
        cart_item['total'] = cart_item['base_price'] * cart_item['qty']
        disc = cart_item['mrp'] - cart_item['base_price']
        di = self.cart_table.item(row, 3)
        if di: di.setText(fmt(disc) if disc else "0")
        ti = self.cart_table.item(row, 5)
        if ti: ti.setText(fmt(cart_item['total']))
        self._cart_updating = False
        self._update_totals()

    def _toggle_split(self, enabled):
        self.split_amount_edit.setEnabled(enabled)
        for btn in self.split_pay_buttons.values():
            btn.setEnabled(enabled)
        if enabled and not any(b.isChecked() for b in self.split_pay_buttons.values()):
            list(self.split_pay_buttons.values())[0].setChecked(True)
        self._update_pay_display()

    def _update_pay_display(self):
        primary = self._get_primary_payment()
        if self.split_check.isChecked():
            split_method = self._get_split_method()
            try:
                split_amt = float(self.split_amount_edit.text() or 0)
            except ValueError:
                split_amt = 0
            grand, _, _ = self._get_grand_total()
            primary_amt = max(0, grand - split_amt)
            self.pay_mode_display.setText(f"{primary}: ₹{fmt(primary_amt)}\n{split_method}: ₹{fmt(split_amt)}")
        else:
            self.pay_mode_display.setText(primary)

    def _get_primary_payment(self):
        for val, btn in self.pay_buttons.items():
            if btn.isChecked():
                return val
        return "CASH"

    def _get_split_method(self):
        map_ = {"UPI2": "UPI", "CARD2": "CARD", "CASH2": "CASH"}
        for val, btn in self.split_pay_buttons.items():
            if btn.isChecked():
                return map_.get(val, "UPI")
        return "UPI"

    def _get_payment(self):
        primary = self._get_primary_payment()
        if self.split_check.isChecked():
            split_method = self._get_split_method()
            try:
                split_amt = float(self.split_amount_edit.text() or 0)
            except ValueError:
                split_amt = 0
            grand, _, _ = self._get_grand_total()
            primary_amt = max(0, grand - split_amt)
            return f"{primary}(₹{fmt(primary_amt)})+{split_method}(₹{fmt(split_amt)})"
        return primary

    def _on_barcode_input(self, text):
        code = text.strip()
        if code in self.products:
            self._barcode_timer.start(150)

    def _try_barcode_auto_add(self):
        code = self.item_entry.text().strip()
        if code in self.products:
            p = self.products[code]
            self.item_entry.setText(p['name'])
            self.mrp_entry.setText(fmt(p['mrp']))
            self.price_entry.setText(fmt(p['price']))
            self._calc_discount()
            self._add_item()

    def _on_item_return(self):
        code = self.item_entry.text().strip()
        if code in self.products:
            p = self.products[code]
            self.item_entry.setText(p['name'])
            self.mrp_entry.setText(fmt(p['mrp']))
            self.price_entry.setText(fmt(p['price']))
            self._calc_discount()
            self._add_item()
        else:
            self.mrp_entry.setFocus()

    def _calc_discount(self):
        try:
            mrp   = float(self.mrp_entry.text() or 0)
            price = float(self.price_entry.text() or 0)
            disc  = mrp - price
            self.disc_show.setText(f"−{fmt(disc)}" if disc else "")
        except ValueError:
            pass

    def _add_item(self):
        if hasattr(self, '_suggest_popup'):
            self._suggest_popup.hide()
        name  = self.item_entry.text().strip()
        if not name:
            return
        try:
            mrp   = float(self.mrp_entry.text() or 0)
            price = float(self.price_entry.text() or 0)
            qty   = float(self.qty_entry.text().strip() or 1)
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid number in MRP, Price, or Qty.")
            return

        if mrp <= 0 or price <= 0 or qty <= 0:
            QMessageBox.warning(self, "Error", "MRP, Price and Qty must be positive.")
            return

        code = None
        for c, p in self.products.items():
            if p['name'].lower() == name.lower():
                code = c
                break
            if c == name:
                code = c
                name = p['name']
                break

        for item in self.cart_items:
            match = (code and item.get('code') == code) or \
                    (not code and item['name'].lower() == name.lower())
            if match:
                item['qty'] += qty
                item['total'] = item['base_price'] * item['qty']
                self._rebuild_cart()
                self._update_totals()
                self._clear_input()
                self.status_bar.showMessage(f"Updated: {name} ×{fmt(item['qty'])}")
                return

        item_data = {
            'code': code or 'manual', 'name': name,
            'mrp': mrp, 'base_price': price,
            'qty': qty, 'total': price * qty
        }
        self.cart_items.append(item_data)

        if code and code in self.products:
            self.products[code]['stock'] = max(0, float(self.products[code]['stock']) - qty)
            save_products(self.products)

        self._rebuild_cart()
        self._update_totals()
        self._clear_input()
        self.status_bar.showMessage(f"Added: {name} ×{fmt(qty)}")

    def _clear_input(self):
        self.item_entry.clear()
        self.mrp_entry.clear()
        self.price_entry.clear()
        self.qty_entry.setText("1")
        self.disc_show.setText("")
        if hasattr(self, '_suggest_popup'):
            self._suggest_popup.hide()
        self.item_entry.setFocus()

    def _rebuild_cart(self):
        self._cart_updating = True
        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(0)
        for idx, item in enumerate(self.cart_items):
            r = self.cart_table.rowCount()
            self.cart_table.insertRow(r)
            disc = item['mrp'] - item['base_price']

            vals = [
                item['name'],
                fmt(item['mrp']),
                fmt(item['base_price']),
                fmt(disc),
                fmt(item['qty']),
                fmt(item['total']),
                item.get('code',''),
            ]
            for col, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setFont(QFont("Segoe UI", 16))
                cell.setTextAlignment(Qt.AlignCenter)
                if col == 0:
                    cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if col == 3 and disc > 0:
                    cell.setForeground(QColor("#69f0ae"))
                if col == 5:
                    cell.setForeground(QColor("#90caf9"))
                    cell.setFont(QFont("Segoe UI", 14, QFont.Bold))
                self.cart_table.setItem(r, col, cell)

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #c62828;
                    border: none;
                    border-radius: 5px;
                    color: white;
                    font-weight: 900;
                    font-size: 13px;
                    padding: 0;
                    margin: 2px;
                }}
                QPushButton:hover {{ background: #b71c1c; border: 1px solid white; }}
            """)
            del_btn.setFixedSize(40, 30)
            del_btn.setCursor(QCursor(Qt.PointingHandCursor))
            del_btn.clicked.connect(lambda _, i=idx: self._delete_item(i))
            cell_widget = QWidget()
            cell_widget.setStyleSheet("background:transparent;")
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(2, 2, 2, 2)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(del_btn)
            self.cart_table.setColumnWidth(7, 65)
            self.cart_table.setRowHeight(r, 42)
            self.cart_table.setCellWidget(r, 7, cell_widget)

        self.cart_table.blockSignals(False)
        self._cart_updating = False

    def _update_totals(self):
        subtotal = sum(i['mrp'] * i['qty'] for i in self.cart_items)
        total_disc = sum((i['mrp'] - i['base_price']) * i['qty'] for i in self.cart_items)
        grand = subtotal - total_disc

        try:
            extra_rs = float(self.extra_disc_edit.text() or 0)
            extra_rs = max(0, extra_rs)
        except ValueError:
            extra_rs = 0

        grand = max(0, grand - extra_rs)

        total_qty = sum(i['qty'] for i in self.cart_items)
        self.items_count_lbl.setText(f"Items: {fmt(total_qty)}  ({len(self.cart_items)} types)")
        self.subtotal_lbl.setText(f"Subtotal: ₹{fmt(subtotal)}")

        disc_text = f"₹{fmt(total_disc)}"
        if extra_rs > 0:
            disc_text += f" + ₹{fmt(extra_rs)} = ₹{fmt(total_disc + extra_rs)}"
        self.discount_lbl.setText(f"Discount: {disc_text}")
        self.grand_total_lbl.setText(f"GRAND TOTAL: ₹{fmt(grand)}")
        self.gt_display.setText(f"₹ {fmt(grand)}")
        self._update_pay_display()

    def _get_grand_total(self):
        subtotal = sum(i['mrp'] * i['qty'] for i in self.cart_items)
        total_disc = sum((i['mrp'] - i['base_price']) * i['qty'] for i in self.cart_items)
        grand = subtotal - total_disc
        try:
            extra_rs = float(self.extra_disc_edit.text() or 0)
            extra_rs = max(0, extra_rs)
        except ValueError:
            extra_rs = 0
        grand = max(0, grand - extra_rs)
        return grand, subtotal, total_disc

    def _delete_item(self, idx):
        if 0 <= idx < len(self.cart_items):
            item = self.cart_items[idx]
            code = item.get('code')
            if code and code in self.products and code != 'manual':
                self.products[code]['stock'] = float(self.products[code]['stock']) + item['qty']
                save_products(self.products)
            self.cart_items.pop(idx)
            self._rebuild_cart()
            self._update_totals()

    def _remove_selected(self):
        row = self.cart_table.currentRow()
        if row >= 0:
            self._delete_item(row)
        else:
            QMessageBox.information(self, "Select", "Click a cart row first.")

    def _phone_autofill(self, phone):
        phone = phone.strip()
        if phone in self.customers:
            if not self.cust_name.text().strip():
                self.cust_name.setText(self.customers[phone]['name'])
            pts = self.customers[phone]['points']
            self.pts_lbl.setText(f"⭐ {pts} pts")
        else:
            self.pts_lbl.setText("⭐ —")

    def _tier_local(self, pts):
        if pts >= 10000: return "💎 Diamond", "#b9f2ff"
        if pts >= 5000:  return "🏆 Platinum", "#e5e4e2"
        if pts >= 2000:  return "⭐⭐ Gold",   "#FFD700"
        if pts >= 1000:  return "⭐ Silver",   "#C0C0C0"
        if pts > 0:      return "🥉 Bronze",   "#CD7F32"
        return "🆕 New", "#b0b8cc"

    def _build_bill_text(self):
        grand, subtotal, total_disc = self._get_grand_total()
        try:
            extra_rs = float(self.extra_disc_edit.text() or 0)
            extra_rs = max(0, extra_rs)
        except ValueError:
            extra_rs = 0

        W = 42

        b = []
        b.append("=" * W)
        b.append(MART_NAME.upper().center(W))
        b.append(TAGLINE.center(W))
        b.append(ADDRESS.center(W))
        b.append(f"GST:{GSTIN} {PHONE}".center(W))
        b.append("=" * W)
        b.append(f"Bill No : {self.current_bill_no}")
        b.append(f"Date    : {datetime.now():%d-%m-%Y %I:%M %p}")
        cust_name_txt  = self.cust_name.text().strip() or 'Walk-in Customer'
        cust_phone_txt = self.cust_phone.text().strip()
        b.append(f"Customer: {cust_name_txt}")
        if cust_phone_txt:
            b.append(f"Phone   : {cust_phone_txt}")
            if cust_phone_txt in self.customers:
                pts = self.customers[cust_phone_txt]['points']
                tier, _ = self._tier_local(pts)
                tier_plain = tier.replace("💎","").replace("🏆","").replace("⭐⭐","").replace("⭐","").replace("🥉","").replace("🆕","").strip()
                b.append(f"Loyalty : {pts} pts  |  {tier_plain}")
        b.append("-" * W)

        ITEM_W  = 14
        QTY_W   = 4
        MRP_W   = 6
        PRICE_W = 6
        TOTAL_W = 8

        hdr = f"{'ITEM':<{ITEM_W}} {'QTY':>{QTY_W}} {'MRP':>{MRP_W}} {'PRICE':>{PRICE_W}} {'TOTAL':>{TOTAL_W}}"
        b.append(hdr)
        b.append("-" * W)

        for item in self.cart_items:
            name  = item['name'][:ITEM_W]
            line  = (f"{name:<{ITEM_W}} "
                    f"{fmt(item['qty']):>{QTY_W}} "
                    f"{fmt(item['mrp']):>{MRP_W}} "
                    f"{fmt(item['base_price']):>{PRICE_W}} "
                    f"{fmt(item['total']):>{TOTAL_W}}")
            b.append(line)

        b.append("-" * W)

        LPAD = W - TOTAL_W - 1
        b.append(f"{'Subtotal:':<{LPAD}} {'Rs.'+fmt(subtotal):>{TOTAL_W}}")
        disc_total = total_disc + extra_rs
        if disc_total > 0:
            b.append(f"{'Discount:':<{LPAD}} {'Rs.'+fmt(disc_total):>{TOTAL_W}}")
        b.append(f"{'GRAND TOTAL:':<{LPAD}} {'Rs.'+fmt(grand):>{TOTAL_W}}")
        b.append("=" * W)

        pay_str = self._get_payment().replace("₹", "Rs.")
        b.append(f"PAYMENT: {pay_str}")
        b.append(f"Items (types): {len(self.cart_items)}")

        if cust_phone_txt and cust_phone_txt in self.customers:
            earned   = int(grand // 100)
            pts_now  = self.customers[cust_phone_txt]['points']
            b.append(f"Loyalty: {pts_now} pts  (+{earned})")

        b.append("=" * W)
        b.append("THANK YOU!  VISIT AGAIN".center(W))
        b.append(datetime.now().strftime("%d-%m-%Y %I:%M %p").center(W))

        return "\n".join(b)

    def _preview_bill(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Cart", "No items in cart!")
            return
        dlg = BillPreviewDialog(self._build_bill_text(), parent=self)
        dlg.exec()

    def _print_thermal(self):
        bill_text = self._build_bill_text()

        if not REPORTLAB_OK:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
            tmp.write(bill_text)
            tmp.close()
            try:
                os.startfile(tmp.name, "print")
            except Exception:
                os.startfile(tmp.name)
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        filename = tmp.name
        tmp.close()

        width  = 80 * mm
        height = 297 * mm
        c = rl_canvas.Canvas(filename, pagesize=(width, height))
        y = height - 8

        lines = bill_text.split("\n")
        for line in lines:
            stripped = line.rstrip()
            if (stripped.startswith("=") or stripped.startswith("-")
                    or "GRAND TOTAL" in stripped or MART_NAME.upper() in stripped):
                font_name = "Courier-Bold"
                font_size = 12 if MART_NAME.upper() in stripped else 8
            else:
                font_name = "Courier"
                font_size = 8

            c.setFont(font_name, font_size)
            text_w = c.stringWidth(stripped, font_name, font_size)
            if (len(stripped) < 36 and not stripped.startswith(" ")
                    and not any(stripped.startswith(k) for k in
                                ["Bill","Date","Cust","Phone","Loyal","ITEM","PAYMENT","Items","No."])):
                x = max(2, (width - text_w) / 2)
            else:
                x = 2

            c.drawString(x, y, stripped)
            y -= (font_size + 3)
            if y < 10:
                c.showPage()
                y = height - 8

        c.save()

        try:
            if os.name == 'nt':
                os.startfile(filename, "print")
            else:
                import subprocess
                subprocess.Popen(["xdg-open", filename])
        except Exception:
            QMessageBox.information(self, "Bill PDF",
                f"Bill saved to:\n{filename}\n\nPlease open and print manually.")

    def _print_bill(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Cart", "No items in cart!")
            return
        if "DUE" in self._get_payment():
            self._add_to_dues()
            return
        self._save_transaction()
        self._print_thermal()
        self._add_points()
        self._clear_all(skip_confirm=True)

    def _hold_bill(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty", "Nothing to hold.")
            return
        grand, _, _ = self._get_grand_total()
        held = load_held_bills()
        held.append({
            'bill_no':   self.current_bill_no,
            'customer':  self.cust_name.text().strip() or 'Walk-in',
            'phone':     self.cust_phone.text().strip(),
            'items':     self.cart_items.copy(),
            'grand':     grand,
            'payment':   self._get_payment(),
            'held_at':   datetime.now().strftime("%H:%M %d-%m-%Y"),
            'extra_disc': self.extra_disc_edit.text().strip(),
        })
        save_held_bills(held)
        self._clear_all(skip_confirm=True)
        self.status_bar.showMessage(f"Bill #{self.current_bill_no} put on hold.")

    def _show_held_bills(self):
        dlg = HeldBillsDialog(self)
        dlg.recall.connect(self._recall_bill)
        dlg.exec()

    def _recall_bill(self, bill):
        self._clear_all(skip_confirm=True)
        self.cart_items = bill.get('items', [])
        self.cust_name.setText(bill.get('customer', ''))
        self.cust_phone.setText(bill.get('phone', ''))
        self.extra_disc_edit.setText(bill.get('extra_disc', ''))
        pay = bill.get('payment', 'CASH')
        if pay in self.pay_buttons:
            self.pay_buttons[pay].setChecked(True)
        self._rebuild_cart()
        self._update_totals()
        self.status_bar.showMessage(f"Recalled bill #{bill.get('bill_no', '')}")

    def _clear_all(self, skip_confirm=False):
        if self.cart_items and not skip_confirm:
            if QMessageBox.question(self, "Confirm", "Start a new bill?") != QMessageBox.Yes:
                return
        self.cart_items = []
        self.cart_table.setRowCount(0)
        self._clear_input()
        self.cust_name.clear()
        self.cust_phone.clear()
        self.pts_lbl.setText("⭐ —")
        self.extra_disc_edit.clear()
        self.pay_buttons["CASH"].setChecked(True)
        self.split_check.setChecked(False)
        self.split_amount_edit.clear()
        self._update_totals()
        self.current_bill_no = get_next_bill_number()
        self.bill_lbl.setText(f"BILL # {self.current_bill_no}")
        self.status_bar.showMessage("New bill started.")

    def _add_to_dues(self):
        if not self.cart_items:
            return
        phone = self.cust_phone.text().strip()
        name  = self.cust_name.text().strip()
        if not phone or not name:
            QMessageBox.warning(self, "Missing", "Enter customer name and phone for dues!")
            return
        grand, _, _ = self._get_grand_total()
        dues = load_dues()
        if phone not in dues:
            dues[phone] = {"name": name, "total_due": 0.0, "transactions": []}
        dues[phone]["name"] = name
        dues[phone]["total_due"] = round(float(dues[phone]["total_due"]) + grand, 2)
        dues[phone]["transactions"].append({
            "date":    datetime.now().strftime("%d-%m-%Y %H:%M"),
            "bill_no": self.current_bill_no,
            "amount":  round(grand, 2),
            "status":  "pending"
        })
        save_dues(dues)
        self._save_transaction("DUE")
        QMessageBox.information(self, "Due Added",
            f"Rs.{fmt(grand)} added to dues for {name}.\n"
            f"Total outstanding: Rs.{fmt(dues[phone]['total_due'])}")
        self._clear_all(skip_confirm=True)

    def _save_transaction(self, payment=None):
        grand, _, _ = self._get_grand_total()
        today = date.today().isoformat()
        sd = load_sales()
        if today not in sd:
            sd[today] = {"cash":0,"upi":0,"card":0,"due":0,"total":0,"transactions":[],"bill_count":0}

        pay_str = payment or self._get_payment()

        import re as _re
        if "+" in pay_str:
            parts = pay_str.split("+")
            matched = False
            for part in parts:
                m = _re.match(r"([A-Z]+)\((?:Rs\.|₹)([\d.]+)\)", part.strip())
                if m:
                    method = m.group(1).lower()
                    amount = float(m.group(2))
                    if method not in sd[today]:
                        sd[today][method] = 0
                    sd[today][method] += amount
                    matched = True
            if not matched:
                pay_key = pay_str.lower().split("(")[0].split("+")[0].strip()
                if pay_key not in sd[today]:
                    sd[today][pay_key] = 0
                sd[today][pay_key] += grand
        else:
            pay_key = pay_str.lower().split("(")[0].strip()
            if pay_key not in sd[today]:
                sd[today][pay_key] = 0
            sd[today][pay_key] += grand

        sd[today]["total"] += grand
        sd[today]["bill_count"] += 1
        sd[today]["transactions"].append({
            "bill_no": self.current_bill_no,
            "time": datetime.now().strftime("%I:%M %p"),
            "customer": self.cust_name.text().strip() or "Walk-in",
            "amount": grand,
            "payment": pay_str,
            "items": len(self.cart_items)
        })
        save_sales(sd)

    def _add_points(self):
        phone = self.cust_phone.text().strip()
        if not phone:
            return
        grand, _, _ = self._get_grand_total()
        earned = int(grand // 100)
        name = self.cust_name.text().strip() or "Walk-in"
        if phone in self.customers:
            self.customers[phone]['points'] += earned
        else:
            self.customers[phone] = {"name": name, "points": earned, "gifts": 0}
        save_customers(self.customers)
        total = self.customers[phone]['points']
        self.pts_lbl.setText(f"⭐ {total} pts")
        if earned:
            self.status_bar.showMessage(f"Earned {earned} pts  |  Total: {total}")

    def _admin_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C_SURFACE2};
                border: 1px solid {C_BORDER};
                border-radius: 8px;
                padding: 4px;
                color: {C_TEXT};
                font-size: 13px;
            }}
            QMenu::item {{ padding: 8px 20px; border-radius: 5px; }}
            QMenu::item:selected {{ background: {C_ACCENT}; color: white; }}
        """)
        menu.addAction("👥 Manage Users", self._manage_users)
        menu.addAction("🔄 Switch User",  self._switch_user)
        menu.addSeparator()
        menu.addAction("🕐 Shifts",       self._shift_management)
        menu.addSeparator()
        menu.addAction("🚪 Logout",        self._logout)
        pos = self.admin_btn.mapToGlobal(self.admin_btn.rect().bottomLeft())
        menu.exec(pos)

    def _build_short_whatsapp_msg(self):
        cust_name = self.cust_name.text().strip() or "Valued Customer"
        grand, subtotal, total_disc = self._get_grand_total()
        disc_total = total_disc
        try:
            extra_rs = float(self.extra_disc_edit.text() or 0)
            disc_total += max(0, extra_rs)
        except ValueError:
            pass
        payment = self._get_payment()
        bill_no = self.current_bill_no
        date_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
        items_count = len(self.cart_items)

        item_lines = []
        for item in self.cart_items[:5]:
            item_lines.append(f"  • {item['name']} x{fmt(item['qty'])} — ₹{fmt(item['total'])}")
        if len(self.cart_items) > 5:
            item_lines.append(f"  • ...and {len(self.cart_items) - 5} more item(s)")
        items_str = "\n".join(item_lines)

        disc_line = f"\n💚 Discount saved: ₹{fmt(disc_total)}" if disc_total > 0 else ""

        msg = (
            f"🛒 *{MART_NAME}*\n"
            f"_{TAGLINE}_\n\n"
            f"Hello *{cust_name}*! 👋\n"
            f"Thank you for shopping with us.\n\n"
            f"🧾 *Bill #{bill_no}*\n"
            f"📅 {date_str}\n\n"
            f"*Items ({items_count}):*\n"
            f"{items_str}\n\n"
            f"{'─' * 28}\n"
            f"💰 *Total: ₹{fmt(grand)}*"
            f"{disc_line}\n"
            f"💳 Payment: {payment}\n"
            f"{'─' * 28}\n\n"
            f"📍 {ADDRESS}\n"
            f"📞 {PHONE}\n\n"
            f"✨ *Visit again soon!* 🙏"
        )
        return msg

    def _send_whatsapp_bill(self, phone=None, bill_text=None):
        import urllib.parse, webbrowser
        if not phone:
            phone = self.cust_phone.text().strip()
        if not phone:
            QMessageBox.warning(self, "No Phone", "Enter customer phone number first."); return

        ph = phone.replace(" ", "").replace("-", "")
        if ph.startswith("0"): ph = "91" + ph[1:]
        elif not ph.startswith("91") and len(ph) == 10: ph = "91" + ph

        if not bill_text:
            bill_text = self._build_bill_text()

        msg = f"```\n{bill_text}\n```"
        url = f"https://wa.me/{ph}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

        self._save_transaction()
        self._add_points()
        self._clear_all(skip_confirm=True)

    def _whatsapp_dialog(self):
        import urllib.parse, webbrowser

        dlg = QDialog(self)
        dlg.setWindowTitle("📱 WhatsApp Communication")
        dlg.resize(560, 720)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; }")
        content = QWidget()
        content.setStyleSheet(f"background:{C_BG};")
        l = QVBoxLayout(content)
        l.setContentsMargins(20, 18, 20, 18)
        l.setSpacing(12)
        scroll.setWidget(content)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0,0,0,0)
        outer.addWidget(scroll)

        ttl = QLabel("📱  WhatsApp Communication")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        sec1 = QFrame()
        sec1.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(37,211,102,0.12), stop:1 rgba(18,140,126,0.06));
                border: 1px solid #25D366;
                border-radius: 10px;
            }}
        """)
        s1l = QVBoxLayout(sec1)
        s1l.setContentsMargins(16, 14, 16, 14)
        s1l.setSpacing(10)

        s1_hdr = QHBoxLayout()
        s1_ttl = QLabel("📲  Quick Bill Message  (Recommended)")
        s1_ttl.setStyleSheet(f"font-size:14px;font-weight:800;color:#25D366;background:transparent;border:none;")
        s1_hdr.addWidget(s1_ttl)
        s1_hdr.addStretch()

        info_badge = QLabel("Auto-filled ✓")
        info_badge.setStyleSheet(f"""
            color:white; background:#25D366; border-radius:8px;
            padding:2px 10px; font-size:10px; font-weight:700; border:none;
        """)
        s1_hdr.addWidget(info_badge)
        s1l.addLayout(s1_hdr)

        ph_row = QHBoxLayout()
        ph_icon = QLabel("📞")
        ph_icon.setStyleSheet("font-size:16px;background:transparent;border:none;")
        ph_row.addWidget(ph_icon)
        ph_lbl2 = QLabel("Customer Phone:")
        ph_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:12px;font-weight:600;background:transparent;border:none;")
        ph_row.addWidget(ph_lbl2)
        ph_edit = QLineEdit(self.cust_phone.text().strip())
        ph_edit.setPlaceholderText("e.g. 9507695751")
        ph_edit.setFixedHeight(36)
        ph_row.addWidget(ph_edit, 1)
        s1l.addLayout(ph_row)

        msg_lbl = QLabel("MESSAGE PREVIEW  (editable)")
        msg_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        s1l.addWidget(msg_lbl)

        short_msg_edit = QTextEdit()
        short_msg_edit.setMinimumHeight(220)
        short_msg_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {C_SURFACE2};
                border: 1px solid #25D366;
                border-radius: 8px;
                color: {C_TEXT};
                font-size: 13px;
                padding: 8px;
            }}
        """)

        cname = self.cust_name.text().strip() or "Customer"
        grand,_,_ = self._get_grand_total()
        short_default = (
            f"Dear {cname},\n"
            f"Thank you for your purchase of Rs.{fmt(grand)} at Printing World.🙏\n\n"
            f"We look forward to seeing you again!\n\n"
            f"प्रिय ग्राहक,\n"
            f"रूमी मार्ट से ₹{fmt(grand)} की खरीदारी के लिए धन्यवाद। 🙏\n\n"
            f"आपका फिर से स्वागत है!"
        )
        short_msg_edit.setPlainText(short_default)
        s1l.addWidget(short_msg_edit)

        refresh_btn = QPushButton("🔄  Refresh Message")
        refresh_btn.setFixedHeight(30)
        refresh_btn.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:6px;color:{C_TEXT};font-size:11px;font-weight:600;padding:0 12px;")
        refresh_btn.clicked.connect(lambda: short_msg_edit.setPlainText(
            self._build_short_whatsapp_msg() if self.cart_items else short_msg_edit.toPlainText()
        ))
        s1l.addWidget(refresh_btn)

        send_short_btn = QPushButton("📲  Send Short Bill Message")
        send_short_btn.setFixedHeight(46)
        send_short_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #25D366,stop:1 #128C7E);
                border:none; border-radius:10px; color:white; font-weight:800; font-size:14px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{ border:2px solid white; background:#128C7E; }}
            QPushButton:pressed {{ background:#075e54; }}
        """)
        s1l.addWidget(send_short_btn)
        l.addWidget(sec1)

        sec2 = QFrame()
        sec2.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        s2l = QVBoxLayout(sec2)
        s2l.setContentsMargins(14, 12, 14, 12)
        s2l.setSpacing(8)

        s2_ttl = QLabel("🧾  Send Full Thermal Bill")
        s2_ttl.setStyleSheet(f"font-size:13px;font-weight:800;color:#4fc3f7;background:transparent;border:none;")
        s2l.addWidget(s2_ttl)

        s2_note = QLabel("Sends complete bill in courier/fixed-width format (like thermal print receipt)")
        s2_note.setStyleSheet(f"color:{C_MUTED};font-size:11px;background:transparent;border:none;")
        s2_note.setWordWrap(True)
        s2l.addWidget(s2_note)

        send_full_btn = QPushButton("🧾  Send Full Thermal Bill")
        send_full_btn.setFixedHeight(42)
        send_full_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4fc3f7,stop:1 #0288d1);
                border:none; border-radius:9px; color:white; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ border:2px solid white; background:#0288d1; }}
        """)
        s2l.addWidget(send_full_btn)
        l.addWidget(sec2)

        sec3 = QFrame()
        sec3.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        s3l = QVBoxLayout(sec3)
        s3l.setContentsMargins(14, 12, 14, 12)
        s3l.setSpacing(8)

        s3_ttl = QLabel("💬  Custom Message")
        s3_ttl.setStyleSheet(f"font-size:13px;font-weight:800;color:#ce93d8;background:transparent;border:none;")
        s3l.addWidget(s3_ttl)

        custom_msg_edit = QTextEdit()
        custom_msg_edit.setPlaceholderText(
            f"Type any custom message here…\n\nExample:\nHello! We have a special offer this weekend. 🎉\nVisit {MART_NAME} and get 10% off!"
        )
        custom_msg_edit.setMaximumHeight(90)
        s3l.addWidget(custom_msg_edit)

        send_custom_btn = QPushButton("💬  Send Custom Message")
        send_custom_btn.setFixedHeight(40)
        send_custom_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ce93d8,stop:1 #8e24aa);
                border:none; border-radius:9px; color:white; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ border:2px solid white; background:#8e24aa; }}
        """)
        s3l.addWidget(send_custom_btn)
        l.addWidget(sec3)

        note = QLabel("ℹ️  All buttons open WhatsApp Web in your browser. Make sure you are logged in to WhatsApp Web.")
        note.setStyleSheet(f"color:{C_MUTED};font-size:11px;background:transparent;border:none;")
        note.setWordWrap(True)
        l.addWidget(note)

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)

        def _get_phone():
            p = ph_edit.text().strip()
            if not p:
                QMessageBox.warning(dlg, "No Phone", "Enter customer phone number first.")
                return None
            ph2 = p.replace(" ","").replace("-","")
            if ph2.startswith("0"): ph2 = "91" + ph2[1:]
            elif not ph2.startswith("91") and len(ph2) == 10: ph2 = "91" + ph2
            return ph2

        def send_short():
            ph2 = _get_phone()
            if not ph2: return
            msg = short_msg_edit.toPlainText().strip()
            if not msg:
                QMessageBox.warning(dlg, "Empty", "Message is empty."); return
            url = f"https://wa.me/{ph2}?text={urllib.parse.quote(msg)}"
            webbrowser.open(url)
            dlg.accept()

        def send_full():
            if "DUE" in self._get_payment():
                if not self.cust_phone.text().strip() or not self.cust_name.text().strip():
                    QMessageBox.warning(dlg, "Missing", "Enter customer name and phone for DUE!"); return
                self._add_to_dues()
                dlg.accept()
                return
            ph2 = _get_phone()
            if not ph2: return
            if not self.cart_items:
                QMessageBox.warning(dlg, "Empty Cart", "No items in cart."); return
            bill_text = self._build_bill_text()
            msg = f"```\n{bill_text}\n```"
            url = f"https://wa.me/{ph2}?text={urllib.parse.quote(msg)}"
            webbrowser.open(url)
            self._save_transaction()
            self._add_points()
            self._clear_all(skip_confirm=True)
            dlg.accept()

        def send_custom():
            ph2 = _get_phone()
            if not ph2: return
            msg = custom_msg_edit.toPlainText().strip()
            if not msg:
                QMessageBox.warning(dlg, "Empty", "Enter a message first."); return
            url = f"https://wa.me/{ph2}?text={urllib.parse.quote(msg)}"
            webbrowser.open(url)
            dlg.accept()

        send_short_btn.clicked.connect(send_short)
        send_full_btn.clicked.connect(send_full)
        send_custom_btn.clicked.connect(send_custom)

        dlg.exec()

    def _show_dashboard(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Dashboard")
        dlg.resize(900, 650)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(12)

        ttl = QLabel("🏠  Today's Dashboard")
        ttl.setStyleSheet(f"font-size:20px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        today = date.today().isoformat()
        sd = load_sales()
        d = sd.get(today, {})

        bills = d.get('bill_count', 0)
        total = d.get('total', 0)
        txs   = d.get('transactions', [])

        hours_sales = [0] * 24
        for tx in txs:
            try:
                h = int(datetime.strptime(tx['time'], "%I:%M %p").strftime("%H"))
                hours_sales[h] += tx.get('amount', 0)
            except Exception:
                pass
        max_sale = max(hours_sales) if max(hours_sales) > 0 else 1
        now_h = datetime.now().hour

        chart_frame = QFrame()
        chart_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:9px;")
        chart_frame.setMaximumHeight(110)
        cf_l = QVBoxLayout(chart_frame)
        cf_l.setContentsMargins(12, 8, 12, 8)
        cf_l.setSpacing(4)
        chart_lbl = QLabel("⏰  Hourly Sales Today  (★ = current hour)")
        chart_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;background:transparent;border:none;")
        cf_l.addWidget(chart_lbl)

        bar_row = QHBoxLayout()
        bar_row.setSpacing(2)
        BAR_MAX = 50
        for h in range(7, 23):
            col_w = QWidget(); col_w.setStyleSheet("background:transparent;")
            cl = QVBoxLayout(col_w); cl.setContentsMargins(0,0,0,0); cl.setSpacing(1)
            is_now = (h == now_h)
            bar_color = "#ffd54f" if is_now else "#7c6aff"
            bar_h = max(3, int(hours_sales[h] / max_sale * BAR_MAX))
            spacer = QWidget(); spacer.setFixedHeight(BAR_MAX - bar_h)
            spacer.setStyleSheet("background:transparent;")
            bar = QFrame(); bar.setFixedWidth(13); bar.setFixedHeight(bar_h)
            bar.setStyleSheet(f"background:{bar_color};border-radius:3px;border:none;")
            t_lbl = QLabel("★" if is_now else f"{h%12 or 12}")
            t_lbl.setStyleSheet(f"color:{'#ffd54f' if is_now else C_MUTED};font-size:7px;background:transparent;border:none;")
            t_lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(spacer); cl.addWidget(bar); cl.addWidget(t_lbl)
            bar_row.addWidget(col_w)
        cf_l.addLayout(bar_row)
        l.addWidget(chart_frame)

        low = [(c, p['name'], float(p['stock'])) for c, p in self.products.items() if float(p['stock']) <= 2]
        low_hdr = QLabel(f"⚠️  Low Stock Items  ({len(low)} products ≤ 2 units)")
        low_hdr.setStyleSheet(f"font-size:13px;font-weight:700;color:#ffd54f;margin-top:4px;")
        l.addWidget(low_hdr)

        if low:
            low_table = QTableWidget(0, 3)
            low_table.setHorizontalHeaderLabels(["CODE", "PRODUCT NAME", "STOCK"])
            low_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            low_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            low_table.verticalHeader().setVisible(False)
            low_table.setAlternatingRowColors(True)
            low_table.setMaximumHeight(180)
            low_table.setColumnWidth(0, 80)
            low_table.setColumnWidth(2, 70)
            for code, name, stock in sorted(low, key=lambda x: x[2]):
                r = low_table.rowCount()
                low_table.insertRow(r)
                for ci, val in enumerate([code, name, fmt(stock)]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter if ci != 1 else (Qt.AlignLeft | Qt.AlignVCenter))
                    if ci == 2:
                        itm.setForeground(QColor("#ef5350" if stock == 0 else "#ffd54f"))
                        itm.setFont(QFont("Segoe UI", 11, QFont.Bold))
                    low_table.setItem(r, ci, itm)
            l.addWidget(low_table)
        else:
            ok_lbl = QLabel("✅  All products are well stocked!")
            ok_lbl.setStyleSheet(f"color:#69f0ae;font-size:12px;")
            l.addWidget(ok_lbl)

        if txs:
            tx_lbl = QLabel("📋  Recent Transactions Today:")
            tx_lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
            l.addWidget(tx_lbl)

            tx_table = QTableWidget(0, 5)
            tx_table.setHorizontalHeaderLabels(["Time", "Bill#", "Customer", "Payment", "Amount"])
            tx_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            tx_table.setColumnWidth(0, 68)
            tx_table.setColumnWidth(1, 78)
            tx_table.setColumnWidth(2, 90)
            tx_table.setColumnWidth(4, 75)
            tx_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tx_table.verticalHeader().setVisible(False)
            tx_table.setAlternatingRowColors(True)
            tx_table.setMaximumHeight(160)

            for tx in reversed(txs[-10:]):
                r = tx_table.rowCount()
                tx_table.insertRow(r)
                for col, val in enumerate([
                    tx.get('time',''), tx.get('bill_no',''),
                    tx.get('customer',''), tx.get('payment',''),
                    f"₹{fmt(tx.get('amount',0))}"
                ]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter)
                    tx_table.setItem(r, col, itm)
            l.addWidget(tx_table)

        close_btn = QPushButton("✕  Close")
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet(f"background:#b71c1c;border:none;border-radius:7px;color:white;font-weight:700;")
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _manage_products(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Product Inventory")
        dlg.resize(1000, 620)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(10)

        ttl = QLabel("📦  Product Inventory")
        ttl.setStyleSheet(f"font-size:20px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        search_row = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("🔍  Search products...")
        search_edit.setFixedHeight(36)
        search_edit.setMaximumWidth(300)
        search_row.addWidget(search_edit)
        search_row.addStretch()

        def export_csv():
            path, _ = QFileDialog.getSaveFileName(dlg, "Export Inventory", "inventory.csv", "CSV Files (*.csv)")
            if path:
                try:
                    with open(path, 'w', newline='', encoding='utf-8') as f:
                        w = csv.writer(f)
                        w.writerow(["Code", "Name", "MRP", "Price", "Stock"])
                        for code, p in self.products.items():
                            w.writerow([code, p['name'], p['mrp'], p['price'], p['stock']])
                    QMessageBox.information(dlg, "✅ Exported", f"Inventory exported to:\n{path}")
                except Exception as ex:
                    QMessageBox.warning(dlg, "Error", str(ex))

        def import_csv():
            path, _ = QFileDialog.getOpenFileName(dlg, "Import Inventory", "", "CSV Files (*.csv)")
            if path:
                try:
                    with open(path, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        count = 0
                        for row in reader:
                            code = row.get('Code','').strip()
                            name = row.get('Name','').strip()
                            if not code or not name: continue
                            self.products[code] = {
                                "name": name,
                                "mrp":   float(row.get('MRP',0) or 0),
                                "price": float(row.get('Price',0) or 0),
                                "stock": float(row.get('Stock',0) or 0),
                            }
                            count += 1
                        save_products(self.products)
                        refresh()
                        QMessageBox.information(dlg, "✅ Imported", f"Imported {count} products.")
                except Exception as ex:
                    QMessageBox.warning(dlg, "Error", str(ex))

        imp_btn = QPushButton("📥 Import CSV")
        imp_btn.setFixedHeight(34)
        imp_btn.setStyleSheet(f"background:#0288d1;border:none;border-radius:7px;color:white;font-weight:700;padding:0 12px;")
        imp_btn.clicked.connect(import_csv)
        search_row.addWidget(imp_btn)

        exp_btn = QPushButton("📤 Export CSV")
        exp_btn.setFixedHeight(34)
        exp_btn.setStyleSheet(f"background:#009e76;border:none;border-radius:7px;color:white;font-weight:700;padding:0 12px;")
        exp_btn.clicked.connect(export_csv)
        search_row.addWidget(exp_btn)

        l.addLayout(search_row)

        body = QHBoxLayout()
        body.setSpacing(12)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["CODE", "NAME", "MRP", "PRICE", "STOCK"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setColumnWidth(0, 80)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 80)
        table.setColumnWidth(4, 80)
        body.addWidget(table, 3)

        form_frame = QFrame()
        form_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        form_frame.setFixedWidth(260)
        fl = QVBoxLayout(form_frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(8)

        form_ttl = QLabel("ADD / EDIT PRODUCT")
        form_ttl.setStyleSheet(f"""
            font-size:13px;font-weight:800;color:white;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ff8a65,stop:1 #e64a19);
            border-radius:7px;padding:6px 12px;
        """)
        fl.addWidget(form_ttl)

        entries = {}
        for label, key in [("Barcode/Code", "code"), ("Name", "name"),
                            ("MRP", "mrp"), ("Sell Price", "price"), ("Stock", "stock")]:
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:2px;")
            fl.addWidget(lbl)
            e = QLineEdit()
            e.setFixedHeight(34)
            fl.addWidget(e)
            entries[key] = e

        status_lbl = QLabel("")
        status_lbl.setStyleSheet(f"color:#69f0ae;font-size:11px;background:transparent;border:none;")
        status_lbl.setWordWrap(True)
        fl.addWidget(status_lbl)

        def refresh(q=""):
            table.setRowCount(0)
            ql = q.lower().strip()
            for code, p in self.products.items():
                if ql and ql not in code.lower() and ql not in p['name'].lower():
                    continue
                r = table.rowCount()
                table.insertRow(r)
                for col, val in enumerate([code, p['name'], fmt(p['mrp']), fmt(p['price']), fmt(p['stock'])]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    if col == 1: item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    table.setItem(r, col, item)

        def on_code_edit():
            code = entries['code'].text().strip()
            if code in self.products:
                p = self.products[code]
                entries['name'].setText(p['name'])
                entries['mrp'].setText(fmt(p['mrp']))
                entries['price'].setText(fmt(p['price']))
                entries['stock'].setText(fmt(p['stock']))
                status_lbl.setText("✅ Product found — edit & save")
                status_lbl.setStyleSheet("color:#69f0ae;font-size:11px;background:transparent;border:none;")
                entries['stock'].setFocus()
                entries['stock'].selectAll()
            else:
                if code:
                    status_lbl.setText("🆕 New product — fill details below")
                    status_lbl.setStyleSheet(f"color:#ffd54f;font-size:11px;background:transparent;border:none;")
                    entries['name'].setFocus()

        entries['code'].returnPressed.connect(on_code_edit)

        def on_select():
            rows = table.selectedItems()
            if not rows: return
            code = table.item(table.currentRow(), 0).text()
            p = self.products.get(code, {})
            entries['code'].setText(code)
            entries['name'].setText(p.get('name',''))
            entries['mrp'].setText(fmt(p.get('mrp',0)))
            entries['price'].setText(fmt(p.get('price',0)))
            entries['stock'].setText(fmt(p.get('stock',0)))

        table.itemSelectionChanged.connect(on_select)
        search_edit.textChanged.connect(lambda t: refresh(t))
        refresh()

        def clear_form():
            for e in entries.values(): e.clear()
            status_lbl.setText("")
            entries['code'].setFocus()

        def save_product():
            code = entries['code'].text().strip()
            name = entries['name'].text().strip()
            mrp_txt   = entries['mrp'].text().strip()
            price_txt = entries['price'].text().strip()
            stock_txt = entries['stock'].text().strip()
            try:
                mrp   = float(mrp_txt) if mrp_txt else 0.0
                price = float(price_txt) if price_txt else 0.0
                stock = float(stock_txt) if stock_txt else 0.0
            except ValueError:
                status_lbl.setText("Enter valid numbers!"); status_lbl.setStyleSheet("color:#ef5350;font-size:11px;")
                return
            if not code or not name:
                status_lbl.setText("Code and Name required!"); return
            self.products[code] = {"name": name, "mrp": mrp, "price": price, "stock": stock}
            save_products(self.products)
            refresh(search_edit.text())
            clear_form()
            status_lbl.setText(f"✅ Saved: {name}"); status_lbl.setStyleSheet(f"color:#69f0ae;font-size:11px;")

        def delete_product():
            rows = table.selectedItems()
            if not rows: return
            code = table.item(table.currentRow(), 0).text()
            if QMessageBox.question(dlg, "Confirm", f"Delete product '{code}'?") == QMessageBox.Yes:
                del self.products[code]
                save_products(self.products)
                refresh(search_edit.text())

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾  Save")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00c896,stop:1 #009e76);
                border:none; border-radius:8px; color:white; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ background:#009e76; border:2px solid white; }}
        """)
        save_btn.clicked.connect(save_product)
        btn_row.addWidget(save_btn)

        del_btn = QPushButton("🗑  Delete")
        del_btn.setFixedHeight(38)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
                border:none; border-radius:8px; color:white; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ background:#b71c1c; border:2px solid white; }}
        """)
        del_btn.clicked.connect(delete_product)
        btn_row.addWidget(del_btn)
        fl.addLayout(btn_row)

        clr_btn = QPushButton("🧹 Clear Form")
        clr_btn.setFixedHeight(34)
        clr_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE2}; border:1px solid {C_BORDER};
                border-radius:7px; color:{C_TEXT}; font-weight:600;
            }}
            QPushButton:hover {{ border-color:{C_ACCENT}; }}
        """)
        clr_btn.clicked.connect(clear_form)
        fl.addWidget(clr_btn)
        fl.addStretch()

        entries['name'].returnPressed.connect(lambda: entries['mrp'].setFocus())
        entries['mrp'].returnPressed.connect(lambda: entries['price'].setFocus())
        entries['price'].returnPressed.connect(lambda: entries['stock'].setFocus())
        entries['stock'].returnPressed.connect(save_product)

        for ib in [imp_btn, exp_btn, save_btn, del_btn, clr_btn]:
            ib.setAutoDefault(False)
            ib.setDefault(False)
            ib.setFocusPolicy(Qt.NoFocus)

        body.addWidget(form_frame)
        l.addLayout(body)

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _manage_customers(self):
        self.customers = load_customers()
        dlg = CustomerDialog(self.customers, self)
        dlg.exec()
        self.customers = load_customers()

    def _manage_dues(self):
        dues = load_dues()
        dlg = QDialog(self)
        dlg.setWindowTitle("Dues / Credit Management")
        dlg.resize(880, 580)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(10)

        hdr_row = QHBoxLayout()
        ttl = QLabel("💳  Dues / Credit Management")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        hdr_row.addWidget(ttl)
        hdr_row.addStretch()
        total_outstanding = sum(float(d.get("total_due", 0)) for d in dues.values())
        tot_lbl = QLabel(f"Total Outstanding: Rs.{fmt(total_outstanding)}")
        tot_lbl.setStyleSheet(f"color:#ef5350;font-size:14px;font-weight:800;background:transparent;border:none;")
        hdr_row.addWidget(tot_lbl)
        l.addLayout(hdr_row)

        body = QHBoxLayout()
        body.setSpacing(12)

        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(6)

        srch = QLineEdit()
        srch.setPlaceholderText("🔍 Search customer...")
        srch.setFixedHeight(34)
        left_l.addWidget(srch)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["CUSTOMER", "PHONE", "TOTAL DUE", "LAST BILL"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setColumnWidth(1, 110)
        table.setColumnWidth(2, 90)
        table.setColumnWidth(3, 110)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        left_l.addWidget(table, 1)
        body.addWidget(left_w, 2)

        right_w = QFrame()
        right_w.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        right_w.setFixedWidth(300)
        rw_l = QVBoxLayout(right_w)
        rw_l.setContentsMargins(14, 14, 14, 14)
        rw_l.setSpacing(8)

        det_ttl = QLabel("Transaction History")
        det_ttl.setStyleSheet(f"""
            font-size:13px;font-weight:800;color:white;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
            border-radius:7px;padding:6px 12px;
        """)
        rw_l.addWidget(det_ttl)

        self._due_name_lbl  = QLabel("—")
        self._due_name_lbl.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:700;background:transparent;border:none;")
        self._due_total_lbl = QLabel("Outstanding: Rs.0")
        self._due_total_lbl.setStyleSheet(f"color:#ef5350;font-size:13px;font-weight:700;background:transparent;border:none;")
        rw_l.addWidget(self._due_name_lbl)
        rw_l.addWidget(self._due_total_lbl)

        tx_table = QTableWidget(0, 3)
        tx_table.setHorizontalHeaderLabels(["Date", "Bill#", "Amount"])
        tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tx_table.setColumnWidth(1, 70)
        tx_table.setColumnWidth(2, 70)
        tx_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tx_table.verticalHeader().setVisible(False)
        tx_table.setAlternatingRowColors(True)
        tx_table.setMaximumHeight(220)
        rw_l.addWidget(tx_table)

        part_lbl = QLabel("RECORD PAYMENT")
        part_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
        rw_l.addWidget(part_lbl)

        pay_row = QHBoxLayout()
        pay_amt_edit = QLineEdit()
        pay_amt_edit.setPlaceholderText("Amount paid")
        pay_amt_edit.setFixedHeight(32)
        pay_row.addWidget(pay_amt_edit)

        pay_btn = QPushButton("✅ Pay")
        pay_btn.setFixedHeight(32)
        pay_btn.setFixedWidth(60)
        pay_btn.setStyleSheet(f"background:#00c896;border:none;border-radius:7px;color:white;font-weight:700;")
        pay_row.addWidget(pay_btn)
        rw_l.addLayout(pay_row)

        mark_all_btn = QPushButton("✅ Mark All as Paid")
        mark_all_btn.setFixedHeight(34)
        mark_all_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00c896,stop:1 #009e76);
                border:none;border-radius:7px;color:white;font-weight:700;font-size:12px;
            }}
            QPushButton:hover {{ background:#009e76; }}
        """)
        rw_l.addWidget(mark_all_btn)
        rw_l.addStretch()
        body.addWidget(right_w)
        l.addLayout(body, 1)

        def refresh_table(q=""):
            fresh = load_dues()
            table.setRowCount(0)
            ql = q.lower()
            for phone, data in fresh.items():
                if ql and ql not in data.get("name","").lower() and ql not in phone:
                    continue
                last = data["transactions"][-1]["date"] if data["transactions"] else "—"
                amt  = float(data.get("total_due", 0))
                r = table.rowCount()
                table.insertRow(r)
                for col, val in enumerate([data['name'], phone, f"Rs.{fmt(amt)}", last]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    if col == 2:
                        item.setForeground(QColor("#ef5350" if amt > 0 else "#69f0ae"))
                        item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                    table.setItem(r, col, item)
            total_outstanding = sum(float(d.get("total_due", 0)) for d in fresh.values())
            tot_lbl.setText(f"Total Outstanding: Rs.{fmt(total_outstanding)}")

        def on_select():
            row = table.currentRow()
            if row < 0:
                return
            phone = table.item(row, 1).text()
            data  = dues.get(phone, {})
            self._due_name_lbl.setText(data.get("name", "—"))
            amt = float(data.get("total_due", 0))
            self._due_total_lbl.setText(f"Outstanding: Rs.{fmt(amt)}")
            tx_table.setRowCount(0)
            for tx in reversed(data.get("transactions", [])):
                r = tx_table.rowCount()
                tx_table.insertRow(r)
                status_suffix = " ✓" if tx.get("status") == "paid" else ""
                for ci, val in enumerate([tx.get("date",""), tx.get("bill_no",""),
                                           f"Rs.{fmt(tx.get('amount',0))}{status_suffix}"]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter)
                    if ci == 2:
                        itm.setForeground(QColor("#69f0ae" if tx.get("status") == "paid" else "#ef5350"))
                    tx_table.setItem(r, ci, itm)

        def partial_pay():
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(dlg, "Select", "Select a customer first."); return
            phone = table.item(row, 1).text()
            try:
                amt_paid = float(pay_amt_edit.text())
            except ValueError:
                QMessageBox.warning(dlg, "Invalid", "Enter a valid amount."); return
            if phone in dues:
                dues[phone]["total_due"] = round(max(0, float(dues[phone]["total_due"]) - amt_paid), 2)
                dues[phone]["transactions"].append({
                    "date":    datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "bill_no": "PAYMENT",
                    "amount":  -amt_paid,
                    "status":  "paid"
                })
                save_dues(dues)
                pay_amt_edit.clear()
                refresh_table(srch.text())
                on_select()
                QMessageBox.information(dlg, "Recorded", f"Payment of Rs.{fmt(amt_paid)} recorded.")

        def mark_all_paid():
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(dlg, "Select", "Select a customer."); return
            phone = table.item(row, 1).text()
            if phone in dues:
                amt = dues[phone]['total_due']
                if QMessageBox.question(dlg, "Confirm",
                        f"Mark Rs.{fmt(amt)} as fully paid for {dues[phone]['name']}?") == QMessageBox.Yes:
                    dues[phone]['total_due'] = 0.0
                    for t in dues[phone]['transactions']:
                        t['status'] = 'paid'
                    save_dues(dues)
                    refresh_table(srch.text())
                    on_select()
                    QMessageBox.information(dlg, "Done", "Marked as fully paid!")

        table.itemSelectionChanged.connect(on_select)
        srch.textChanged.connect(lambda t: refresh_table(t))
        pay_btn.clicked.connect(partial_pay)
        mark_all_btn.clicked.connect(mark_all_paid)
        pay_amt_edit.returnPressed.connect(partial_pay)

        refresh_table()

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
                border:none;border-radius:8px;color:white;font-weight:800;font-size:13px;padding:0 24px;
            }}
            QPushButton:hover {{ background:#b71c1c; }}
        """)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _manage_purchases(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Purchases")
        dlg.resize(1100, 720)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet(f"background:{C_SURFACE};border-bottom:1px solid {C_BORDER};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(20, 14, 20, 14)
        ttl = QLabel("🛒  Purchase Management")
        ttl.setStyleSheet(f"font-size:20px;font-weight:800;color:{C_TEXT};")
        hdr_l.addWidget(ttl)
        hdr_l.addStretch()
        l.addWidget(hdr)

        tabs = QTabWidget()
        l.addWidget(tabs)

        new_w = QWidget()
        new_l = QVBoxLayout(new_w)
        new_l.setContentsMargins(16, 14, 16, 14)
        new_l.setSpacing(10)

        sup_frame = QFrame()
        sup_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        sup_fl = QVBoxLayout(sup_frame)
        sup_fl.setContentsMargins(16, 12, 16, 12)
        sup_fl.setSpacing(8)

        sup_head = QLabel("SUPPLIER DETAILS")
        sup_head.setStyleSheet(f"""
            font-size:12px;font-weight:800;color:white;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00c896,stop:1 #009e76);
            border-radius:6px;padding:5px 12px;
        """)
        sup_fl.addWidget(sup_head)

        sup_row = QHBoxLayout()
        sup_row.setSpacing(12)
        sup_entries = {}
        for lbl, key, ph, w in [
            ("Seller Name", "seller", "Required", 200),
            ("Phone",       "phone",  "Optional", 140),
            ("Invoice No.", "invoice","Optional", 130),
            ("GST Rate %",  "gst",    "5",        70),
        ]:
            col_w = QWidget()
            col_l = QVBoxLayout(col_w)
            col_l.setContentsMargins(0, 0, 0, 0)
            col_l.setSpacing(3)
            ql = QLabel(lbl.upper())
            ql.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
            col_l.addWidget(ql)
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(34)
            e.setMaximumWidth(w)
            if key == "gst": e.setText("5")
            col_l.addWidget(e)
            sup_entries[key] = e
            sup_row.addWidget(col_w)
        sup_row.addStretch()
        sup_fl.addLayout(sup_row)
        new_l.addWidget(sup_frame)

        items_head_row = QHBoxLayout()
        items_ttl = QLabel("ITEMS")
        items_ttl.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
        items_head_row.addWidget(items_ttl)
        items_head_row.addStretch()

        add_row_btn = QPushButton("➕ Add Row")
        add_row_btn.setFixedHeight(32)
        add_row_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
                border:none;border-radius:7px;color:white;font-weight:700;padding:0 14px;
            }}
            QPushButton:hover {{ background:#5a49d0; }}
        """)
        items_head_row.addWidget(add_row_btn)
        new_l.addLayout(items_head_row)

        item_table = QTableWidget(0, 7)
        item_table.setHorizontalHeaderLabels(["Code", "Product Name", "Qty", "Cost ₹", "MRP ₹", "Tax ₹", "Total ₹"])
        item_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        item_table.setAlternatingRowColors(True)
        item_table.verticalHeader().setVisible(False)
        item_table.setColumnWidth(0, 90)
        item_table.setColumnWidth(2, 60)
        item_table.setColumnWidth(3, 80)
        item_table.setColumnWidth(4, 80)
        item_table.setColumnWidth(5, 80)
        item_table.setColumnWidth(6, 90)
        new_l.addWidget(item_table, 1)

        p_rows_data = []

        def add_pur_row():
            r = item_table.rowCount()
            item_table.insertRow(r)
            item_table.setRowHeight(r, 36)
            widgets = {}
            for col, (key, ph, w_) in enumerate([
                ("code", "Code", 86),
                ("name", "Product Name", 0),
                ("qty",  "Qty", 56),
                ("cost", "Cost ₹", 76),
                ("mrp",  "MRP ₹", 76),
            ]):
                e = QLineEdit()
                e.setPlaceholderText(ph)
                e.setFixedHeight(30)
                if key == "qty": e.setText("1")
                e.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:5px;color:{C_TEXT};padding:0 5px;")
                item_table.setCellWidget(r, col, e)
                widgets[key] = e

            for col, key in [(5, "tax"), (6, "total")]:
                lbl_w = QLabel("0.00")
                lbl_w.setAlignment(Qt.AlignCenter)
                lbl_w.setStyleSheet(f"color:{C_TEXT};font-weight:700;font-size:12px;background:transparent;")
                item_table.setCellWidget(r, col, lbl_w)
                widgets[key] = lbl_w

            p_rows_data.append(widgets)

            def recalc(*_):
                try:
                    qty  = float(widgets['qty'].text() or 1)
                    cost = float(widgets['cost'].text() or 0)
                    gst  = float(sup_entries['gst'].text() or 0)
                    tax  = cost * qty * gst / 100
                    total = cost * qty + tax
                    widgets['tax'].setText(f"₹{fmt(tax)}")
                    widgets['total'].setText(f"₹{fmt(total)}")
                except ValueError:
                    pass

            def autofill():
                code = widgets['code'].text().strip()
                if code in self.products:
                    p = self.products[code]
                    widgets['name'].setText(p['name'])
                    widgets['mrp'].setText(fmt(p['mrp']))
                    widgets['qty'].setFocus()
                    widgets['qty'].selectAll()
                recalc()

            widgets['code'].editingFinished.connect(autofill)
            widgets['code'].returnPressed.connect(lambda: widgets['name'].setFocus())
            widgets['name'].returnPressed.connect(lambda: widgets['qty'].setFocus())
            widgets['qty'].returnPressed.connect(lambda: widgets['cost'].setFocus())
            widgets['cost'].returnPressed.connect(lambda: widgets['mrp'].setFocus())
            for k in ('qty', 'cost', 'mrp'):
                widgets[k].textChanged.connect(recalc)

            widgets['code'].setFocus()

        grand_row = QHBoxLayout()
        grand_row.addStretch()
        grand_lbl = QLabel("GRAND TOTAL: ₹0.00")
        grand_lbl.setStyleSheet(f"color:white;font-size:16px;font-weight:800;background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);border-radius:8px;padding:8px 18px;")
        grand_row.addWidget(grand_lbl)
        new_l.addLayout(grand_row)

        def update_grand():
            total = 0.0
            for wr in p_rows_data:
                try:
                    txt = wr['total'].text().replace("₹","").strip()
                    total += float(txt) if txt else 0
                except: pass
            grand_lbl.setText(f"GRAND TOTAL: ₹{fmt(total)}")

        def add_row_with_grand():
            add_pur_row()
            for wr in p_rows_data[-1:]:
                for k in ('qty','cost','mrp'):
                    wr[k].textChanged.connect(update_grand)
        add_row_btn.clicked.connect(add_row_with_grand)
        add_pur_row()
        for wr in p_rows_data:
            for k in ('qty','cost','mrp'):
                wr[k].textChanged.connect(update_grand)

        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()

        def save_purchase():
            seller = sup_entries['seller'].text().strip()
            if not seller:
                QMessageBox.warning(dlg, "Missing", "Enter seller name."); return
            try:
                gst_r = float(sup_entries['gst'].text() or 0)
            except ValueError:
                gst_r = 0

            purchases = load_purchases()
            txn_items = []
            grand = 0.0

            for wr in p_rows_data:
                code = wr['code'].text().strip()
                name = wr['name'].text().strip()
                if not code or not name: continue
                try:
                    qty  = float(wr['qty'].text() or 0)
                    cost = float(wr['cost'].text() or 0)
                    mrp  = float(wr['mrp'].text() or 0)
                except ValueError:
                    continue
                if qty <= 0: continue
                tax   = cost * qty * gst_r / 100
                total = cost * qty + tax
                grand += total
                txn_items.append({"code":code,"name":name,"qty":qty,"cost":cost,"mrp":mrp,"tax":tax,"total":total})
                if code in self.products:
                    self.products[code]['stock'] = float(self.products[code]['stock']) + qty
                    if mrp > 0: self.products[code]['mrp'] = mrp
                else:
                    self.products[code] = {"name":name,"mrp":mrp,"price":round(cost*1.1,2),"stock":qty}

            if not txn_items:
                QMessageBox.warning(dlg, "No Items", "Add at least one valid item."); return
            save_products(self.products)
            purchases.append({
                "date":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                "seller":  seller,
                "phone":   sup_entries['phone'].text().strip(),
                "invoice": sup_entries['invoice'].text().strip(),
                "gst_rate": gst_r, "items": txn_items, "grand": grand
            })
            save_purchases(purchases)
            QMessageBox.information(dlg, "✅ Saved",
                f"Purchase saved!\nSeller: {seller}\nItems: {len(txn_items)}\nTotal: ₹{fmt(grand)}")
            dlg.accept()

        save_btn2 = QPushButton("💾  Save & Update Stock")
        save_btn2.setFixedHeight(40)
        save_btn2.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00c896,stop:1 #009e76);
                border:none;border-radius:9px;color:white;font-weight:800;font-size:14px;padding:0 24px;
            }}
            QPushButton:hover {{ background:#009e76; }}
        """)
        save_btn2.clicked.connect(save_purchase)
        btn_row2.addWidget(save_btn2)

        cancel_btn = QPushButton("✕  Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
                border:none;border-radius:9px;color:white;font-weight:800;font-size:14px;padding:0 20px;
            }}
            QPushButton:hover {{ background:#b71c1c; }}
        """)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row2.addWidget(cancel_btn)
        new_l.addLayout(btn_row2)

        tabs.addTab(new_w, "➕  New Purchase")

        hist_w = QWidget()
        hist_l = QVBoxLayout(hist_w)
        hist_l.setContentsMargins(16, 14, 16, 14)
        hist_l.setSpacing(10)

        purchases_all = load_purchases()
        total_purch = sum(p.get('grand', 0) for p in purchases_all)
        this_month = datetime.now().strftime("%Y-%m")
        month_purch = sum(p.get('grand', 0) for p in purchases_all if p.get('date','').startswith(this_month))

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        for icon, val, lbl, c1, c2 in [
            ("🧾", str(len(purchases_all)),  "Total Bills",    "#7c6aff", "#5a49d0"),
            ("💰", f"₹{fmt(total_purch)}",   "Total Spent",    "#00c896", "#009e76"),
            ("📅", f"₹{fmt(month_purch)}",   "This Month",     "#ff8a65", "#e64a19"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});
                    border-radius:10px;border:none;
                }}
            """)
            cl_l = QVBoxLayout(card)
            cl_l.setContentsMargins(16, 10, 16, 10)
            vl = QLabel(val)
            vl.setStyleSheet(f"color:white;font-size:18px;font-weight:800;background:transparent;border:none;")
            vl.setAlignment(Qt.AlignCenter)
            cl_l.addWidget(vl)
            sl = QLabel(f"{icon} {lbl}")
            sl.setStyleSheet(f"color:rgba(255,255,255,0.85);font-size:11px;font-weight:600;background:transparent;border:none;")
            sl.setAlignment(Qt.AlignCenter)
            cl_l.addWidget(sl)
            stats_row.addWidget(card)
        hist_l.addLayout(stats_row)

        hist_table = QTableWidget(0, 6)
        hist_table.setHorizontalHeaderLabels(["Date", "Seller", "Invoice", "Items", "GST %", "Total ₹"])
        hist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        hist_table.setAlternatingRowColors(True)
        hist_table.verticalHeader().setVisible(False)
        hist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hist_l.addWidget(hist_table, 1)

        for pur in reversed(purchases_all):
            r = hist_table.rowCount()
            hist_table.insertRow(r)
            for col, val in enumerate([
                pur.get("date","—"), pur.get("seller","—"), pur.get("invoice","—"),
                str(len(pur.get("items",[]))), f"{pur.get('gst_rate',0):.0f}%",
                f"₹{fmt(pur.get('grand',0))}"
            ]):
                itm = QTableWidgetItem(val)
                itm.setTextAlignment(Qt.AlignCenter)
                if col == 5:
                    itm.setForeground(QColor("#69f0ae"))
                hist_table.setItem(r, col, itm)

        detail_lbl2 = QLabel("Select a row to view items")
        detail_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        hist_l.addWidget(detail_lbl2)

        detail_table = QTableWidget(0, 5)
        detail_table.setHorizontalHeaderLabels(["Code", "Product", "Qty", "Cost", "Total"])
        detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        detail_table.setMaximumHeight(150)
        detail_table.verticalHeader().setVisible(False)
        hist_l.addWidget(detail_table)

        def show_detail():
            row = hist_table.currentRow()
            if row < 0: return
            idx = len(purchases_all) - 1 - row
            pur = purchases_all[idx]
            detail_table.setRowCount(0)
            detail_lbl2.setText(f"Items in: {pur.get('seller','?')} — {pur.get('date','')}")
            for item in pur.get("items", []):
                r = detail_table.rowCount()
                detail_table.insertRow(r)
                for col, val in enumerate([
                    item.get('code',''), item.get('name',''),
                    fmt(item.get('qty',0)), f"₹{fmt(item.get('cost',0))}",
                    f"₹{fmt(item.get('total',0))}"
                ]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter)
                    detail_table.setItem(r, col, itm)

        hist_table.itemSelectionChanged.connect(show_detail)
        tabs.addTab(hist_w, "📋  History")

        dlg.exec()

    def _show_reports(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Sales Reports")
        dlg.resize(720, 620)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16,16,16,16)

        ttl = QLabel("📊  Sales Reports")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        tabs = QTabWidget()
        l.addWidget(tabs)

        daily_w = QWidget()
        dl = QVBoxLayout(daily_w)
        today = date.today().isoformat()
        sd = load_sales()
        d  = sd.get(today, {})

        stats = [
            ("💰 Cash",    f"₹{fmt(d.get('cash',0))}",  "#4fc3f7", "#0288d1"),
            ("📱 UPI",     f"₹{fmt(d.get('upi',0))}",   "#ff8a65", "#e64a19"),
            ("💳 Card",    f"₹{fmt(d.get('card',0))}",  "#ce93d8", "#8e24aa"),
            ("🔴 Due",     f"₹{fmt(d.get('due',0))}",   "#ef5350", "#b71c1c"),
            ("📋 Bills",   str(d.get('bill_count',0)),   "#7c6aff", "#5a49d0"),
            ("💰 Total",   f"₹{fmt(d.get('total',0))}", "#00c896", "#009e76"),
        ]

        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (label, value, color, dark) in enumerate(stats):
            row, col = divmod(i, 3)
            cf = QFrame()
            cf.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {color},stop:1 {dark});
                    border-radius:10px; border:none;
                }}
            """)
            cf_l = QVBoxLayout(cf)
            cf_l.setContentsMargins(14, 10, 14, 10)
            vl = QLabel(value)
            vl.setStyleSheet(f"color:white;font-size:20px;font-weight:800;background:transparent;border:none;")
            vl.setAlignment(Qt.AlignCenter)
            cf_l.addWidget(vl)
            ll2 = QLabel(label)
            ll2.setStyleSheet(f"color:rgba(255,255,255,0.85);font-size:11px;font-weight:600;background:transparent;border:none;")
            ll2.setAlignment(Qt.AlignCenter)
            cf_l.addWidget(ll2)
            grid.addWidget(cf, row, col)
        dl.addLayout(grid)

        txs = d.get('transactions', [])
        tx_lbl = QLabel(f"📋  Today's Bills  ({len(txs)} total)")
        tx_lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{C_TEXT};")
        dl.addWidget(tx_lbl)

        tx_table = QTableWidget(0, 5)
        tx_table.setHorizontalHeaderLabels(["Time", "Bill#", "Customer", "Payment", "Amount"])
        tx_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tx_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tx_table.verticalHeader().setVisible(False)
        tx_table.setAlternatingRowColors(True)
        tx_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        all_txs = list(reversed(txs[-50:]))
        for tx in all_txs:
            r = tx_table.rowCount()
            tx_table.insertRow(r)
            import re as _re
            raw_pay = tx.get('payment','')
            clean_pay = _re.sub(r'\([^)]*\)', '', raw_pay).strip().strip('+').strip()
            for col, val in enumerate([
                tx.get('time',''), tx.get('bill_no',''),
                tx.get('customer',''), clean_pay,
                f"Rs.{fmt(tx.get('amount',0))}"
            ]):
                itm = QTableWidgetItem(val)
                itm.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    itm.setForeground(QColor("#69f0ae"))
                tx_table.setItem(r, col, itm)
        dl.addWidget(tx_table, 1)

        tabs.addTab(daily_w, "📅 Today")

        byday_w = QWidget()
        byday_l = QVBoxLayout(byday_w)
        byday_l.setContentsMargins(12, 12, 12, 12)
        byday_l.setSpacing(8)

        byday_ctrl = QHBoxLayout()
        date_edit = QLineEdit()
        date_edit.setPlaceholderText("YYYY-MM-DD  (or leave blank for all)")
        date_edit.setFixedHeight(34)
        date_edit.setMaximumWidth(220)
        byday_ctrl.addWidget(date_edit)
        search_day_btn = QPushButton("🔍 Search")
        search_day_btn.setFixedHeight(34)
        search_day_btn.setStyleSheet(f"background:{C_ACCENT};border:none;border-radius:7px;color:white;font-weight:700;padding:0 14px;")
        byday_ctrl.addWidget(search_day_btn)
        byday_ctrl.addStretch()
        byday_l.addLayout(byday_ctrl)

        byday_table = QTableWidget(0, 5)
        byday_table.setHorizontalHeaderLabels(["Date", "Bills", "Cash", "UPI/Card", "Total"])
        byday_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        byday_table.setAlternatingRowColors(True)
        byday_table.verticalHeader().setVisible(False)
        byday_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        byday_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        byday_l.addWidget(byday_table, 1)

        def load_byday(q=""):
            byday_table.setRowCount(0)
            for ds in sorted(sd.keys(), reverse=True):
                if q and q not in ds:
                    continue
                dd = sd[ds]
                r = byday_table.rowCount()
                byday_table.insertRow(r)
                upi_card = dd.get('upi',0) + dd.get('card',0)
                for ci, val in enumerate([
                    ds, str(dd.get('bill_count',0)),
                    f"₹{fmt(dd.get('cash',0))}", f"₹{fmt(upi_card)}",
                    f"₹{fmt(dd.get('total',0))}"
                ]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter)
                    if ci == 4:
                        itm.setForeground(QColor("#69f0ae"))
                    byday_table.setItem(r, ci, itm)

        search_day_btn.clicked.connect(lambda: load_byday(date_edit.text().strip()))
        date_edit.returnPressed.connect(lambda: load_byday(date_edit.text().strip()))
        load_byday()
        tabs.addTab(byday_w, "📆 By Day")

        month_w = QWidget()
        ml = QVBoxLayout(month_w)
        now = datetime.now()

        ctrl = QHBoxLayout()
        month_combo = QComboBox()
        month_combo.addItems([str(i) for i in range(1, 13)])
        month_combo.setCurrentIndex(now.month - 1)
        ctrl.addWidget(QLabel("Month:"))
        ctrl.addWidget(month_combo)
        year_combo = QComboBox()
        year_combo.addItems([str(y) for y in range(2024, now.year + 2)])
        year_combo.setCurrentText(str(now.year))
        ctrl.addWidget(QLabel("Year:"))
        ctrl.addWidget(year_combo)
        load_btn = QPushButton("📊 Load")
        load_btn.setFixedHeight(32)
        ctrl.addWidget(load_btn)
        ctrl.addStretch()
        ml.addLayout(ctrl)

        report_edit = QTextEdit()
        report_edit.setReadOnly(True)
        report_edit.setFont(QFont("Courier New", 10))
        ml.addWidget(report_edit)

        def load_monthly():
            m = int(month_combo.currentText())
            y = int(year_combo.currentText())
            tc=tu=tcard=tdue=tot=bills=0
            day_lines=[]
            for day in range(1, calendar.monthrange(y, m)[1]+1):
                ds = f"{y}-{m:02d}-{day:02d}"
                if ds in sd:
                    dd = sd[ds]
                    tc    += dd.get('cash',0)
                    tu    += dd.get('upi',0)
                    tcard += dd.get('card',0)
                    tdue  += dd.get('due',0)
                    tot   += dd.get('total',0)
                    bills += dd.get('bill_count',0)
                    day_lines.append(f"  {ds} | Bills:{dd['bill_count']:3d} | ₹{fmt(dd['total']):>10}")
            W = 52
            lines = [
                "=" * W, MART_NAME.center(W),
                f"MONTHLY REPORT - {calendar.month_name[m]} {y}".center(W),
                "=" * W, f"  Total Bills: {bills}", "-" * W,
                f"  CASH : ₹{fmt(tc)}", f"  UPI  : ₹{fmt(tu)}",
                f"  CARD : ₹{fmt(tcard)}", f"  DUE  : ₹{fmt(tdue)}", "-" * W,
                f"  GRAND TOTAL: ₹{fmt(tot)}", "=" * W
            ]
            if day_lines:
                lines += ["", "DAILY BREAKDOWN:"] + day_lines
            else:
                lines.append("\nNo transactions this month.")
            report_edit.setPlainText("\n".join(lines))

        load_btn.clicked.connect(load_monthly)
        load_monthly()
        tabs.addTab(month_w, "📆 Monthly")

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _manage_users(self):
        if self.current_user['role'] != 'admin':
            QMessageBox.warning(self, "Access Denied", "Admins only."); return
        dlg = QDialog(self)
        dlg.setWindowTitle("User Management")
        dlg.resize(800, 540)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16,16,16,16)
        l.setSpacing(10)

        ttl = QLabel("👥  User Management")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        body = QHBoxLayout()

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["USERNAME", "NAME", "ROLE", "CREATED"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        body.addWidget(table, 2)

        form_frame = QFrame()
        form_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        form_frame.setFixedWidth(280)
        fl = QVBoxLayout(form_frame)
        fl.setContentsMargins(16,16,16,16)
        fl.setSpacing(8)

        create_ttl = QLabel("CREATE USER")
        create_ttl.setStyleSheet(f"""
            font-size:13px;font-weight:800;color:white;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #4fc3f7,stop:1 #0288d1);
            border-radius:7px;padding:6px 12px;
        """)
        fl.addWidget(create_ttl)

        entries = {}
        for lbl, key, pw in [("Username","uname",False),("Full Name","fullname",False),
                               ("Password","pwd",True),("Confirm Password","cpwd",True)]:
            ql = QLabel(lbl.upper())
            ql.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:3px;")
            fl.addWidget(ql)
            e = QLineEdit()
            if pw: e.setEchoMode(QLineEdit.Password)
            e.setFixedHeight(34)
            fl.addWidget(e)
            entries[key] = e

        ql2 = QLabel("ROLE")
        ql2.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:3px;")
        fl.addWidget(ql2)
        role_combo = QComboBox()
        role_combo.addItems(["cashier","admin"])
        role_combo.setFixedHeight(34)
        fl.addWidget(role_combo)

        status_lbl2 = QLabel("")
        status_lbl2.setStyleSheet(f"font-size:11px;background:transparent;border:none;")
        fl.addWidget(status_lbl2)

        def refresh_users():
            table.setRowCount(0)
            for u in self.user_manager.get_all_users():
                r = table.rowCount(); table.insertRow(r)
                for col, val in enumerate([u['username'],u['name'],u['role'],u['created']]):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(r, col, item)

        refresh_users()

        def create_user():
            u = entries['uname'].text().strip()
            n = entries['fullname'].text().strip()
            p = entries['pwd'].text()
            cp = entries['cpwd'].text()
            if not all([u, n, p]):
                status_lbl2.setText("All fields required!"); status_lbl2.setStyleSheet("color:#ef5350;"); return
            if p != cp:
                status_lbl2.setText("Passwords don't match!"); status_lbl2.setStyleSheet("color:#ef5350;"); return
            ok, msg = self.user_manager.add_user(u, p, n, role_combo.currentText())
            status_lbl2.setText(msg)
            status_lbl2.setStyleSheet(f"color:{'#69f0ae' if ok else '#ef5350'};")
            if ok:
                for e in entries.values(): e.clear()
                refresh_users()

        def delete_user():
            row = table.currentRow()
            if row < 0: return
            uname = table.item(row, 0).text()
            if QMessageBox.question(dlg, "Confirm", f"Delete user '{uname}'?") == QMessageBox.Yes:
                ok, msg = self.user_manager.delete_user(uname)
                if ok: refresh_users()
                else: QMessageBox.warning(dlg, "Error", msg)

        btn_row3 = QHBoxLayout()
        cb = QPushButton("✅ Create"); cb.setObjectName("greenBtn"); cb.setFixedHeight(36)
        cb.clicked.connect(create_user)
        btn_row3.addWidget(cb)
        db = QPushButton("🗑 Delete"); db.setObjectName("redBtn"); db.setFixedHeight(36)
        db.clicked.connect(delete_user)
        btn_row3.addWidget(db)
        fl.addLayout(btn_row3)
        fl.addStretch()

        body.addWidget(form_frame)
        l.addLayout(body)

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _switch_user(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Switch User")
        dlg.setFixedSize(360, 280)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(30, 30, 30, 20)
        l.setSpacing(10)

        ttl = QLabel("🔄 Switch User")
        ttl.setStyleSheet(f"font-size:16px;font-weight:700;color:{C_TEXT};")
        l.addWidget(ttl)

        form = QFormLayout()
        ue = QLineEdit(); ue.setFixedHeight(36)
        pe = QLineEdit(); pe.setFixedHeight(36); pe.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", ue)
        form.addRow("Password:", pe)
        l.addLayout(form)

        st = QLabel(""); st.setStyleSheet("color:#ef5350;")
        l.addWidget(st)

        btn = QPushButton("Login")
        btn.setObjectName("accentBtn"); btn.setFixedHeight(40)
        l.addWidget(btn)

        def do_switch():
            um = UserManager()
            if um.verify_login(ue.text().strip(), pe.text().strip()):
                self.current_user = um.current_user
                self.admin_btn.setText(f"⚙  {self.current_user['name']}  ▾")
                self.user_lbl.setText(f"👤 {self.current_user['name']}")
                self.status_bar.showMessage(f"Switched to: {self.current_user['name']}")
                dlg.accept()
            else:
                st.setText("⚠ Invalid credentials")

        btn.clicked.connect(do_switch)
        ue.returnPressed.connect(pe.setFocus)
        pe.returnPressed.connect(do_switch)
        dlg.exec()

    def _logout(self):
        if self.cart_items:
            if QMessageBox.question(self, "Logout", "Cart has items. Logout anyway?") != QMessageBox.Yes:
                return
        self.close()
        main()

    def _send_offer_all_dialog(self):
        import urllib.parse, webbrowser, time as _time
        dlg = QDialog(self)
        dlg.setWindowTitle("📢 WhatsApp")
        dlg.resize(700, 680)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(10)

        ttl = QLabel("📢  Send Message / Offer to Customers")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        tabs = QTabWidget()
        l.addWidget(tabs, 1)

        tab_all = QWidget()
        ta_l = QVBoxLayout(tab_all)
        ta_l.setContentsMargins(12, 12, 12, 12)
        ta_l.setSpacing(8)

        ta_info = QLabel(f"Send the same message to ALL {len(self.customers)} saved customers at once.")
        ta_info.setStyleSheet(f"color:{C_MUTED};font-size:12px;background:transparent;border:none;")
        ta_l.addWidget(ta_info)

        offer_edit = QTextEdit()
        offer_edit.setPlaceholderText(
            f"🎉 Special Offer from {MART_NAME}!\n\nGet 10% OFF on all items this weekend!\n"
            f"Visit us at: {ADDRESS}\nCall: {PHONE}"
        )
        offer_edit.setMinimumHeight(120)
        ta_l.addWidget(offer_edit)

        broadcast_btn = QPushButton(f"📢  Broadcast to ALL {len(self.customers)} Customers")
        broadcast_btn.setFixedHeight(46)
        broadcast_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ff8a65,stop:1 #e64a19);
                border:none; border-radius:10px; color:white; font-weight:800; font-size:14px;
            }}
            QPushButton:hover {{ border:2px solid white; background:#e64a19; }}
        """)
        ta_l.addWidget(broadcast_btn)

        status_all = QLabel("")
        status_all.setStyleSheet(f"color:#69f0ae;font-size:12px;font-weight:700;background:transparent;border:none;")
        status_all.setAlignment(Qt.AlignCenter)
        status_all.setWordWrap(True)
        ta_l.addWidget(status_all)
        ta_l.addStretch()

        def send_all():
            msg = offer_edit.toPlainText().strip()
            if not msg:
                QMessageBox.warning(dlg, "Empty", "Enter message first."); return
            phones = [p for p in self.customers.keys() if p]
            if not phones:
                QMessageBox.warning(dlg, "No Customers", "No phones saved."); return
            reply = QMessageBox.question(dlg, "Confirm",
                f"Opens {len(phones)} WhatsApp tabs.\nYou must press SEND manually in each.\nProceed?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes: return
            sent = 0
            for phone in phones:
                ph2 = phone.replace(" ","").replace("-","")
                if ph2.startswith("0"): ph2 = "91" + ph2[1:]
                elif not ph2.startswith("91") and len(ph2) == 10: ph2 = "91" + ph2
                webbrowser.open(f"https://wa.me/{ph2}?text={urllib.parse.quote(msg)}")
                sent += 1
                status_all.setText(f"⏳ Opened {sent}/{len(phones)}…")
                QApplication.processEvents()
                _time.sleep(0.5)
            status_all.setText(f"✅ Done! {sent} tabs opened.")

        broadcast_btn.clicked.connect(send_all)
        tabs.addTab(tab_all, "📢 Broadcast to All")

        tab_sel = QWidget()
        ts_l = QVBoxLayout(tab_sel)
        ts_l.setContentsMargins(12, 12, 12, 12)
        ts_l.setSpacing(8)

        cust_tbl = QTableWidget(0, 3)
        cust_tbl.setHorizontalHeaderLabels(["Customer Name", "Phone", "Points"])
        cust_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        cust_tbl.setColumnWidth(1, 120)
        cust_tbl.setColumnWidth(2, 70)
        cust_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        cust_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cust_tbl.verticalHeader().setVisible(False)
        cust_tbl.setAlternatingRowColors(True)
        cust_tbl.setMaximumHeight(200)
        ts_l.addWidget(cust_tbl)

        for phone, data in self.customers.items():
            r = cust_tbl.rowCount()
            cust_tbl.insertRow(r)
            for ci, val in enumerate([data.get('name', ''), phone, str(data.get('points', 0))]):
                itm = QTableWidgetItem(val)
                itm.setTextAlignment(Qt.AlignCenter if ci else (Qt.AlignLeft | Qt.AlignVCenter))
                cust_tbl.setItem(r, ci, itm)
            cust_tbl.setRowHeight(r, 26)

        sel_all_btn = QPushButton("☑ Select All")
        sel_all_btn.setFixedHeight(28)
        sel_all_btn.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:6px;color:{C_TEXT};padding:0 10px;font-size:11px;")
        sel_all_btn.clicked.connect(cust_tbl.selectAll)
        ts_l.addWidget(sel_all_btn)

        ind_msg_edit = QTextEdit()
        ind_msg_edit.setPlaceholderText(
            f"Hello {{name}},\n\nSpecial offer just for you from {MART_NAME}!\nVisit us at {ADDRESS}.\nCall: {PHONE}")
        ind_msg_edit.setMinimumHeight(100)
        ts_l.addWidget(ind_msg_edit)

        send_sel_btn = QPushButton("📱  Send to Selected Customers")
        send_sel_btn.setFixedHeight(44)
        send_sel_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #25D366,stop:1 #128C7E);
                border:none; border-radius:9px; color:white; font-weight:800; font-size:13px;
            }}
            QPushButton:hover {{ border:2px solid white; background:#128C7E; }}
        """)
        ts_l.addWidget(send_sel_btn)

        status_sel = QLabel("")
        status_sel.setStyleSheet(f"color:#69f0ae;font-size:12px;font-weight:700;background:transparent;border:none;")
        status_sel.setAlignment(Qt.AlignCenter)
        ts_l.addWidget(status_sel)
        ts_l.addStretch()

        def send_selected():
            rows = sorted(set(idx.row() for idx in cust_tbl.selectedIndexes()))
            if not rows:
                QMessageBox.warning(dlg, "None Selected", "Select at least one customer."); return
            msg_tmpl = ind_msg_edit.toPlainText().strip()
            if not msg_tmpl:
                QMessageBox.warning(dlg, "Empty", "Enter message first."); return
            sent = 0
            for row in rows:
                ni = cust_tbl.item(row, 0)
                pi = cust_tbl.item(row, 1)
                if not ni or not pi: continue
                cname = ni.text()
                cphone = pi.text()
                msg = msg_tmpl.replace("{name}", cname)
                ph2 = cphone.replace(" ","").replace("-","")
                if ph2.startswith("0"): ph2 = "91" + ph2[1:]
                elif not ph2.startswith("91") and len(ph2) == 10: ph2 = "91" + ph2
                webbrowser.open(f"https://wa.me/{ph2}?text={urllib.parse.quote(msg)}")
                sent += 1
                status_sel.setText(f"⏳ Opened {sent}…")
                QApplication.processEvents()
                _time.sleep(0.5)
            status_sel.setText(f"✅ Sent to {sent} customer(s).")

        send_sel_btn.clicked.connect(send_selected)
        tabs.addTab(tab_sel, "👤 Send to Selected")

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _expense_tracker(self):
        EXPENSE_FILE = "expenses.json"
        try:
            with open(EXPENSE_FILE) as f:
                expenses = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            expenses = []

        dlg = QDialog(self)
        dlg.setWindowTitle("Cash Expense Tracker")
        dlg.resize(900, 580)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(8)

        hdr_row = QHBoxLayout()
        ttl = QLabel("💸  Cash Expense Tracker")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        hdr_row.addWidget(ttl)
        hdr_row.addStretch()
        today_exp = sum(e['amount'] for e in expenses if e.get('date','').startswith(date.today().isoformat()))
        today_lbl = QLabel(f"Today's Total: ₹{fmt(today_exp)}")
        today_lbl.setStyleSheet(f"color:#ef5350;font-size:14px;font-weight:800;background:transparent;border:none;")
        hdr_row.addWidget(today_lbl)
        l.addLayout(hdr_row)

        filter_row = QHBoxLayout()
        date_filter = QLineEdit()
        date_filter.setPlaceholderText("YYYY-MM-DD")
        date_filter.setFixedHeight(32)
        date_filter.setMaximumWidth(180)
        filter_row.addWidget(date_filter)
        filter_btn = QPushButton("🔍 Filter")
        filter_btn.setFixedHeight(32)
        filter_btn.setStyleSheet(f"background:{C_ACCENT};border:none;border-radius:7px;color:white;font-weight:700;padding:0 12px;")
        filter_row.addWidget(filter_btn)
        filter_row.addStretch()
        l.addLayout(filter_row)

        body = QHBoxLayout()
        body.setSpacing(12)

        exp_table = QTableWidget(0, 6)
        exp_table.setHorizontalHeaderLabels(["Date", "Time", "Description", "Category", "Payment", "Amount"])
        exp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        exp_table.setColumnWidth(0, 95)
        exp_table.setColumnWidth(1, 68)
        exp_table.setColumnWidth(3, 80)
        exp_table.setColumnWidth(4, 85)
        exp_table.setColumnWidth(5, 80)
        exp_table.setAlternatingRowColors(True)
        exp_table.verticalHeader().setVisible(False)
        exp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        exp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        body.addWidget(exp_table, 3)

        form_frame = QFrame()
        form_frame.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        form_frame.setFixedWidth(240)
        fl = QVBoxLayout(form_frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(8)

        form_ttl = QLabel("ADD EXPENSE")
        form_ttl.setStyleSheet(f"""
            font-size:12px;font-weight:800;color:white;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6aff,stop:1 #5a49d0);
            border-radius:7px;padding:6px 12px;
        """)
        form_ttl.setAlignment(Qt.AlignCenter)
        fl.addWidget(form_ttl)

        desc_lbl2 = QLabel("DESCRIPTION")
        desc_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        fl.addWidget(desc_lbl2)
        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("e.g. Tea, Transport")
        desc_edit.setFixedHeight(34)
        fl.addWidget(desc_edit)

        amt_lbl2 = QLabel("AMOUNT ₹")
        amt_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
        fl.addWidget(amt_lbl2)
        amt_edit = QLineEdit()
        amt_edit.setPlaceholderText("0.00")
        amt_edit.setFixedHeight(34)
        fl.addWidget(amt_edit)

        cat_lbl2 = QLabel("CATEGORY")
        cat_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
        fl.addWidget(cat_lbl2)
        cat_combo = QComboBox()
        cat_combo.addItems(["General", "Food", "Transport", "Utility", "Salary", "Other"])
        cat_combo.setFixedHeight(34)
        fl.addWidget(cat_combo)

        pay_lbl2 = QLabel("PAYMENT METHOD")
        pay_lbl2.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
        fl.addWidget(pay_lbl2)
        pay_combo2 = QComboBox()
        pay_combo2.addItems(["Cash", "UPI", "Card", "Other"])
        pay_combo2.setFixedHeight(34)
        fl.addWidget(pay_combo2)

        exp_status = QLabel("")
        exp_status.setStyleSheet(f"color:#69f0ae;font-size:11px;background:transparent;border:none;")
        exp_status.setWordWrap(True)
        fl.addWidget(exp_status)

        add_btn = QPushButton("✚  Add Expense")
        add_btn.setFixedHeight(38)
        add_btn.setAutoDefault(False)
        add_btn.setDefault(False)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00c896,stop:1 #009e76);
                border:none;border-radius:8px;color:white;font-weight:800;font-size:13px;
            }}
            QPushButton:hover {{ background:#009e76; border:2px solid white; }}
        """)
        fl.addWidget(add_btn)

        del_exp_btn = QPushButton("🗑  Delete Selected")
        del_exp_btn.setFixedHeight(34)
        del_exp_btn.setAutoDefault(False)
        del_exp_btn.setDefault(False)
        del_exp_btn.setStyleSheet(f"""
            QPushButton {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
                border:none;border-radius:8px;color:white;font-weight:700;font-size:12px;
            }}
            QPushButton:hover {{ background:#b71c1c; border:2px solid white; }}
        """)
        fl.addWidget(del_exp_btn)

        fl.addStretch()

        total_box = QFrame()
        total_box.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:8px;")
        tb_l = QVBoxLayout(total_box)
        tb_l.setContentsMargins(10, 8, 10, 8)
        total_lbl = QLabel(f"Total: ₹{fmt(sum(e['amount'] for e in expenses))}")
        total_lbl.setStyleSheet(f"color:#ef5350;font-size:14px;font-weight:800;background:transparent;border:none;")
        total_lbl.setAlignment(Qt.AlignCenter)
        tb_l.addWidget(total_lbl)
        fl.addWidget(total_box)

        body.addWidget(form_frame)
        l.addLayout(body, 1)

        def refresh_exp(q=""):
            exp_table.setRowCount(0)
            for e in reversed(expenses):
                if q and not e.get('date','').startswith(q):
                    continue
                r = exp_table.rowCount()
                exp_table.insertRow(r)
                for ci, val in enumerate([
                    e.get('date',''), e.get('time',''),
                    e.get('desc',''), e.get('cat',''),
                    e.get('pay_method','Cash'),
                    f"Rs.{fmt(e.get('amount',0))}"
                ]):
                    itm = QTableWidgetItem(val)
                    itm.setTextAlignment(Qt.AlignCenter if ci != 2 else (Qt.AlignLeft | Qt.AlignVCenter))
                    if ci == 5: itm.setForeground(QColor("#ef5350"))
                    exp_table.setItem(r, ci, itm)
            total = sum(e['amount'] for e in expenses if not q or e.get('date','').startswith(q))
            total_lbl.setText(f"Total: Rs.{fmt(total)}")

        def add_expense():
            desc = desc_edit.text().strip()
            try:
                amt = float(amt_edit.text())
            except ValueError:
                exp_status.setText("⚠ Enter valid amount")
                exp_status.setStyleSheet("color:#ef5350;font-size:11px;background:transparent;border:none;")
                return
            if not desc:
                exp_status.setText("⚠ Enter description")
                exp_status.setStyleSheet("color:#ef5350;font-size:11px;background:transparent;border:none;")
                return
            expenses.append({
                "date": date.today().isoformat(),
                "time": datetime.now().strftime("%I:%M %p"),
                "desc": desc, "cat": cat_combo.currentText(),
                "pay_method": pay_combo2.currentText(),
                "amount": amt
            })
            with open(EXPENSE_FILE, 'w') as f_:
                json.dump(expenses, f_, indent=2)
            desc_edit.clear(); amt_edit.clear()
            exp_status.setText(f"✅ Added: {desc}")
            exp_status.setStyleSheet("color:#69f0ae;font-size:11px;background:transparent;border:none;")
            refresh_exp(date_filter.text().strip())

        def delete_expense():
            row = exp_table.currentRow()
            if row < 0: return
            shown = [e for e in reversed(expenses)
                     if not date_filter.text().strip() or e.get('date','').startswith(date_filter.text().strip())]
            if row < len(shown):
                exp = shown[row]
                if QMessageBox.question(dlg, "Delete", f"Delete: {exp['desc']} Rs.{fmt(exp['amount'])}?") == QMessageBox.Yes:
                    expenses.remove(exp)
                    with open(EXPENSE_FILE, 'w') as f_:
                        json.dump(expenses, f_, indent=2)
                    refresh_exp(date_filter.text().strip())

        add_btn.clicked.connect(add_expense)
        del_exp_btn.clicked.connect(delete_expense)
        desc_edit.returnPressed.connect(lambda: amt_edit.setFocus())
        amt_edit.returnPressed.connect(add_expense)
        filter_btn.clicked.connect(lambda: refresh_exp(date_filter.text().strip()))
        date_filter.returnPressed.connect(lambda: refresh_exp(date_filter.text().strip()))

        refresh_exp()

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.setAutoDefault(False)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

    def _shift_management(self):
        SHIFT_FILE = "shifts.json"
        try:
            with open(SHIFT_FILE) as f:
                shifts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            shifts = []

        dlg = QDialog(self)
        dlg.setWindowTitle("Shift Management")
        dlg.resize(820, 600)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(16,16,16,16)
        l.setSpacing(10)

        ttl = QLabel("🕐  Shift Management")
        ttl.setStyleSheet(f"font-size:18px;font-weight:800;color:{C_TEXT};")
        l.addWidget(ttl)

        tabs = QTabWidget()
        l.addWidget(tabs, 1)

        active_w = QWidget()
        active_l = QVBoxLayout(active_w)
        active_l.setContentsMargins(16,14,16,14)
        active_l.setSpacing(10)

        open_shift = next((s for s in reversed(shifts) if not s.get('end')), None)

        shift_status = QLabel()
        shift_status.setAlignment(Qt.AlignCenter)
        shift_status.setWordWrap(True)
        active_l.addWidget(shift_status)

        shift_info_frame = QFrame()
        shift_info_frame.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:10px;")
        si_l = QVBoxLayout(shift_info_frame)
        si_l.setContentsMargins(16,14,16,14)

        if open_shift:
            shift_status.setText(f"✅ Shift OPEN — {open_shift.get('cashier','?')} (since {open_shift.get('start','')})")
            shift_status.setStyleSheet(f"color:#69f0ae;font-size:14px;font-weight:800;background:transparent;border:none;")
            sd_now = load_sales()
            ds = open_shift.get('date', date.today().isoformat())
            day_data = sd_now.get(ds, {})
            for lbl, val, color in [
                ("Cashier", open_shift.get('cashier','—'), C_TEXT),
                ("Shift Start", open_shift.get('start','—'), "#69f0ae"),
                ("Date", open_shift.get('date','—'), C_MUTED),
                ("Bills This Shift", str(day_data.get('bill_count', 0)), "#ffd54f"),
                ("Revenue Today", f"₹{fmt(day_data.get('total', 0))}", "#00c896"),
            ]:
                row_w = QHBoxLayout()
                kl = QLabel(lbl + ":"); kl.setStyleSheet(f"color:{C_MUTED};font-weight:700;background:transparent;border:none;")
                vl = QLabel(val); vl.setStyleSheet(f"color:{color};font-weight:700;background:transparent;border:none;")
                row_w.addWidget(kl); row_w.addWidget(vl); row_w.addStretch()
                si_l.addLayout(row_w)
        else:
            shift_status.setText("⏹ No active shift. Start a new shift below.")
            shift_status.setStyleSheet(f"color:#ffd54f;font-size:14px;font-weight:800;background:transparent;border:none;")
            no_lbl = QLabel("No open shift found.")
            no_lbl.setStyleSheet(f"color:{C_MUTED};background:transparent;border:none;")
            si_l.addWidget(no_lbl)

        active_l.addWidget(shift_info_frame)
        active_l.addStretch()

        btn_row4 = QHBoxLayout()

        def start_shift():
            cashier = self.current_user['name']
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            shifts.append({
                "cashier": cashier, "username": self.current_user['username'],
                "date": date.today().isoformat(),
                "start": now_str, "end": None, "notes": ""
            })
            with open(SHIFT_FILE, 'w') as f_:
                json.dump(shifts, f_, indent=2)
            QMessageBox.information(dlg, "Shift Started", f"Shift started for {cashier} at {now_str}")
            dlg.accept()

        def end_shift():
            if not open_shift:
                QMessageBox.warning(dlg, "No Shift", "No active shift to end."); return
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            open_shift['end'] = now_str
            with open(SHIFT_FILE, 'w') as f_:
                json.dump(shifts, f_, indent=2)
            QMessageBox.information(dlg, "Shift Ended", f"Shift ended at {now_str}")
            dlg.accept()

        start_btn = QPushButton("▶  Start Shift")
        start_btn.setFixedHeight(40)
        start_btn.setEnabled(open_shift is None)
        start_btn.setStyleSheet(f"background:#00c896;border:none;border-radius:9px;color:white;font-weight:800;font-size:13px;padding:0 20px;")
        start_btn.clicked.connect(start_shift)
        btn_row4.addWidget(start_btn)

        end_btn = QPushButton("⏹  End Shift")
        end_btn.setFixedHeight(40)
        end_btn.setEnabled(open_shift is not None)
        end_btn.setStyleSheet(f"background:#ef5350;border:none;border-radius:9px;color:white;font-weight:800;font-size:13px;padding:0 20px;")
        end_btn.clicked.connect(end_shift)
        btn_row4.addWidget(end_btn)

        btn_row4.addStretch()
        active_l.addLayout(btn_row4)
        tabs.addTab(active_w, "⏰ Current Shift")

        hist_w = QWidget()
        hist_l = QVBoxLayout(hist_w)
        hist_l.setContentsMargins(16,14,16,14)

        hist_table = QTableWidget(0, 5)
        hist_table.setHorizontalHeaderLabels(["Date", "Cashier", "Start", "End", "Duration"])
        hist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        hist_table.setAlternatingRowColors(True)
        hist_table.verticalHeader().setVisible(False)
        hist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hist_l.addWidget(hist_table)

        for sh in reversed(shifts):
            r = hist_table.rowCount()
            hist_table.insertRow(r)
            start_full = sh.get('start','')
            end_full   = sh.get('end','')
            def time_only(s):
                if not s: return '—'
                parts = s.split(' ')
                if len(parts) >= 2:
                    try:
                        t = datetime.strptime(parts[1], "%H:%M")
                        return t.strftime("%I:%M %p")
                    except: pass
                return s
            start_t = time_only(start_full)
            end_t   = time_only(end_full) if end_full else "Active"
            duration = "Active"
            if start_full and end_full:
                try:
                    s2 = datetime.strptime(start_full, "%Y-%m-%d %H:%M")
                    e2 = datetime.strptime(end_full,   "%Y-%m-%d %H:%M")
                    diff = int((e2 - s2).total_seconds() / 60)
                    duration = f"{diff // 60}h {diff % 60}m"
                except: pass
            for ci, val in enumerate([sh.get('date',''), sh.get('cashier',''), start_t, end_t, duration]):
                itm = QTableWidgetItem(val)
                itm.setTextAlignment(Qt.AlignCenter)
                if val == "Active":
                    itm.setForeground(QColor("#69f0ae"))
                hist_table.setItem(r, ci, itm)

        tabs.addTab(hist_w, "📋 History")

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(RED_CLOSE_SS)
        close_btn.clicked.connect(dlg.accept)
        l.addWidget(close_btn)
        dlg.exec()

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    login = LoginWindow()
    login.setWindowIcon(QIcon('shopping.ico'))
    login.setStyleSheet(STYLESHEET)

    current_user = None

    def on_login(user):
        nonlocal current_user
        current_user = user

    login.login_success.connect(on_login)
    result = login.exec()

    if result == QDialog.Accepted and current_user:
        pos = POSWindow(current_user)
        pos.setWindowIcon(QIcon('shopping.ico'))
        pos.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()