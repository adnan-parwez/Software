from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit, QLineEdit, 
    QFormLayout, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QKeySequence
from config import *
from data_manager import *
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

class CustomerDialog(QDialog):
    def __init__(self, customers, parent=None):
        super().__init__(parent)
        self.customers = customers
        self.setWindowTitle("Customers & Loyalty")
        self.resize(1100, 650)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self._build()

    def _tier(self, pts):
        if pts >= 10000: return "💎 Diamond", "#b9f2ff"
        if pts >= 5000:  return "🏆 Platinum", "#e5e4e2"
        if pts >= 2000:  return "⭐⭐ Gold", C_GOLD
        if pts >= 1000:  return "⭐ Silver", C_SILVER
        if pts > 0:      return "🥉 Bronze", C_BRONZE
        return "🆕 New Member", C_MUTED

    def _build(self):
        self.setStyleSheet(STYLESHEET)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top = QWidget()
        top.setStyleSheet(f"background:{C_SURFACE}; border-bottom:1px solid {C_BORDER};")
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(20, 14, 20, 14)

        ttl = QLabel("Customers & Loyalty")
        ttl.setStyleSheet(f"font-size:22px;font-weight:800;color:{C_TEXT};")
        top_l.addWidget(ttl)
        top_l.addStretch()

        add_btn = QPushButton("+ New Customer")
        add_btn.setObjectName("accentBtn")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._add_customer)
        top_l.addWidget(add_btn)
        root.addWidget(top)

        stats_w = QWidget()
        stats_w.setStyleSheet(f"background:{C_BG};")
        stats_l = QHBoxLayout(stats_w)
        stats_l.setContentsMargins(20, 6, 20, 6)
        stats_l.setSpacing(10)

        total_members = len(self.customers)
        total_pts = sum(d['points'] for d in self.customers.values())
        gold_members = sum(1 for d in self.customers.values() if d['points'] >= 2000)

        for icon, val, lbl, c1, c2 in [
            ("👥", str(total_members),  "Members",       "#1a2744", "#3d4fa8"),
            ("⭐", str(total_pts),       "Total Points",  "#2a1f00", "#a07800"),
            ("🏆", str(gold_members),   "Gold+",         "#3a1a00", "#a03000"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});
                    border-radius:8px;
                    border-left: 3px solid {c2};
                }}
            """)
            card_l = QHBoxLayout(card)
            card_l.setContentsMargins(10, 6, 10, 6)

            ico = QLabel(icon)
            ico.setStyleSheet("font-size:18px; border:none;")
            card_l.addWidget(ico)

            vbox = QVBoxLayout()
            vbox.setSpacing(0)
            num = QLabel(val)
            num.setStyleSheet(f"font-size:18px;font-weight:800;color:white;border:none;")
            vbox.addWidget(num)
            sub = QLabel(lbl)
            sub.setStyleSheet(f"font-size:9px;color:rgba(255,255,255,0.7);border:none;")
            vbox.addWidget(sub)
            card_l.addLayout(vbox)
            card_l.addStretch()
            stats_l.addWidget(card)

        root.addWidget(stats_w)

        srch_w = QWidget()
        srch_w.setStyleSheet(f"background:{C_BG};")
        srch_l = QHBoxLayout(srch_w)
        srch_l.setContentsMargins(20, 4, 20, 4)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Search by name or phone...")
        self.search_edit.setFixedHeight(36)
        self.search_edit.setMaximumWidth(280)
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background:{C_SURFACE}; border:1px solid {C_BORDER};
                border-radius:8px; padding: 0 14px; font-size:13px;
            }}
            QLineEdit:focus {{ border-color:{C_ACCENT}; }}
        """)
        self.search_edit.textChanged.connect(self._refresh)
        srch_l.addWidget(self.search_edit)
        srch_l.addStretch()
        root.addWidget(srch_w)

        body = QWidget()
        body.setStyleSheet(f"background:{C_BG};")
        body_l = QHBoxLayout(body)
        body_l.setContentsMargins(20, 0, 20, 12)
        body_l.setSpacing(12)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PHONE", "NAME", "POINTS", "TIER", "GIFTS", "GIFT NAME"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 55)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background:{C_SURFACE}; border:1px solid {C_BORDER}; border-radius:10px; }}
        """)
        self.table.itemSelectionChanged.connect(self._on_select)
        body_l.addWidget(self.table, 2)

        self.detail = QFrame()
        self.detail.setObjectName("surface")
        self.detail.setFixedWidth(340)
        self.detail.setStyleSheet(f"background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;")
        det_l = QVBoxLayout(self.detail)
        det_l.setContentsMargins(18, 18, 18, 18)
        det_l.setSpacing(10)

        det_title = QLabel("Member Profile")
        det_title.setStyleSheet(f"""
            font-size:14px;font-weight:800;color:white;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ce93d8,stop:1 #8e24aa);
            border-radius:7px;padding:6px 12px;
        """)
        det_l.addWidget(det_title)

        self.det_fields = {}
        for key, lbl in [("name","Name"),("phone","Phone"),("points","Points"),("tier","Tier")]:
            fl = QLabel(lbl.upper())
            fl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
            det_l.addWidget(fl)
            vl = QLabel("—")
            vl.setStyleSheet(f"color:{C_TEXT};font-size:14px;font-weight:700;background:transparent;border:none;")
            det_l.addWidget(vl)
            self.det_fields[key] = vl

        det_l.addSpacing(8)

        adj_lbl = QLabel("ADJUST POINTS")
        adj_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        det_l.addWidget(adj_lbl)

        self.adj_edit = QLineEdit()
        self.adj_edit.setPlaceholderText("e.g. 50 or -20")
        self.adj_edit.setFixedHeight(34)
        self.adj_edit.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:7px;color:{C_TEXT};padding:0 8px;")
        det_l.addWidget(self.adj_edit)

        adj_btn = QPushButton("Apply Adjustment")
        adj_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ff8a65,stop:1 #e64a19);
                border:none;border-radius:7px;color:white;font-weight:700;font-size:12px;
            }}
            QPushButton:hover {{ background:#e64a19; }}
        """)
        adj_btn.setFixedHeight(34)
        adj_btn.clicked.connect(self._adjust_points)
        det_l.addWidget(adj_btn)

        det_l.addSpacing(8)

        gift_lbl = QLabel("GIFTS EARNED")
        gift_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;")
        det_l.addWidget(gift_lbl)

        gift_row = QHBoxLayout()
        self.gift_edit = QLineEdit()
        self.gift_edit.setPlaceholderText("0")
        self.gift_edit.setFixedHeight(32)
        self.gift_edit.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:7px;color:{C_TEXT};padding:0 6px;")
        gift_row.addWidget(self.gift_edit)

        save_gift_btn = QPushButton("Save")
        save_gift_btn.setFixedHeight(32)
        save_gift_btn.setFixedWidth(56)
        save_gift_btn.setStyleSheet(f"background:#00c896;border:none;border-radius:7px;color:white;font-weight:700;")
        save_gift_btn.clicked.connect(self._save_gifts)
        gift_row.addWidget(save_gift_btn)
        det_l.addLayout(gift_row)

        gift_name_lbl = QLabel("GIFT NAME")
        gift_name_lbl.setStyleSheet(f"color:{C_MUTED};font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;border:none;margin-top:4px;")
        det_l.addWidget(gift_name_lbl)

        gift_name_row = QHBoxLayout()
        self.gift_name_edit = QLineEdit()
        self.gift_name_edit.setPlaceholderText("e.g. Rice Bag")
        self.gift_name_edit.setFixedHeight(32)
        self.gift_name_edit.setStyleSheet(f"background:{C_SURFACE2};border:1px solid {C_BORDER};border-radius:7px;color:{C_TEXT};padding:0 6px;")
        gift_name_row.addWidget(self.gift_name_edit)

        save_gname_btn = QPushButton("Save")
        save_gname_btn.setFixedHeight(32)
        save_gname_btn.setFixedWidth(56)
        save_gname_btn.setStyleSheet(f"background:#7c6aff;border:none;border-radius:7px;color:white;font-weight:700;")
        save_gname_btn.clicked.connect(self._save_gift_name)
        gift_name_row.addWidget(save_gname_btn)
        det_l.addLayout(gift_name_row)

        det_l.addStretch()

        del_btn = QPushButton("🗑  Remove Customer")
        del_btn.setObjectName("redBtn")
        del_btn.setFixedHeight(36)
        del_btn.clicked.connect(self._delete_customer)
        det_l.addWidget(del_btn)

        body_l.addWidget(self.detail)
        root.addWidget(body)

        close_bar = QWidget()
        close_bar.setStyleSheet(f"background:{C_BG};")
        close_bar_l = QHBoxLayout(close_bar)
        close_bar_l.setContentsMargins(20, 8, 20, 12)
        close_bar_l.addStretch()
        close_btn_main = QPushButton("✕  Close")
        close_btn_main.setFixedHeight(36)
        close_btn_main.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef5350,stop:1 #b71c1c);
                border:none; border-radius:8px; color:white; font-weight:800; font-size:13px; padding: 0 24px;
            }}
            QPushButton:hover {{ background:#b71c1c; }}
        """)
        close_btn_main.clicked.connect(self.accept)
        close_bar_l.addWidget(close_btn_main)
        root.addWidget(close_bar)

        self._refresh()

    def _refresh(self, q=""):
        q = self.search_edit.text().lower().strip()
        self.table.setRowCount(0)
        for phone, d in self.customers.items():
            if q and q not in phone.lower() and q not in d['name'].lower():
                continue
            tier, _ = self._tier(d['points'])
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate([phone, d['name'], str(d['points']), tier,
                                        str(d.get('gifts', 0)), d.get('gift_name', '')]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    item.setForeground(QColor(C_GOLD))
                if col == 5:
                    item.setForeground(QColor("#69f0ae"))
                self.table.setItem(row, col, item)

    def _on_select(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = self.table.currentRow()
        phone = self.table.item(row, 0).text()
        d = self.customers.get(phone, {})
        tier, col = self._tier(d.get('points', 0))
        self.det_fields['name'].setText(d.get('name', ''))
        self.det_fields['phone'].setText(phone)
        self.det_fields['points'].setText(str(d.get('points', 0)))
        self.det_fields['tier'].setText(tier)
        self.det_fields['tier'].setStyleSheet(f"color:{col};font-size:14px;font-weight:700;background:transparent;border:none;")
        self.gift_edit.setText(str(d.get('gifts', 0)))
        self.gift_name_edit.setText(d.get('gift_name', ''))

    def _adjust_points(self):
        phone = self.det_fields['phone'].text()
        if not phone or phone == '—':
            return
        try:
            adj = int(self.adj_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter an integer (positive or negative).")
            return
        if phone in self.customers:
            self.customers[phone]['points'] = max(0, self.customers[phone]['points'] + adj)
            save_customers(self.customers)
            self._refresh()
            self.det_fields['points'].setText(str(self.customers[phone]['points']))
            self.adj_edit.clear()
            QMessageBox.information(self, "Updated", f"Points updated. New total: {self.customers[phone]['points']}")

    def _save_gifts(self):
        phone = self.det_fields['phone'].text()
        if not phone or phone == '—':
            return
        try:
            gifts = int(self.gift_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter an integer for gifts.")
            return
        if phone in self.customers:
            self.customers[phone]['gifts'] = gifts
            save_customers(self.customers)
            self._refresh()
            QMessageBox.information(self, "Saved", f"Gifts updated to {gifts}.")

    def _save_gift_name(self):
        phone = self.det_fields['phone'].text()
        if not phone or phone == '—':
            return
        name = self.gift_name_edit.text().strip()
        if phone in self.customers:
            self.customers[phone]['gift_name'] = name
            save_customers(self.customers)
            self._refresh()

    def _delete_customer(self):
        phone = self.det_fields['phone'].text()
        if not phone or phone == '—':
            return
        if QMessageBox.question(self, "Confirm", f"Delete customer {phone}?") == QMessageBox.Yes:
            del self.customers[phone]
            save_customers(self.customers)
            self._refresh()
            for v in self.det_fields.values():
                v.setText('—')

    def _add_customer(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add New Customer")
        dlg.setFixedSize(360, 220)
        dlg.setStyleSheet(STYLESHEET)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(24, 24, 24, 24)
        l.setSpacing(10)

        ttl = QLabel("➕ NEW CUSTOMER")
        ttl.setStyleSheet(f"font-size:16px;font-weight:700;color:{C_TEXT};")
        l.addWidget(ttl)

        form = QFormLayout()
        ne = QLineEdit(); ne.setFixedHeight(36)
        pe = QLineEdit(); pe.setFixedHeight(36)
        form.addRow("Name:", ne)
        form.addRow("Phone:", pe)
        l.addLayout(form)

        sb = QPushButton("✅ Save")
        sb.setObjectName("accentBtn")
        sb.setFixedHeight(40)
        l.addWidget(sb)

        def save():
            n = ne.text().strip(); p = pe.text().strip()
            if not n or not p:
                return
            if p in self.customers:
                QMessageBox.warning(dlg, "Exists", "Phone already registered.")
                return
            self.customers[p] = {"name": n, "points": 0, "gifts": 0}
            save_customers(self.customers)
            self._refresh()
            dlg.accept()

        sb.clicked.connect(save)
        dlg.exec()


class BillPreviewDialog(QDialog):
    def __init__(self, bill_text, parent=None):
        super().__init__(parent)
        self.bill_text = bill_text
        self.parent_pos = parent
        self.setWindowTitle("Bill Preview")
        self.resize(420, 640)
        self.setStyleSheet(STYLESHEET)
        self._build()
        self._btn_print.setFocus()

    def _build(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        ttl = QLabel("📄  Bill Preview(Thermal)")
        ttl.setStyleSheet(f"font-size:15px;font-weight:700;color:{C_TEXT};")
        l.addWidget(ttl)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setFont(QFont("Courier New", 10))
        self.text_view.setStyleSheet(f"""
            QTextEdit {{
                background: #fffde7;
                color: #111;
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        self.text_view.setPlainText(self.bill_text)
        l.addWidget(self.text_view)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_print = QPushButton("🖨️  Print  (Enter)")
        self._btn_print.setObjectName("greenBtn")
        self._btn_print.setFixedHeight(42)
        self._btn_print.clicked.connect(self._do_print)
        btn_row.addWidget(self._btn_print)

        self._btn_pdf = QPushButton("📄  Save PDF")
        self._btn_pdf.setFixedHeight(42)
        self._btn_pdf.clicked.connect(self._do_pdf)
        btn_row.addWidget(self._btn_pdf)

        self._btn_close = QPushButton("✕  Close")
        self._btn_close.setObjectName("redBtn")
        self._btn_close.setFixedHeight(42)
        self._btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_close)

        l.addLayout(btn_row)

        self._btn_print.setShortcut(QKeySequence(Qt.Key_Return))
        self._btns = [self._btn_print, self._btn_pdf, self._btn_close]

        for i, btn in enumerate(self._btns):
            btn.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Tab:
                idx = self._btns.index(obj) if obj in self._btns else -1
                if idx >= 0:
                    self._btns[(idx + 1) % len(self._btns)].setFocus()
                    return True
        return super().eventFilter(obj, event)

    def _do_print(self):
        if self.parent_pos:
             if "DUE" in self.parent_pos._get_payment():
                self.parent_pos._add_to_dues()
                self.accept()
                return
        self.parent_pos._save_transaction()
        self.parent_pos._print_thermal()
        self.parent_pos._add_points()
        self.parent_pos._clear_all(skip_confirm=True)
        self.accept()

    def _do_pdf(self):
        if not REPORTLAB_OK:
            QMessageBox.warning(self, "Missing", "Install reportlab:\n  pip install reportlab")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"Bill_{datetime.now():%Y%m%d_%H%M}.pdf", "PDF (*.pdf)")
        if path:
            self._generate_pdf(path)
            QMessageBox.information(self, "Saved", f"PDF saved:\n{path}")
            self.accept()
            if self.parent_pos:
                self._save_and_clear()

    def _generate_pdf(self, filename):
        width = 80 * mm
        height = 297 * mm
        c = rl_canvas.Canvas(filename, pagesize=(width, height))
        y = height - 8
        lines = self.bill_text.split("\n")

        for line in lines:
            stripped = line.strip()
            is_bold = (
                MART_NAME.upper() in stripped
                or "GRAND TOTAL" in stripped
                or stripped.startswith("=")
                or stripped.startswith("-")
            )
            if is_bold:
                c.setFont("Courier-Bold", 9)
            else:
                c.setFont("Courier", 8)

            text_w = c.stringWidth(stripped, c._fontname, c._fontsize)
            if "MART" in stripped.upper() or stripped in (MART_NAME.upper(),):
                c.setFont("Courier-Bold", 12)
                text_w = c.stringWidth(stripped, "Courier-Bold", 12)
                x = (width - text_w) / 2
            elif stripped and (stripped == stripped.center(48).strip() and len(stripped) < 40
                               and not any(c2.isdigit() for c2 in stripped[:4])):
                x = (width - text_w) / 2
            else:
                x = 3

            c.drawString(x, y, stripped if stripped else "")
            y -= 11
            if y < 8:
                c.showPage()
                y = height - 8

        c.save()

    def _save_and_clear(self):
        if self.parent_pos:
            if "DUE" in self.parent_pos._get_payment():
                self.parent_pos._add_to_dues()
                return
            self.parent_pos._save_transaction()
            self.parent_pos._add_points()
            self.parent_pos._clear_all(skip_confirm=True)


class HeldBillsDialog(QDialog):
    recall = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Held Bills")
        self.resize(700, 420)
        self.setStyleSheet(STYLESHEET)
        self._build()

    def _build(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)

        ttl = QLabel("⏸  Held Bills")
        ttl.setStyleSheet(f"font-size:18px;font-weight:700;color:{C_TEXT};")
        l.addWidget(ttl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Customer", "Items", "Total", "Time"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        l.addWidget(self.table)

        btn_row = QHBoxLayout()
        recall_btn = QPushButton("↩  Recall Bill")
        recall_btn.setObjectName("accentBtn")
        recall_btn.setFixedHeight(38)
        recall_btn.clicked.connect(self._recall)
        btn_row.addWidget(recall_btn)

        del_btn = QPushButton("🗑  Delete")
        del_btn.setObjectName("redBtn")
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedHeight(38)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        l.addLayout(btn_row)

        self._load()

    def _load(self):
        self.table.setRowCount(0)
        self.held = load_held_bills()
        for i, b in enumerate(self.held):
            r = self.table.rowCount()
            self.table.insertRow(r)
            for col, val in enumerate([
                b.get('bill_no',''),
                b.get('customer','Walk-in'),
                str(len(b.get('items',[]))),
                f"₹{b.get('grand',0):.2f}",
                b.get('held_at','')
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, col, item)

    def _recall(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select", "Select a held bill to recall.")
            return
        bill = self.held[row]
        self.recall.emit(bill)
        self.held.pop(row)
        save_held_bills(self.held)
        self.accept()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "Confirm", "Delete this held bill?") == QMessageBox.Yes:
            self.held.pop(row)
            save_held_bills(self.held)
            self._load()