"""
CAD Studio — 3-Page Desktop App
=================================
pip install PyQt6 pyqtgraph PyOpenGL ezdxf trimesh numpy
"""

import sys, os, json
from pathlib import Path
from datetime import datetime


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QFileDialog, QLineEdit,
    QTextEdit, QSizePolicy, QSpacerItem, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, QObject
from PyQt6.QtGui import QCursor, QFont, QColor

from core.database import DatabaseManager
from core.pipeline_manager import PipelineManager

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import ezdxf
import trimesh
import numpy as np

# ─── Recent projects storage ────────────────────────────
RECENTS_FILE = Path.home() / ".cad_studio_recents.json"

def load_recents():
    if RECENTS_FILE.exists():
        try:
            return json.loads(RECENTS_FILE.read_text())
        except Exception:
            return []
    return []

def save_recents(paths: list):
    RECENTS_FILE.write_text(json.dumps(paths))

def add_recent(path: str):
    recents = load_recents()
    if path in recents:
        recents.remove(path)
    recents.insert(0, path)
    recents = recents[:20]
    save_recents(recents)


# ─────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────
#  GLOBAL STYLE (Unified Design System)
# ─────────────────────────────────────────────────────────
STYLE = """
* { 
    font-family: 'Segoe UI', 'JetBrains Mono', sans-serif; 
}

QMainWindow, QWidget { 
    background: #0d0d1a; 
    color: #cdd6f4; 
}

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: #0b0b18; width: 4px; border-radius: 2px;
}
QScrollBar::handle:vertical {
    background: #3a2a68; border-radius: 2px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #7c3aed; }

/* ── Home Page (Screen 1) ── */
QLabel#h1_title { 
    color: #ffffff; 
    font-size: 32px; 
    font-weight: 800; 
    letter-spacing: 1px;
}
QLabel#sub_title { 
    color: #8880a8; 
    font-size: 13px; 
    letter-spacing: 1px;
}

/* ── Feature Cards (image + overlay style) ── */
QFrame#feature_card {
    border-radius: 18px;
    border: 1.5px solid #2a2a50;
    background: #111128;
}
QFrame#feature_card:hover {
    border-color: #7c3aed;
}

QLabel#card_icon {
    font-size: 28px;
    background: transparent;
    color: #cdd6f4;
}
QLabel#card_title {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
    background: transparent;
}
QLabel#card_desc {
    font-size: 11px;
    color: #9090b0;
    background: transparent;
}
QLabel#card_badge {
    font-size: 10px;
    color: #a090ff;
    background: #1a1040;
    border: 1px solid #3a2a70;
    border-radius: 8px;
    padding: 2px 10px;
}

QPushButton#btn_card_3d {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #4f46e5);
    color: white;
    border: none;
    border-radius: 22px;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 28px;
    min-width: 180px;
}
QPushButton#btn_card_3d:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6d28d9, stop:1 #4338ca);
}

QPushButton#btn_card_2d {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #c2410c, stop:1 #ea580c);
    color: white;
    border: none;
    border-radius: 22px;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 28px;
    min-width: 180px;
}
QPushButton#btn_card_2d:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #b91c1c, stop:1 #dc2626);
}

QPushButton#btn_primary {
    background: #7c3aed;
    color: white;
    border: none;
    border-radius: 9px;
    font-size: 13px;
    font-weight: 700;
    padding: 12px 40px;
}
QPushButton#btn_primary:disabled {
    background: #1a1035;
    color: #40405a;
    opacity: 0.3;
}
QPushButton#btn_primary:hover:!disabled {
    background: #6d28d9;
}

/* ── Editor UI (Screen 2) ── */
QWidget#editor_sidebar {
    background: #0b0b18;
    border-right: 1px solid #1a1a30;
}
QWidget#topbar {
    background: #0b0b18;
    border-bottom: 0.5px solid #1a1a30;
}
QLabel#logo { color: #8060d0; font-size: 13px; font-weight: 700; letter-spacing: 1px; }

QScrollArea#chat_log_scroll { background: transparent; border: none; }

/* ── Bubbles ── */
QFrame#bubble_ai {
    background: #1a1035;
    border: 0.5px solid #3a2060;
    border-radius: 12px;
    padding: 2px;
    margin-bottom: 4px;
}
QLabel#bubble_text_ai { color: #b090e0; font-size: 11px; }

QFrame#bubble_user {
    background: #131328;
    border: 0.5px solid #222240;
    border-radius: 12px;
    padding: 2px;
    margin-bottom: 4px;
}
QLabel#bubble_text_user { color: #9090c0; font-size: 11px; }

/* ── Input Zone ── */
QFrame#input_box_area {
    background: #13132a;
    border: 0.5px solid #2a2a45;
    border-radius: 10px;
}
QTextEdit#chat_input_field {
    background: transparent;
    color: #c0c0e0;
    border: none;
    font-size: 12px;
}

QPushButton#btn_chat_action {
    background: transparent;
    border: none;
    color: #6050a0;
    font-size: 16px;
    padding: 0;
}
QPushButton#btn_chat_action::menu-indicator {
    image: none;
}
QPushButton#btn_chat_action:hover {
    color: #a090e0;
}

/* ── Viewport ── */
QWidget#viewport_toolbar {
    background: #0b0b18;
    border-bottom: 0.5px solid #1a1a30;
    min-height: 34px;
}
QPushButton#v_tool_btn {
    background: transparent;
    border: 0.5px solid #2a2a40;
    border-radius: 5px;
    color: #505070;
    font-size: 10px;
    padding: 3px 8px;
}
QPushButton#v_tool_btn:hover { background: #141428; color: #8080b0; border-color: #4a4a70; }

QLabel#viewport_hint { color: #3a2a68; font-size: 14px; font-weight: 600; }

/* ── Workspace Chip ── */
QPushButton#workspace_chip {
    background: #141428;
    border-radius: 10px;
    border: 0.5px solid #2a2a45;
    color: #70708f;
    font-size: 10px;
    padding-right: 12px;
}
QPushButton#workspace_chip:hover {
    background: #1a1a35;
    border-color: #7c3aed;
}
QPushButton#workspace_chip::menu-indicator {
    image: none;
}

QPushButton#btn_clear_viewport {
    background: transparent;
    border: 0.5px solid #2a2a40;
    border-radius: 5px;
    color: #40405a;
    font-size: 10px;
    padding: 4px 10px;
}
QPushButton#btn_clear_viewport:hover { color: #ff6b6b; border-color: #ff6b6b; }

QPushButton#btn_details_toggle {
    background: transparent;
    border: none;
    color: #40405a;
    font-size: 10px;
    font-weight: bold;
    padding: 5px;
}
QPushButton#btn_details_toggle:hover { color: #7c3aed; }

QPushButton#btn_ghost_small, QPushButton#btn_autocad {
    background: #131328;
    border: 1px solid #2a2a45;
    border-radius: 6px;
    color: #8080b0;
    font-size: 10px;
    font-weight: bold;
    padding: 6px 12px;
}
QPushButton#btn_ghost_small:hover, QPushButton#btn_autocad:hover {
    background: #1a1a35;
    border-color: #7c3aed;
    color: #c0b0ff;
}
QPushButton#btn_autocad {
    color: #7c3aed;
}

QLineEdit#inp_small {
    background: #13132a;
    border: 0.5px solid #2a2a45;
    border-radius: 4px;
    color: #c0c0e0;
    font-size: 10px;
    padding: 2px 4px;
}

/* ── Sign In Page ── */
QWidget#signin_container {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 #1a1035, stop:1 #08080f);
}

QLabel#login_title {
    font-size: 38px;
    font-weight: 900;
    color: #ffffff;
    margin-bottom: 5px;
}

QLabel#login_subtitle {
    font-size: 14px;
    color: #8880a8;
    margin-bottom: 20px;
}

QFrame#login_card {
    background: rgba(17, 17, 40, 0.7);
    border: 1px solid #2a2a50;
    border-radius: 20px;
}

QLineEdit#login_input {
    background: #1a1a35;
    border: 1px solid #2a2a45;
    border-radius: 8px;
    color: #ffffff;
    font-size: 13px;
    padding: 12px 16px;
}
QLineEdit#login_input:focus {
    border-color: #7c3aed;
}

QPushButton#btn_login_primary {
    background: #7c3aed;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    padding: 12px;
}
QPushButton#btn_login_primary:hover {
    background: #6d28d9;
}

QPushButton#btn_google_signin {
    background: #ffffff;
    color: #1f1f1f;
    border: 1px solid #dadce0;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    padding: 10px;
}
QPushButton#btn_google_signin:hover {
    background: #f8f9fa;
    border-color: #d2e3fc;
}

QLabel#login_footer {
    font-size: 12px;
    color: #63638a;
}

/* ── Settings Page ── */
QWidget#settings_page {
    background-color: #121212;
}
QFrame#settings_section {
    background-color: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 14px;
}
QLabel#settings_section_title {
    font-size: 11px;
    font-weight: 700;
    color: #e53935;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}
QLabel#settings_field_label {
    font-size: 13px;
    color: #999999;
}
QLabel#settings_value {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
}
QLabel#settings_page_title {
    font-size: 28px;
    font-weight: 800;
    color: #ffffff;
}
QFrame#history_row {
    background-color: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 12px;
}
QFrame#history_row:hover {
    border-color: #3d3d3d;
    background-color: #252525;
}
QLabel#history_status_done {
    color: #4caf50;
    background-color: rgba(76, 175, 80, 0.12);
    border: 1px solid rgba(76, 175, 80, 0.25);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#history_status_fail {
    color: #e53935;
    background-color: rgba(229, 57, 53, 0.12);
    border: 1px solid rgba(229, 57, 53, 0.25);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#history_status_pend {
    color: #ff9800;
    background-color: rgba(255, 152, 0, 0.12);
    border: 1px solid rgba(255, 152, 0, 0.25);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#history_prompt {
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
}
QLabel#history_meta {
    color: #888888;
    font-size: 11px;
}
QLineEdit#cad_path_input {
    background-color: #121212;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #ffffff;
    font-size: 12px;
    padding: 10px 14px;
}
QLineEdit#cad_path_input:focus {
    border-color: #e53935;
}
QPushButton#btn_settings_back {
    background-color: transparent;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #999999;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 20px;
}
QPushButton#btn_settings_back:hover {
    border-color: #3d3d3d;
    color: #ffffff;
    background-color: #1a1a1a;
}
QPushButton#btn_save_path {
    background-color: #e53935;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 20px;
}
QPushButton#btn_save_path:hover {
    background-color: #d32f2f;
}
QPushButton#btn_settings_icon {
    background-color: transparent;
    border: none;
    color: #555555;
    font-size: 18px;
    padding: 2px 6px;
}
QPushButton#btn_settings_icon:hover {
    color: #e53935;
}
QLineEdit#history_search {
    background-color: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #ffffff;
    font-size: 13px;
    padding: 10px 14px;
}
QLineEdit#history_search:focus {
    border-color: #e53935;
}
QPushButton#filter_btn_active {
    background-color: #e53935;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 16px;
}
QPushButton#filter_btn_inactive {
    background-color: #1e1e1e;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #999999;
    font-size: 12px;
    padding: 6px 16px;
}
QPushButton#filter_btn_inactive:hover {
    border-color: #3d3d3d;
    color: #ffffff;
}
QPushButton#btn_clear_history {
    background-color: transparent;
    border: 1px solid #e53935;
    border-radius: 8px;
    color: #e53935;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
}
QPushButton#btn_clear_history:hover {
    background-color: #e53935;
    color: #ffffff;
}
"""


