from PySide6.QtWidgets import QDialog, QHBoxLayout, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from config import *
from auth import UserManager

class LoginWindow(QDialog):
    login_success = Signal(dict)

    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
        self.setWindowTitle("Login")
        self.setFixedSize(700, 440)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(STYLESHEET)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        brand = QWidget()
        brand.setFixedWidth(320)
        brand.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3d2f99,stop:1 #7c6aff);
        """)
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(30, 40, 30, 30)
        bl.setSpacing(10)
        bl.setAlignment(Qt.AlignCenter)

        try:
            logo_lbl = QLabel()
            logo_lbl.setStyleSheet("background:transparent;border:none;")
            raw_pix = QPixmap(LOGO_PATH)
            if not raw_pix.isNull():
                pix = raw_pix.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_lbl.setPixmap(pix)
                logo_lbl.setFixedSize(90, 90)
                logo_lbl.setAlignment(Qt.AlignCenter)
            bl.addWidget(logo_lbl, 0, Qt.AlignCenter)
        except Exception:
            pass

        bl.addSpacing(12)

        mart_name = QLabel(MART_NAME.upper())
        mart_name.setStyleSheet("color:white;font-size:24px;font-weight:900;letter-spacing:3px;background:transparent;border:none;")
        mart_name.setAlignment(Qt.AlignCenter)
        bl.addWidget(mart_name)

        tagline_lbl = QLabel(TAGLINE)
        tagline_lbl.setStyleSheet("color:rgba(255,255,255,0.80);font-size:13px;font-weight:500;background:transparent;border:none;")
        tagline_lbl.setAlignment(Qt.AlignCenter)
        bl.addWidget(tagline_lbl)

        bl.addSpacing(16)

        addr_lbl = QLabel(f"📍 {ADDRESS}")
        addr_lbl.setStyleSheet("color:rgba(255,255,255,0.65);font-size:11px;background:transparent;border:none;")
        addr_lbl.setAlignment(Qt.AlignCenter)
        addr_lbl.setWordWrap(True)
        bl.addWidget(addr_lbl)

        bl.addStretch()

        credit_frame = QWidget()
        credit_frame.setStyleSheet("background: transparent; border: none;")
        cf_layout = QVBoxLayout(credit_frame)
        cf_layout.setContentsMargins(0, 0, 0, 0)
        cf_layout.setSpacing(4)
        cf_layout.setAlignment(Qt.AlignCenter)

        designed_lbl = QLabel("Powered by")
        designed_lbl.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 14px; font-weight: 600; background: transparent; border: none;")
        designed_lbl.setAlignment(Qt.AlignCenter)
        cf_layout.addWidget(designed_lbl)

        logo_lbl = QLabel()
        logo_pix = QPixmap("logo.png")
        if not logo_pix.isNull():
            logo_lbl.setPixmap(logo_pix.scaled(250, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("adaptare UI")
            logo_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: 900; background: transparent; border: none;")
        
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        cf_layout.addWidget(logo_lbl)

        email_lbl = QLabel("adnan.uc3m@gmail.com")
        email_lbl.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 14px; font-weight: 600; background: transparent; border: none;")
        email_lbl.setAlignment(Qt.AlignCenter)
        cf_layout.addWidget(email_lbl)

        bl.addWidget(credit_frame)

        outer.addWidget(brand)

        form_w = QWidget()
        form_w.setStyleSheet(f"background:{C_BG};")
        layout = QVBoxLayout(form_w)
        layout.setContentsMargins(50, 50, 50, 40)
        layout.setSpacing(0)

        welcome = QLabel("Welcome back")
        welcome.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        welcome.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome)

        title = QLabel("Sign in to continue")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 22px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(28)

        lbl_u = QLabel("Username")
        lbl_u.setStyleSheet(f"color: {C_TEXT}; font-weight: 600; font-size: 13px;")
        layout.addWidget(lbl_u)
        layout.addSpacing(4)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setMinimumHeight(46)
        self.username_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {C_SURFACE2};
                border: 1.5px solid {C_BORDER};
                border-radius: 9px;
                padding: 6px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {C_ACCENT}; }}
        """)
        layout.addWidget(self.username_edit)
        layout.addSpacing(14)

        lbl_p = QLabel("Password")
        lbl_p.setStyleSheet(f"color: {C_TEXT}; font-weight: 600; font-size: 13px;")
        layout.addWidget(lbl_p)
        layout.addSpacing(4)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(46)
        self.password_edit.setStyleSheet(self.username_edit.styleSheet())
        layout.addWidget(self.password_edit)
        layout.addSpacing(24)

        self.sign_btn = QPushButton("Sign In  →")
        self.sign_btn.setMinimumHeight(50)
        self.sign_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3d2f99,stop:1 #7c6aff);
                border: none;
                border-radius: 10px;
                color: white;
                font-weight: 800;
                font-size: 16px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: #6a59e0; }}
            QPushButton:pressed {{ background: #5a49d0; }}
        """)
        self.sign_btn.clicked.connect(self._do_login)
        layout.addWidget(self.sign_btn)
        layout.addSpacing(10)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("color: #ef5350; font-size: 12px;")
        layout.addWidget(self.status_lbl)

        layout.addStretch()

        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self._do_login)
        self.username_edit.setFocus()

        outer.addWidget(form_w)

    def _do_login(self):
        u = self.username_edit.text().strip()
        p = self.password_edit.text().strip()
        if not u or not p:
            self.status_lbl.setText("Please enter username and password")
            return
        if self.user_manager.verify_login(u, p):
            self.login_success.emit(self.user_manager.current_user)
            self.accept()
        else:
            self.status_lbl.setText("⚠  Invalid username or password")
            self.password_edit.clear()
            self.password_edit.setFocus()