# ─────────────────────────────────────────────────────────
#  PAGE 0 — SIGN IN
# ─────────────────────────────────────────────────────────
class SignInPage(QWidget):
    authenticated = pyqtSignal(str, str, str) # user_id, name, email

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName("signin_container")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Center card
        card = QFrame()
        card.setObjectName("login_card")
        card.setFixedSize(400, 520)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 40, 40, 40)
        card_lay.setSpacing(15)

        # Logo / Title
        title_lbl = QLabel("CAD Studio")
        title_lbl.setObjectName("login_title")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub_lbl = QLabel("Sign in to your account")
        sub_lbl.setObjectName("login_subtitle")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Inputs
        self.email_input = QLineEdit()
        self.email_input.setObjectName("login_input")
        self.email_input.setPlaceholderText("Email address")
        
        self.pass_input = QLineEdit()
        self.pass_input.setObjectName("login_input")
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Login button
        btn_login = QPushButton("Sign In")
        btn_login.setObjectName("btn_login_primary")
        btn_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_login.clicked.connect(self._handle_login)

        # Divider
        divider_lay = QHBoxLayout()
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setStyleSheet("color: #2a2a45;")
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("color: #2a2a45;")
        or_lbl = QLabel("or"); or_lbl.setStyleSheet("color: #63638a; font-size: 11px;")
        divider_lay.addWidget(line1); divider_lay.addWidget(or_lbl); divider_lay.addWidget(line2)

        # Google Button
        btn_google = QPushButton("  Sign in with Google")
        btn_google.setObjectName("btn_google_signin")
        btn_google.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # icon could be added here
        btn_google.clicked.connect(self._handle_google_login)

        # Footer
        footer = QLabel("Don't have an account? Sign up")
        footer.setObjectName("login_footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_lay.addWidget(title_lbl)
        card_lay.addWidget(sub_lbl)
        card_lay.addSpacing(10)
        card_lay.addWidget(self.email_input)
        card_lay.addWidget(self.pass_input)
        card_lay.addWidget(btn_login)
        card_lay.addSpacing(10)
        card_lay.addLayout(divider_lay)
        card_lay.addSpacing(10)
        card_lay.addWidget(btn_google)
        card_lay.addStretch()
        card_lay.addWidget(footer)

        root.addWidget(card)

    def _handle_login(self):
        email = self.email_input.text().strip()
        pw = self.pass_input.text().strip()
        if not email or not pw:
            return
            
        # Check DB
        user = self.db.get_user_by_email(email)
        if user:
            # In a real app, verify hash
            self.authenticated.emit(user[0], user[1], user[2])
        else:
            # Create a mock user for demo if it doesn't exist?
            # Or just show error. For now, let's allow "guest" or any email for demo.
            uid = self.db.create_user(email.split('@')[0], email, "mock_hash")
            self.authenticated.emit(uid, email.split('@')[0], email)

    def _handle_google_login(self):
        # Mock Google Auth Process
        self.btn_google = self.findChild(QPushButton, "btn_google_signin")
        self.btn_google.setText("  Connecting to Google...")
        self.btn_google.setEnabled(False)
        
        # Simulate a small delay for the "OAuth" flow
        QTimer.singleShot(1500, self._complete_google_login)

    def _complete_google_login(self):
        # Simulate successful return from Google
        google_email = "user.google@gmail.com"
        google_name = "Google User"
        
        user = self.db.get_user_by_email(google_email)
        if not user:
            uid = self.db.create_user(google_name, google_email, "google_oauth_token")
        else:
            uid = user[0]
            
        self.authenticated.emit(uid, google_name, google_email)


# ─────────────────────────────────────────────────────────
#  PAGE 1 — HOME
# ─────────────────────────────────────────────────────────
class HomePage(QWidget):
    # signals for mode picked
    modePicked = pyqtSignal(str, str) # mode, path

    def __init__(self):
        super().__init__()
        self._selected_mode = None
        self._build()

    def _build(self):
        from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush
        from PyQt6.QtCore import QRect

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Background wrapper ─────────────────────────────
        self.setStyleSheet("background: #08080f;")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # ── Scroll container ───────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(60, 60, 60, 60)
        vbox.setSpacing(0)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Hero Title ─────────────────────────────────────
        hero = QVBoxLayout()
        hero.setSpacing(8)
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("Generate Anything in CAD")
        lbl_title.setObjectName("h1_title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel("Your All-in-One AI CAD Workspace")
        lbl_sub.setObjectName("sub_title")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hero.addWidget(lbl_title)
        hero.addWidget(lbl_sub)
        vbox.addLayout(hero)
        vbox.addSpacing(48)

        # ── Cards Row ──────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)
        cards_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_3d = self._create_feature_card(
            mode_id="3d",
            icon="🧊",
            title="High Detail 3D Model",
            desc="Up to 2 Million Polygons for 3D\nPrinting & Visual Art",
            badge="STL",
            btn_text="Generate 3D Model  →",
            btn_name="btn_card_3d",
            img_path=os.path.join(script_dir, "assets", "hero_3d.png"),
            accent="#7c3aed"
        )
        card_2d = self._create_feature_card(
            mode_id="2d",
            icon="📐",
            title="Smart 2D Blueprint",
            desc="~2s  |  Clean Topology for CAD,\nGames & Engineering",
            badge="DXF",
            btn_text="Generate 2D Layout  →",
            btn_name="btn_card_2d",
            img_path=os.path.join(script_dir, "assets", "hero_2d.png"),
            accent="#ea580c"
        )

        cards_row.addWidget(card_3d)
        cards_row.addWidget(card_2d)
        vbox.addLayout(cards_row)
        vbox.addSpacing(40)

        # ── Bottom tagline ─────────────────────────────────
        tagline = QLabel("✦  AI-Powered CAD Generation — From Text, Image or File")
        tagline.setStyleSheet(
            "color: #3a2a68; font-size: 11px; letter-spacing: 1px; background:transparent;"
        )
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(tagline)

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _create_feature_card(self, mode_id, icon, title, desc, badge,
                              btn_text, btn_name, img_path, accent):
        from PyQt6.QtGui import QPixmap

        card = QFrame()
        card.setObjectName("feature_card")
        card.setFixedSize(460, 380)
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # ── Image banner (full image, no crop) ────────────
        img_frame = QLabel()
        img_frame.setFixedSize(460, 220)
        img_frame.setScaledContents(True)
        img_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_frame.setStyleSheet(
            "border-radius: 16px 16px 0 0;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 #1a1035, stop:1 #0d0820);"
        )

        print(f"DEBUG: Loading card image from: {img_path}")
        if not os.path.exists(img_path):
            print(f"DEBUG ERROR: File does not exist at {img_path}")
            
        pix = QPixmap(img_path)
        if pix.isNull():
            print(f"DEBUG ERROR: QPixmap failed to load {img_path}")
        else:
            img_frame.setPixmap(pix)
        card_lay.addWidget(img_frame)

        # ── Content panel ──────────────────────────────────
        content = QWidget()
        content.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f" stop:0 #12102a, stop:1 #0e0c20);"
            f"border-radius: 0 0 16px 16px;"
        )
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(8)

        # Icon + badge row
        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("card_icon")
        badge_lbl = QLabel(badge)
        badge_lbl.setObjectName("card_badge")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()
        top_row.addWidget(badge_lbl)
        c_lay.addLayout(top_row)

        # Title
        t_lbl = QLabel(title)
        t_lbl.setObjectName("card_title")
        t_lbl.setWordWrap(True)
        c_lay.addWidget(t_lbl)

        # Description
        d_lbl = QLabel(desc)
        d_lbl.setObjectName("card_desc")
        d_lbl.setWordWrap(True)
        c_lay.addWidget(d_lbl)

        c_lay.addStretch()

        # CTA Button
        btn = QPushButton(btn_text)
        btn.setObjectName(btn_name)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFixedHeight(42)
        btn.clicked.connect(lambda checked=False, m=mode_id: self._select_mode(m))
        c_lay.addWidget(btn)

        card_lay.addWidget(content)

        # Make whole card clickable
        card.mousePressEvent = lambda e, m=mode_id: self._select_mode(m)

        return card

    def _select_mode(self, mode_id):
        # Immediate navigation on click
        mode_str = "3D" if mode_id == "3d" else "2D"
        self.modePicked.emit(mode_str, "")



# ─────────────────────────────────────────────────────────
#  FILE ROW WIDGET
# ─────────────────────────────────────────────────────────
EXT_COLORS = {
    "dxf": ("#7b2fff", "#7b2fff22"),
    "stl": ("#00aaff", "#00aaff22"),
    "png": ("#ff6b6b", "#ff6b6b22"),
    "jpg": ("#ff6b6b", "#ff6b6b22"),
    "jpeg":("#ff6b6b", "#ff6b6b22"),
    "svg": ("#ffaa00", "#ffaa0022"),
}

class FileRow(QFrame):
    clicked = pyqtSignal(str)   # emits file path

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.setObjectName("file_row")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        filename = Path(filepath).name
        ext = Path(filepath).suffix.lstrip('.').lower()
        fg, bg = EXT_COLORS.get(ext, ("#888", "#88888822"))

        ext_lbl = QLabel(ext.upper() or "FILE")
        ext_lbl.setObjectName("file_ext")
        ext_lbl.setStyleSheet(f"color:{fg}; background:{bg}; border-radius:4px;")
        ext_lbl.setFixedWidth(40)
        ext_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name_lbl = QLabel(filename)
        name_lbl.setObjectName("file_name")

        layout.addWidget(ext_lbl)
        layout.addWidget(name_lbl)
        layout.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit(self.filepath)


# ─────────────────────────────────────────────────────────
#  PAGE 2 — PROJECT
# ─────────────────────────────────────────────────────────
class ProjectPage(QWidget):
    go_back      = pyqtSignal()
    open_editor  = pyqtSignal(str, str)  # (mode "2D"/"3D", folder_path)

    def __init__(self):
        super().__init__()
        self._folder = ""
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(52)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(24, 0, 24, 0)

        btn_back = QPushButton("← Back")
        btn_back.setObjectName("btn_back")
        btn_back.clicked.connect(self.go_back.emit)

        self.title_lbl = QLabel("Project")
        self.title_lbl.setObjectName("h2")

        tb.addWidget(btn_back)
        tb.addSpacing(16)
        tb.addWidget(self.title_lbl)
        tb.addStretch()
        root.addWidget(topbar)

        # ── Content ──────────────────────────────────────
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(28)

        # 2D / 3D mode selector
        mode_lbl = QLabel("CHOOSE MODE")
        mode_lbl.setObjectName("section_header")
        cl.addWidget(mode_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        btn_2d = QPushButton("◧  2D")
        btn_2d.setObjectName("action_card")
        btn_2d.setFixedHeight(88)
        btn_2d.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_2d.clicked.connect(lambda: self.open_editor.emit("2D", self._folder))

        btn_3d = QPushButton("◈  3D")
        btn_3d.setObjectName("action_card")
        btn_3d.setFixedHeight(88)
        btn_3d.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_3d.clicked.connect(lambda: self.open_editor.emit("3D", self._folder))

        btn_row.addWidget(btn_2d)
        btn_row.addWidget(btn_3d)
        cl.addLayout(btn_row)

        # Files section
        files_lbl = QLabel("PROJECT FILES")
        files_lbl.setObjectName("section_header")
        cl.addWidget(files_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.files_container = QWidget()
        self.files_container.setStyleSheet("background:transparent;")
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(6)
        self.files_layout.addStretch()

        scroll.setWidget(self.files_container)
        cl.addWidget(scroll)

        root.addWidget(content)

    def load_project(self, folder: str):
        self._folder = folder
        self.title_lbl.setText(Path(folder).name)

        # Clear old files
        while self.files_layout.count() > 1:
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        supported = {'.dxf', '.stl', '.png', '.jpg', '.jpeg', '.svg'}
        files = [
            f for f in Path(folder).iterdir()
            if f.is_file() and f.suffix.lower() in supported
        ]

        if not files:
            lbl = QLabel("No supported files found in this folder.\n(DXF, STL, PNG, JPG, SVG)")
            lbl.setObjectName("muted")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_layout.insertWidget(0, lbl)
            return

        for f in sorted(files):
            row = FileRow(str(f))
            ext = f.suffix.lower()
            inferred_mode = "3D" if ext == ".stl" else "2D"
            row.clicked.connect(lambda path, m=inferred_mode: self._open_with_file(m, path))
            self.files_layout.insertWidget(self.files_layout.count() - 1, row)

    def _open_with_file(self, mode: str, filepath: str):
        """Open editor pre-loaded with a file from the project file list."""
        self.open_editor.emit(mode, filepath)


# ─────────────────────────────────────────────────────────
#  VIEWPORT WIDGET
# ─────────────────────────────────────────────────────────
class ViewportWidget(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("viewport_area")
        self.current_file = ""

        # Page 0: Placeholder
        self.placeholder = QFrame()
        self.placeholder.setObjectName("viewport_placeholder")
        ph_layout = QVBoxLayout(self.placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.setSpacing(10)
        
        icon = QLabel("◫")
        icon.setStyleSheet("color:#7b2fff; font-size:52px; background:transparent; border:none;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        obj_title = QLabel("Viewport")
        obj_title.setStyleSheet("color:#cdd6f4; font-size:18px; font-weight:bold; background:transparent;")
        obj_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        obj_sub = QLabel("Your model will appear here")
        obj_sub.setObjectName("muted")
        obj_sub.setStyleSheet("color:#6c7086; font-size:12px; background:transparent;")
        obj_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ph_layout.addWidget(icon)
        ph_layout.addWidget(obj_title)
        ph_layout.addWidget(obj_sub)
        self.addWidget(self.placeholder)

        # Page 1: 2D Viewer (PyQtGraph)
        self.view_2d = pg.PlotWidget()
        self.view_2d.setBackground('#11111b')
        self.view_2d.showGrid(x=True, y=True)
        self.addWidget(self.view_2d)

        # Page 2: 3D Viewer (OpenGL)
        self.view_3d = gl.GLViewWidget()
        self.view_3d.setBackgroundColor('#11111b')
        # Add a grid
        grid = gl.GLGridItem()
        grid.scale(10, 10, 1)
        self.view_3d.addItem(grid)
        self.addWidget(self.view_3d)

    def show_placeholder(self):
        self.setCurrentIndex(0)

    def clear_view(self):
        self.current_file = ""
        # Clear 2D
        self.view_2d.clear()
        # Clear 3D
        for item in list(self.view_3d.items):
            if not isinstance(item, gl.GLGridItem):
                self.view_3d.removeItem(item)
        self.show_placeholder()

    def display_file(self, file_path: str):
        self.current_file = file_path
        if not file_path or not os.path.exists(file_path):
            self.current_file = ""
            self.show_placeholder()
            return

        ext = Path(file_path).suffix.lower()
        if ext == '.dxf':
            self._display_dxf(file_path)
        elif ext == '.stl':
            self._display_stl(file_path)
        else:
            self.show_placeholder()

    def _display_dxf(self, path):
        try:
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            self.view_2d.clear()
            
            # Simple rendering of lines and circles
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    self.view_2d.plot([start.x, end.x], [start.y, end.y], pen=pg.mkPen('#7b2fff', width=2))
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    # Approximate circle with points
                    t = np.linspace(0, 2*np.pi, 100)
                    x = center.x + radius * np.cos(t)
                    y = center.y + radius * np.sin(t)
                    self.view_2d.plot(x, y, pen=pg.mkPen('#7b2fff', width=2))
                elif entity.dxftype() == 'LWPOLYLINE':
                    points = entity.get_points()
                    x = [p[0] for p in points]
                    y = [p[1] for p in points]
                    self.view_2d.plot(x, y, pen=pg.mkPen('#7b2fff', width=2))
            
            self.view_2d.autoRange()
            self.setCurrentIndex(1)
        except Exception as e:
            print(f"Error loading DXF: {e}")
            self.show_placeholder()

    def _display_stl(self, path):
        try:
            mesh = trimesh.load(path)
            # Clear old items (except grid)
            for item in list(self.view_3d.items):
                if not isinstance(item, gl.GLGridItem):
                    self.view_3d.removeItem(item)
            
            # Create GL mesh
            verts = mesh.vertices
            faces = mesh.faces
            meshdata = gl.MeshData(vertexes=verts, faces=faces)
            mesh_item = gl.GLMeshItem(meshdata=meshdata, smooth=True, color=(123/255, 47/255, 255/255, 1.0), shader='shaded')
            
            self.view_3d.addItem(mesh_item)
            
            # Calculate bounds to set camera
            bounds = mesh.bounds
            center = mesh.centroid
            size = np.linalg.norm(bounds[1] - bounds[0])
            self.view_3d.setCameraPosition(pos=pg.Vector(center[0], center[1], center[2]), distance=size * 1.5)
            
            self.setCurrentIndex(2)
        except Exception as e:
            print(f"Error loading STL: {e}")
            self.show_placeholder()


# ─────────────────────────────────────────────────────────
#  BACKGROUND PIPELINE WORKER
# ─────────────────────────────────────────────────────────
class PipelineWorker(QObject):
    finished = pyqtSignal(str)   # emits output file path
    error    = pyqtSignal(str)   # emits error message

    def __init__(self, pipeline, mode, user_id, project_id, pm, prompt, image_path, params, output_dir=None):
        super().__init__()
        self._pipeline    = pipeline
        self._mode        = mode          # "2D" or "3D"
        self._user_id     = user_id
        self._project_id  = project_id
        self._pm          = pm            # pipeline mode string e.g. "Prompt", "Text3D"
        self._prompt      = prompt
        self._image_path  = image_path
        self._params      = params
        self._output_dir  = output_dir    # workspace folder chosen by user

    def run(self):
        try:
            if self._mode == "2D":
                res = self._pipeline.run_2d_pipeline(
                    user_id=self._user_id,
                    project_id=self._project_id,
                    mode=self._pm,
                    prompt=self._prompt,
                    image_path=self._image_path,
                    params=self._params,
                    output_dir=self._output_dir
                )
            else:
                res = self._pipeline.run_3d_pipeline(
                    user_id=self._user_id,
                    project_id=self._project_id,
                    mode=self._pm,
                    prompt=self._prompt,
                    image_path=self._image_path,
                    params=self._params,
                    output_dir=self._output_dir
                )
            self.finished.emit(res or "")
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────
#  CHAT BUBBLES
# ─────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()
        self.setObjectName("bubble_ai" if is_ai else "bubble_user")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        lbl = QLabel(text)
        lbl.setObjectName("bubble_text_ai" if is_ai else "bubble_text_user")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(lbl)


# ─────────────────────────────────────────────────────────
#  PAGE 3 — EDITOR / VIEWER
# ─────────────────────────────────────────────────────────
class EditorPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self._mode   = "2D"
        self._folder = ""
        self.project_id = None
        self._uploaded_file = ""
        self._details_visible = False
        self.inputs  = {}
        self._build()

    # ── build permanent skeleton ──────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar (Logo, Mode Pill, Back) ────────────────
        self.top_bar = QWidget()
        self.top_bar.setObjectName("topbar")
        self.top_bar.setFixedHeight(50)
        tb_layout = QHBoxLayout(self.top_bar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_layout.setSpacing(12)

        self.logo_lbl = QLabel("CAD·AI")
        self.logo_lbl.setObjectName("logo")
        
        self.mode_pill = QFrame()
        self.mode_pill.setObjectName("mode_pill_frame")
        self.mode_pill.setStyleSheet(
            "QFrame#mode_pill_frame { background: transparent; border: none; }"
        )
        self.mode_pill.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        mp_layout = QHBoxLayout(self.mode_pill)
        mp_layout.setContentsMargins(0, 0, 0, 0)
        mp_layout.setSpacing(4)
        self.mode_icon = QLabel("🧊")
        self.mode_icon.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        self.mode_text = QLabel("3D Mode")
        self.mode_text.setStyleSheet(
            "font-size: 11px; color: #7050b0; font-weight: bold;"
            "background: transparent; border: none;"
        )
        mp_layout.addWidget(self.mode_icon)
        mp_layout.addWidget(self.mode_text)
        self.mode_pill.adjustSize()

        self.btn_autocad = QPushButton("Go to your CAD app")
        self.btn_autocad.setObjectName("btn_autocad")
        self.btn_autocad.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_autocad.clicked.connect(self._open_cad_app)

        self.btn_back = QPushButton("Change mode")
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.setObjectName("btn_ghost_small")
        self.btn_back.clicked.connect(self.go_back.emit)

        tb_layout.addWidget(self.logo_lbl)
        tb_layout.addWidget(self.mode_pill)
        tb_layout.addStretch()
        self.btn_settings_editor = QPushButton("⚙")
        self.btn_settings_editor.setObjectName("btn_settings_icon")
        self.btn_settings_editor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings_editor.setToolTip("Settings")
        tb_layout.addWidget(self.btn_autocad)
        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_settings_editor)
        root.addWidget(self.top_bar)

        # Main Splitter Area
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0,0,0,0)
        body_lay.setSpacing(0)

        # ── LEFT SIDEBAR (Chat-focused) ──────────────────
        self.sidebar = QWidget()
        self.sidebar.setObjectName("editor_sidebar")
        self.sidebar.setFixedWidth(320)
        self.sb_layout = QVBoxLayout(self.sidebar)
        self.sb_layout.setContentsMargins(14, 14, 14, 14)
        self.sb_layout.setSpacing(12)

        # Chat Log Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setObjectName("chat_log_scroll")
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_content)
        self.sb_layout.addWidget(self.chat_scroll, 1)

        # More Details Toggle
        det_row = QHBoxLayout()
        self.btn_details = QPushButton("MORE DETAILS")
        self.btn_details.setObjectName("btn_details_toggle")
        self.btn_details.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_details.clicked.connect(self._toggle_details)
        det_row.addWidget(self.btn_details)
        det_row.addStretch()
        self.sb_layout.addLayout(det_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVisible(False)
        self.inputs_container = QWidget()
        self.inputs_layout = QVBoxLayout(self.inputs_container)
        self.inputs_layout.setSpacing(10)
        self.scroll.setWidget(self.inputs_container)
        self.sb_layout.addWidget(self.scroll)

        # Input Zone Container
        self.input_zone = QWidget()
        iz_lay = QVBoxLayout(self.input_zone)
        iz_lay.setContentsMargins(0, 0, 0, 0)
        iz_lay.setSpacing(8)

        # Floating File Chip
        self.file_chip = QFrame()
        self.file_chip.setObjectName("file_chip_floating")
        self.file_chip.setVisible(False)
        self.file_chip.setStyleSheet(
            "QFrame#file_chip_floating {"
            "  background: #1a1040;"
            "  border: 1px solid #7c3aed;"
            "  border-radius: 10px;"
            "}"
        )
        fc_lay = QHBoxLayout(self.file_chip)
        fc_lay.setContentsMargins(10, 4, 6, 4)
        fc_lay.setSpacing(6)
        self.file_chip_label = QLabel("")
        self.file_chip_label.setStyleSheet("font-size: 10px; color: #b090ff; font-weight: bold; background:transparent;")
        # ✕ remove button
        self.btn_remove_file = QPushButton("✕")
        self.btn_remove_file.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_remove_file.setFixedSize(18, 18)
        self.btn_remove_file.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #7c3aed;"
            "  font-size: 12px; font-weight: bold; padding:0; }"
            "QPushButton:hover { color: #ff6b6b; }"
        )
        self.btn_remove_file.clicked.connect(self._clear_file)
        fc_lay.addWidget(self.file_chip_label)
        fc_lay.addStretch()
        fc_lay.addWidget(self.btn_remove_file)
        iz_lay.addWidget(self.file_chip)

        # Input Box
        self.input_box = QFrame()
        self.input_box.setObjectName("input_box_area")
        box_lay = QVBoxLayout(self.input_box)
        box_lay.setContentsMargins(10, 10, 10, 10)
        box_lay.setSpacing(6)

        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chat_input_field")
        self.chat_input.setPlaceholderText("Describe your request...")
        self.chat_input.setFixedHeight(50)
        box_lay.addWidget(self.chat_input)

        actions_lay = QHBoxLayout()
        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("btn_chat_action")
        self.btn_plus.setFixedSize(24, 24)
        
        # Action Menu for +
        self.plus_menu = QMenu(self)
        self.plus_menu.addAction("@ Set Workspace",     self._pick_workspace)
        self.plus_menu.addAction("📸 Upload Image",   self._pick_image)
        self.plus_menu.addAction("📄 Upload CAD File", self._pick_file)
        self.btn_plus.setMenu(self.plus_menu)
        
        from PyQt6.QtWidgets import QSizePolicy as QSP
        self.ws_chip = QPushButton("📁  workspace")
        self.ws_chip.setObjectName("workspace_chip")
        self.ws_chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ws_chip.clicked.connect(self._show_workspace_files)
        self.ws_chip.setSizePolicy(QSP.Policy.Minimum, QSP.Policy.Fixed)
        self.ws_chip.setStyleSheet(
            "QPushButton#workspace_chip { background:#141428; border-radius:10px; "
            "border:0.5px solid #2a2a45; color:#70708f; font-size:11px; padding:4px 10px; }"
            "QPushButton#workspace_chip:hover { background:#1a1a35; border-color:#7c3aed; }"
            "QPushButton#workspace_chip::menu-indicator { image:none; }"
        )

        actions_lay.addWidget(self.btn_plus)
        actions_lay.addStretch()
        actions_lay.addWidget(self.ws_chip)
        box_lay.addLayout(actions_lay)
        iz_lay.addWidget(self.input_box)

        self.btn_process = QPushButton("Generate")
        self.btn_process.setObjectName("btn_primary")
        self.btn_process.setFixedHeight(38)
        self.btn_process.clicked.connect(self._on_process_clicked)
        iz_lay.addWidget(self.btn_process)

        self.sb_layout.addWidget(self.input_zone)
        body_lay.addWidget(self.sidebar)

        # ── VIEWPORT AREA ───────────────────────────────
        self.vp_container = QWidget()
        vp_lay = QVBoxLayout(self.vp_container)
        vp_lay.setContentsMargins(0, 0, 0, 0)
        vp_lay.setSpacing(0)

        # Viewport Toolbar
        # Viewport Header (Floating Clear)
        self.btn_clear_vp = QPushButton("CLEAR VIEW")
        self.btn_clear_vp.setObjectName("btn_clear_viewport")
        self.btn_clear_vp.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Place clear button at top right before viewport
        vp_lay.addWidget(self.btn_clear_vp, 0, Qt.AlignmentFlag.AlignRight)
        
        self.viewport = ViewportWidget()
        self.btn_clear_vp.clicked.connect(self.viewport.clear_view)
        vp_lay.addWidget(self.viewport, 1)
        
        body_lay.addWidget(self.vp_container, 1)
        root.addWidget(body)

        # Init chat
        self.add_message("AI", "Hello! Choose a mode or upload a file to start.")


    def add_message(self, role: str, text: str):
        bubble = ChatBubble(text, is_ai=(role == "AI"))
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def setup(self, mode: str, folder: str):
        self._mode = mode
        self._folder = folder
        self._uploaded_file = ""
        self.file_chip.setVisible(False)
        self.chat_input.setPlainText("")
        self._details_visible = False
        self.scroll.setVisible(False)
        self.btn_details.setText("MORE DETAILS")
        
        if folder:
            self.ws_chip.setText(f"📁  {Path(folder).name}")
        else:
            self.ws_chip.setText("📁  workspace")
        self.mode_text.setText(f"{mode} Mode")
        self.mode_icon.setText("🧊" if mode == "3D" else "📐")
        
        # Clear chat
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.add_message("AI", f"Welcome to {mode} editor! How can I help you today?")
        self._rebuild_inputs()

    def _show_workspace_files(self):
        if not self._folder:
            self.add_message("AI", "Please set a workspace first using the + menu.")
            return

        # Prepare Menu
        menu = QMenu(self)
        p = Path(self._folder)
        if not p.exists():
            self.add_message("AI", "The workspace folder no longer exists.")
            return

        # Collect files, deduplicate by lowercased name
        seen = set()
        files = []
        for ext in ["*.dxf", "*.stl", "*.obj", "*.step", "*.stp"]:
            for f in list(p.glob(ext)) + list(p.glob(ext.upper())):
                key = f.name.lower()
                if key not in seen:
                    seen.add(key)
                    files.append(f)

        if not files:
            menu.addAction("No CAD files found").setEnabled(False)
        else:
            for f in sorted(files, key=lambda x: x.name.lower()):
                act = menu.addAction(f"📄 {f.name}")
                act.triggered.connect(lambda checked, path=str(f): self.viewport.display_file(path))

        # Show above button
        menu.popup(self.ws_chip.mapToGlobal(self.ws_chip.rect().topLeft()))

    def _toggle_details(self):
        self._details_visible = not self._details_visible
        self.scroll.setVisible(self._details_visible)
        self.btn_details.setText("HIDE DETAILS" if self._details_visible else "MORE DETAILS")

    def _pick_workspace(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self._folder = folder
            self.ws_chip.setText(f"📁  {Path(folder).name}")
            self.ws_chip.adjustSize()
            add_recent(folder)
            
            # Record in DB
            self.project_id = self.win.db.create_project(
                self.win.user_id, 
                Path(folder).name, 
                f"Project folder: {folder}"
            )
            
            self.add_message("AI", f"Workspace synchronized to: {folder}\nProject ID: {self.project_id}")

    def _pick_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Image", self._folder or "", "Images (*.png *.jpg *.jpeg *.svg)")
        if f:
            self._uploaded_file = f
            self.file_chip_label.setText(Path(f).name)
            self.file_chip.setVisible(True)
            self.add_message("User", f"Attached image: {Path(f).name}")
            self._rebuild_inputs()

    def _pick_file(self):
        if self._mode == "2D":
            file_filter = "2D Files (*.dxf *.svg)"
        else:
            file_filter = "3D Files (*.stl *.obj *.step *.stp)"

        f, _ = QFileDialog.getOpenFileName(self, "Select CAD File", self._folder or "", file_filter)
        if f:
            self._uploaded_file = f
            self.file_chip_label.setText(Path(f).name)
            self.file_chip.setVisible(True)
            self.add_message("User", f"Attached model: {Path(f).name}")
            self._rebuild_inputs()
            # Preview if CAD
            ext = Path(f).suffix.lower()
            if ext in {".stl", ".dxf"}:
                self.viewport.display_file(f)

    def _clear_file(self):
        """Remove the currently attached file/image."""
        self._uploaded_file = ""
        self.file_chip_label.setText("")
        self.file_chip.setVisible(False)
        self._rebuild_inputs()

    def _detect_pipeline_mode(self):
        if not self._uploaded_file:
            return "Prompt" if self._mode == "2D" else "Text3D"
            
        ext = Path(self._uploaded_file).suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".svg"}:
            return "Image" if self._mode == "2D" else "Image3D"
            
        return "Edit" if self._mode == "2D" else "Edit3D"

    def _rebuild_inputs(self):
        while self.inputs_layout.count() > 0:
            item = self.inputs_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.inputs = {}
        pm = self._detect_pipeline_mode()

        # Dynamic Placeholder Logic
        if "Prompt" in pm or "Text" in pm:
            self.chat_input.setPlaceholderText("Describe the CAD project you want to generate from scratch...")
            show_details = True
        elif "Image" in pm:
            self.chat_input.setPlaceholderText("Describe the object in the image for CAD generation...")
            show_details = True
        else: # Edit
            self.chat_input.setPlaceholderText("Enter the modifications you want to apply to this file...")
            show_details = False

        # Toggle "More Details" visibility
        self.btn_details.setVisible(show_details)
        if not show_details:
            self._details_visible = False
            self.scroll.setVisible(False)
            self.btn_details.setText("MORE DETAILS")
        
        if show_details:
            # Re-enable the details section if it was visible before toggle, 
            # or just keep the button available.
            self.scroll.setVisible(self._details_visible)

            # Add fields only for generation modes
            if self._mode == "2D":
                self._add_field("part_width_mm",   "PART WIDTH (mm)",    "100.0")
                self._add_field("part_height_mm",  "PART HEIGHT (mm)",   "100.0")
                self._add_field("sheet_width_mm",  "SHEET WIDTH (mm)",   "300.0")
                self._add_field("sheet_height_mm", "SHEET HEIGHT (mm)",  "200.0")
                self._add_field("tool_diameter_mm","TOOL DIAMETER (mm)", "3.0")
                self._add_field("margin_mm",        "MARGIN (mm)",        "10.0")
            else:
                self._add_field("height", "HEIGHT (mm)", "100.0")
                self._add_field("width",  "WIDTH (mm)",  "100.0")
                self._add_field("length", "LENGTH (mm)", "10.0")

    def _add_field(self, key, label_text, default=""):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 10px; color: #70708f;")
        field = QLineEdit()
        field.setPlaceholderText("e.g. 100")
        field.setText("")  # No default — user must fill
        field.setFixedWidth(60)
        field.setObjectName("inp_small")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(field)
        self.inputs[key] = field
        self.inputs_layout.addLayout(row)

    def _on_process_clicked(self):
        # ── Validation ──────────────────────────────────────────────
        if not self._folder or not self.project_id:
            self.add_message("AI", "⚠️ Please set a workspace folder first (use the 📁 button).")
            return

        prompt = self.chat_input.toPlainText().strip()
        pm = self._detect_pipeline_mode()

        if not prompt:
            self.add_message("AI", "⚠️ Please enter a description or command before generating.")
            return

        if self.scroll.isVisible():
            empty_fields = [k for k, v in self.inputs.items() if not v.text().strip()]
            if empty_fields:
                labels = ", ".join(k.upper() for k in empty_fields)
                self.add_message("AI", f"⚠️ Please fill in all required fields: {labels}")
                return
        # ── End Validation ────────────────────────────────────────────

        # Collect params
        params = {}
        for k, v in self.inputs.items():
            try:
                params[k] = float(v.text())
            except ValueError:
                params[k] = 0.0

        self.add_message("User", prompt)
        self.add_message("AI", f"⏳ Starting {pm} pipeline in background... The UI stays responsive.")
        self.chat_input.setPlainText("")

        # ── Disable button while processing ───────────────────────────
        self.btn_process.setEnabled(False)
        self.btn_process.setText("Processing...")

        # ── Create worker + thread ────────────────────────────────────
        self._thread = QThread()
        self._worker = PipelineWorker(
            pipeline=self.win.pipeline,
            mode=self._mode,
            user_id=self.win.user_id,
            project_id=self.project_id,
            pm=pm,
            prompt=prompt,
            image_path=self._uploaded_file,
            params=params,
            output_dir=self._folder or None   # save to user-selected workspace
        )
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_pipeline_finished)
        self._worker.error.connect(self._on_pipeline_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_pipeline_finished(self, res_file: str):
        self.btn_process.setEnabled(True)
        self.btn_process.setText("Generate")
        if res_file and os.path.exists(res_file):
            self.add_message("AI", "✨ Processing complete. Viewport updated!")
            self.viewport.display_file(os.path.abspath(res_file))
        else:
            self.add_message("AI", "❌ Sorry, the pipeline failed to generate the file.")

    def _on_pipeline_error(self, error_msg: str):
        self.btn_process.setEnabled(True)
        self.btn_process.setText("Generate")
        self.add_message("AI", f"❌ Error: {error_msg}")

    def _open_cad_app(self):
        """Launch the user's configured CAD application."""
        path = getattr(self.win, 'cad_app_path', '').strip()
        if not path:
            self.add_message("AI", "⚙️ No CAD app configured. Please set one in Settings.")
            return
        
        # Pass the currently displayed file to the CAD application if exists
        current_file = getattr(self.viewport, 'current_file', '').strip()
        
        try:
            import subprocess
            if current_file and os.path.exists(current_file):
                self.add_message("AI", f"🚀 Launching CAD app with: {os.path.basename(current_file)}")
                subprocess.Popen([path, os.path.abspath(current_file)])
            else:
                self.add_message("AI", "🚀 Launching CAD app...")
                subprocess.Popen([path])
        except Exception as e:
            self.add_message("AI", f"❌ Could not launch CAD app: {e}")


# ─────────────────────────────────────────────────────────
#  PAGE 4 — SETTINGS
# ─────────────────────────────────────────────────────────
class SettingsPage(QWidget):
    go_back = pyqtSignal()
    cad_path_saved = pyqtSignal(str)   # emits the saved path

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self.setObjectName("settings_page")
        self.active_filter = "ALL"  # "ALL", "TODAY", "WEEK"
        self.all_jobs = []          # Store all jobs fetched from DB
        self.user_id = ""
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(56)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(24, 0, 24, 0)

        title_lbl = QLabel("Settings")
        title_lbl.setObjectName("settings_page_title")
        # Ensure Segoe UI or Inter fonts
        title_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff;")

        btn_back = QPushButton("← Back")
        btn_back.setObjectName("btn_settings_back")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.clicked.connect(self.go_back.emit)

        tb.addWidget(btn_back)
        tb.addSpacing(16)
        tb.addWidget(title_lbl)
        tb.addStretch()
        root.addWidget(topbar)

        # ── Scrollable content ───────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        content = QVBoxLayout(container)
        content.setContentsMargins(48, 24, 48, 48)
        content.setSpacing(24)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Section 1: User Profile Card ─────────────────
        profile_card = QFrame()
        profile_card.setObjectName("settings_section")
        prof_layout = QHBoxLayout(profile_card)
        prof_layout.setContentsMargins(24, 24, 24, 24)
        prof_layout.setSpacing(20)

        # Circular Avatar
        self.avatar_lbl = QLabel("")
        self.avatar_lbl.setObjectName("user_avatar")
        self.avatar_lbl.setFixedSize(70, 70)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setStyleSheet(
            "background-color: #e53935; color: #ffffff; border-radius: 35px; "
            "font-size: 24px; font-weight: 800; border: 2px solid #3d3d3d;"
        )

        # Info column
        info_lay = QVBoxLayout()
        info_lay.setSpacing(8)

        self.lbl_name = QLabel("—")
        self.lbl_name.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")

        # Email row
        email_row = QHBoxLayout()
        email_row.setSpacing(6)
        email_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        m_icon = QLabel("✉")
        m_icon.setStyleSheet("color: #888888; font-size: 14px;")
        self.lbl_email = QLabel("—")
        self.lbl_email.setObjectName("settings_value")
        email_row.addWidget(m_icon)
        email_row.addWidget(self.lbl_email)

        # Metadata row (Status Badge + Member Since)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        st_icon = QLabel("👑")
        st_icon.setStyleSheet("color: #888888; font-size: 14px;")
        self.lbl_status = QLabel("Active Account")
        self.lbl_status.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #e53935; "
            "background-color: rgba(229, 57, 53, 0.12); border: 1px solid rgba(229, 57, 53, 0.25); "
            "border-radius: 6px; padding: 3px 8px;"
        )

        dt_icon = QLabel("📅")
        dt_icon.setStyleSheet("color: #888888; font-size: 14px;")
        self.lbl_since = QLabel("—")
        self.lbl_since.setObjectName("settings_field_label")

        meta_row.addWidget(st_icon)
        meta_row.addWidget(self.lbl_status)
        meta_row.addWidget(dt_icon)
        meta_row.addWidget(self.lbl_since)

        info_lay.addWidget(self.lbl_name)
        info_lay.addLayout(email_row)
        info_lay.addLayout(meta_row)

        prof_layout.addWidget(self.avatar_lbl)
        prof_layout.addLayout(info_lay, 1)

        # UID layout on upper-right
        self.lbl_uid = QLabel("—")
        self.lbl_uid.setStyleSheet("font-size: 10px; color: #555555;")
        uid_col = QVBoxLayout()
        uid_col.addWidget(self.lbl_uid, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        prof_layout.addLayout(uid_col)

        content.addWidget(profile_card)

        # ── Section 2: AutoCAD Path ──────────────────────
        cad_card = QFrame()
        cad_card.setObjectName("settings_section")
        cad_lay = QVBoxLayout(cad_card)
        cad_lay.setContentsMargins(24, 20, 24, 24)
        cad_lay.setSpacing(14)

        sec_title = QLabel("🗂  AutoCAD Executable Configuration")
        sec_title.setObjectName("settings_section_title")
        cad_lay.addWidget(sec_title)

        hint = QLabel("Enter or browse to the executable file path of your desktop CAD application.")
        hint.setObjectName("settings_field_label")
        hint.setStyleSheet("color: #888888; font-size: 12px;")
        hint.setWordWrap(True)
        cad_lay.addWidget(hint)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        self.cad_path_input = QLineEdit()
        self.cad_path_input.setObjectName("cad_path_input")
        self.cad_path_input.setReadOnly(True)
        self.cad_path_input.setPlaceholderText("Path to CAD executable (e.g. C:\\Program Files\\Autodesk\\AutoCAD 2024\\acad.exe)")

        btn_browse = QPushButton("📁 Browse")
        btn_browse.setObjectName("btn_settings_back")
        btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_browse.clicked.connect(self._browse_cad)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("btn_save_path")
        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save.clicked.connect(self._save_path)

        path_row.addWidget(self.cad_path_input, 1)
        path_row.addWidget(btn_browse)
        path_row.addWidget(btn_save)
        cad_lay.addLayout(path_row)

        self.path_status = QLabel("")
        self.path_status.setObjectName("settings_field_label")
        cad_lay.addWidget(self.path_status)

        content.addWidget(cad_card)

        # ── Section 3: History ───────────────────────────
        hist_card = QFrame()
        hist_card.setObjectName("settings_section")
        hist_lay = QVBoxLayout(hist_card)
        hist_lay.setContentsMargins(24, 20, 24, 24)
        hist_lay.setSpacing(16)

        hist_title = QLabel("🕓  Generation History")
        hist_title.setObjectName("settings_section_title")
        hist_lay.addWidget(hist_title)

        # Header Search, Filters & Clear row
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("history_search")
        self.search_input.setPlaceholderText("🔍  Search history by prompt, mode, status...")
        self.search_input.textChanged.connect(self._filter_history)

        self.btn_filter_all = QPushButton("All")
        self.btn_filter_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_filter_all.clicked.connect(lambda: self._set_date_filter("ALL"))

        self.btn_filter_today = QPushButton("Today")
        self.btn_filter_today.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_filter_today.clicked.connect(lambda: self._set_date_filter("TODAY"))

        self.btn_filter_week = QPushButton("This Week")
        self.btn_filter_week.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_filter_week.clicked.connect(lambda: self._set_date_filter("WEEK"))

        btn_clear = QPushButton("🗑 Clear History")
        btn_clear.setObjectName("btn_clear_history")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self._clear_all_history)

        header_row.addWidget(self.search_input, 1)
        header_row.addWidget(self.btn_filter_all)
        header_row.addWidget(self.btn_filter_today)
        header_row.addWidget(self.btn_filter_week)
        header_row.addWidget(btn_clear)
        hist_lay.addLayout(header_row)

        # Sub-container for dynamically listed items
        self.history_items_container = QWidget()
        self.history_items_container.setStyleSheet("background: transparent;")
        self.history_list_layout = QVBoxLayout(self.history_items_container)
        self.history_list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list_layout.setSpacing(10)
        hist_lay.addWidget(self.history_items_container)

        content.addWidget(hist_card)

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _browse_cad(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select CAD Application Executable", "",
            "Executable (*.exe);;All Files (*)"
        )
        if f:
            self.cad_path_input.setText(f)
            self._validate_path(f)

    def _save_path(self):
        path = self.cad_path_input.text().strip()
        self.win.cad_app_path = path
        
        # Persist settings in local json config
        persist_file = Path.home() / ".cad_studio_settings.json"
        try:
            settings = {}
            if persist_file.exists():
                settings = json.loads(persist_file.read_text())
            settings["cad_app_path"] = path
            persist_file.write_text(json.dumps(settings))
        except Exception:
            pass

        self._validate_path(path)
        self.cad_path_saved.emit(path)

    def _validate_path(self, path):
        path = path.strip()
        if not path:
            self.path_status.setText("")
            return
        if os.path.exists(path) and os.path.isfile(path):
            self.path_status.setText("✓ AutoCAD executable validated successfully.")
            self.path_status.setStyleSheet("color: #4caf50; font-size: 12px; font-weight: bold;")
        else:
            self.path_status.setText("⚠ Invalid executable path. File does not exist.")
            self.path_status.setStyleSheet("color: #e53935; font-size: 12px; font-weight: bold;")

    def _set_date_filter(self, filter_mode):
        self.active_filter = filter_mode
        self._update_filter_styles()
        self._filter_history()

    def _update_filter_styles(self):
        self.btn_filter_all.setObjectName("filter_btn_active" if self.active_filter == "ALL" else "filter_btn_inactive")
        self.btn_filter_today.setObjectName("filter_btn_active" if self.active_filter == "TODAY" else "filter_btn_inactive")
        self.btn_filter_week.setObjectName("filter_btn_active" if self.active_filter == "WEEK" else "filter_btn_inactive")

        for btn in [self.btn_filter_all, self.btn_filter_today, self.btn_filter_week]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _open_output(self, path):
        if not path or not os.path.exists(path):
            return
        import subprocess
        try:
            # Select folder and highlight the file using explorer
            subprocess.Popen(f'explorer /select,"{os.path.abspath(path)}"')
        except Exception:
            try:
                os.startfile(os.path.dirname(path))
            except Exception:
                pass

    def _delete_job(self, job_id):
        self.win.db.delete_job(job_id)
        self.refresh(self.user_id)

    def _clear_all_history(self):
        confirm = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to delete all generation jobs from your history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.win.db.clear_user_history(self.user_id)
            self.refresh(self.user_id)

    def _filter_history(self):
        # Clear dynamic item list
        while self.history_list_layout.count() > 0:
            item = self.history_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search_txt = self.search_input.text().strip().lower()
        now = datetime.now()

        filtered = []
        for job in self.all_jobs:
            # (id, job_type, design_type, output_format, status, text_prompt, created_at, input_name, output_name, output_path)
            jid, jtype, dtype, fmt, status, prompt, created, inf, outf, outpath = job
            filename = outf or inf or prompt or ""

            # Check search match
            match = False
            for term in [filename, prompt or "", jtype or "", dtype or "", status or "", fmt or ""]:
                if search_txt in term.lower():
                    match = True
                    break
            if not match:
                continue

            # Check date filter
            if self.active_filter == "TODAY":
                try:
                    dt = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
                    if dt.date() != now.date():
                        continue
                except Exception:
                    pass
            elif self.active_filter == "WEEK":
                try:
                    dt = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
                    if (now - dt).days > 7:
                        continue
                except Exception:
                    pass

            filtered.append(job)

        if not filtered:
            no_jobs = QLabel("No generation history fits the criteria.")
            no_jobs.setObjectName("settings_field_label")
            no_jobs.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_jobs.setContentsMargins(0, 20, 0, 20)
            self.history_list_layout.addWidget(no_jobs)
        else:
            for job in filtered:
                self.history_list_layout.addWidget(self._make_history_row(job))

    def _make_history_row(self, job: tuple) -> QFrame:
        jid, jtype, dtype, fmt, status, prompt, created, inf, outf, outpath = job

        row = QFrame()
        row.setObjectName("history_row")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(16)

        # Icon badge
        icon = "🧊" if dtype == "3D" else "📐"
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_bg = "rgba(229, 57, 53, 0.12)" if dtype == "2D" else "rgba(124, 58, 237, 0.12)"
        badge_border = "rgba(229, 57, 53, 0.25)" if dtype == "2D" else "rgba(124, 58, 237, 0.25)"
        icon_lbl.setStyleSheet(f"background-color: {badge_bg}; border: 1px solid {badge_border}; border-radius: 20px; font-size: 18px;")

        # Details
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        filename = outf or inf or (prompt[:40] + ("..." if len(prompt) > 40 else "")) or "Untitled CAD"
        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")

        mode_desc = f"{jtype or '—'} ({dtype or '—'})  •  Format: {fmt or '—'}  •  {created[:16]}"
        meta_lbl = QLabel(mode_desc)
        meta_lbl.setObjectName("history_meta")

        if prompt and filename != prompt:
            p_text = f"Prompt: \"{prompt[:60]}\"" + ("..." if len(prompt) > 60 else "")
            prompt_lbl = QLabel(p_text)
            prompt_lbl.setStyleSheet("font-size: 11px; color: #aaaaaa; font-style: italic;")
            info_col.addWidget(name_lbl)
            info_col.addWidget(prompt_lbl)
            info_col.addWidget(meta_lbl)
        else:
            info_col.addWidget(name_lbl)
            info_col.addWidget(meta_lbl)

        # Status Badge
        status_map = {
            "COMPLETED": ("history_status_done", "SUCCESS"),
            "FAILED":    ("history_status_fail", "FAILED"),
            "PENDING":   ("history_status_pend", "PENDING"),
        }
        cls_name, stat_lbl = status_map.get(status, ("history_status_pend", status))
        status_lbl = QLabel(stat_lbl)
        status_lbl.setObjectName(cls_name)

        # Buttons
        act_lay = QHBoxLayout()
        act_lay.setSpacing(8)

        btn_open = QPushButton("Open Output")
        btn_open.setObjectName("btn_settings_back")
        btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open.setStyleSheet("padding: 6px 14px; font-size: 11px;")
        
        file_valid = outpath and os.path.exists(outpath)
        btn_open.setEnabled(bool(file_valid))
        if not file_valid:
            btn_open.setToolTip("File is missing or generation failed.")
        else:
            btn_open.setToolTip(f"Show file in explorer:\n{outpath}")
        
        btn_open.clicked.connect(lambda checked=False, p=outpath: self._open_output(p))

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("btn_clear_history")
        btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del.setStyleSheet("padding: 6px 14px; font-size: 11px;")
        btn_del.clicked.connect(lambda checked=False, j=jid: self._delete_job(j))

        act_lay.addWidget(btn_open)
        act_lay.addWidget(btn_del)

        lay.addWidget(icon_lbl)
        lay.addLayout(info_col, 1)
        lay.addWidget(status_lbl)
        lay.addLayout(act_lay)
        return row

    def refresh(self, user_id: str):
        self.user_id = user_id
        
        # User details from DB
        user = self.win.db.get_user_by_id(user_id)
        if user:
            uid, name, email, created_at = user
            self.lbl_name.setText(name or "Guest")
            self.lbl_email.setText(email or "guest@sugrly.ai")
            self.lbl_since.setText(str(created_at or "—")[:10])
            self.lbl_uid.setText(f"UID: {str(uid)}")
            
            # Setup Avatar initials
            parts = (name or "Guest").strip().split()
            initials = "".join([p[0].upper() for p in parts[:2]]) if parts else "GU"
            self.avatar_lbl.setText(initials)
        else:
            self.lbl_name.setText("Guest")
            self.lbl_email.setText("guest@sugrly.ai")
            self.lbl_since.setText("—")
            self.lbl_uid.setText("—")
            self.avatar_lbl.setText("GU")

        # Configuration Cad Path
        saved_path = getattr(self.win, 'cad_app_path', '')
        self.cad_path_input.setText(saved_path)
        self.path_status.setText("")
        self._validate_path(saved_path)

        # Refresh all jobs
        self.all_jobs = self.win.db.get_user_jobs(user_id, limit=100)
        self._update_filter_styles()
        self._filter_history()



# ─────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Studio")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)
        self.setStyleSheet(STYLE)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.db = DatabaseManager()
        self.pipeline = PipelineManager(self.db)
        # Load persisted Settings CAD App Path
        self.cad_app_path = ""
        persist_file = Path.home() / ".cad_studio_settings.json"
        if persist_file.exists():
            try:
                self.cad_app_path = json.loads(persist_file.read_text()).get("cad_app_path", "")
            except Exception:
                pass

        # Default user/project initialization
        DEFAULT_EMAIL = "guest@sugrly.ai"
        user = self.db.get_user_by_email(DEFAULT_EMAIL)
        if not user:
            self.user_id = self.db.create_user("Guest User", DEFAULT_EMAIL, "hash")
        else:
            self.user_id = user[0]

        self.p1_home      = HomePage()
        self.p2_project   = ProjectPage()
        self.p3_editor    = EditorPage(self)
        self.signin_page  = SignInPage(self.db)
        self.p4_settings  = SettingsPage(self)

        self.stack.addWidget(self.signin_page)
        self.stack.addWidget(self.p1_home)
        self.stack.addWidget(self.p2_project)
        self.stack.addWidget(self.p3_editor)
        self.stack.addWidget(self.p4_settings)

        # ── Add settings gear button to Home page ─────────────────────
        self._add_settings_btn_to_home()

        # Wire signals
        self.signin_page.authenticated.connect(self._on_authenticated)
        self.p1_home.modePicked.connect(self._on_open_editor)
        self.p3_editor.go_back.connect(lambda: self.stack.setCurrentWidget(self.p1_home))
        self.p3_editor.btn_settings_editor.clicked.connect(self._on_open_settings)
        self.p4_settings.go_back.connect(self._on_settings_back)

        # Start at Sign In
        self.stack.setCurrentWidget(self.signin_page)

    def _add_settings_btn_to_home(self):
        """Inject a ⚙ gear button into the HomePage's top-right corner."""
        # The HomePage uses a QVBoxLayout with a QScrollArea inside.
        # We overlay a floating settings button by using the home page's root layout.
        from PyQt6.QtWidgets import QSizePolicy as QSP

        gear = QPushButton("⚙")
        gear.setObjectName("btn_settings_icon")
        gear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        gear.setToolTip("Settings")
        gear.setFixedSize(36, 36)
        gear.clicked.connect(self._on_open_settings)

        # Create a thin topbar overlay for home
        topbar = QWidget(self.p1_home)
        topbar.setStyleSheet("background: transparent;")
        topbar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(0, 10, 16, 0)
        tb_lay.addStretch()
        tb_lay.addWidget(gear)

        topbar.setFixedHeight(56)

        # Place it by resizing on first show
        def _position_topbar():
            topbar.setGeometry(0, 0, self.p1_home.width(), 56)

        # Resize on every resize event of p1_home
        orig_resize = self.p1_home.resizeEvent
        def _new_resize(event):
            _position_topbar()
            if orig_resize:
                orig_resize(event)
        self.p1_home.resizeEvent = _new_resize
        topbar.raise_()

    def _on_authenticated(self, user_id, name, email):
        self.user_id = user_id
        self.stack.setCurrentWidget(self.p1_home)

    def _on_open_editor(self, mode: str, folder: str):
        self.p3_editor.setup(mode, folder)
        self.stack.setCurrentWidget(self.p3_editor)

    def _on_open_settings(self):
        self._previous_page = self.stack.currentWidget()
        self.p4_settings.refresh(self.user_id)
        self.stack.setCurrentWidget(self.p4_settings)

    def _on_settings_back(self):
        prev = getattr(self, '_previous_page', self.p1_home)
        self.stack.setCurrentWidget(prev if prev else self.p1_home)


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())