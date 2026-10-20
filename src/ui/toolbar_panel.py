"""
Top Toolbar - professional top bar with project name, tools, export
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class TopToolbar(QWidget):
    export_clicked = pyqtSignal()
    split_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    import_clicked = pyqtSignal()
    undo_clicked = pyqtSignal()
    redo_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet("""
            QWidget {
                background-color: #111111;
                border-bottom: 1px solid #2a2a2a;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Logo — try SVG icon, fallback to text
        logo_widget = QWidget()
        logo_widget.setFixedSize(130, 36)
        logo_widget.setStyleSheet("background: transparent;")
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(6)

        # SVG icon (play triangle in red circle)
        icon_label = QLabel()
        icon_label.setFixedSize(30, 30)
        icon_label.setStyleSheet("""
            background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                fx:0.5,fy:0.5,stop:0 #fe2c55,stop:1 #cc1a3a);
            border-radius: 6px;
            color: white;
            font-size: 13px;
            font-weight: bold;
        """)
        icon_label.setText("▶")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(icon_label)

        # "VideoCut" text
        logo_text = QLabel("VideoCut")
        logo_text.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
            background: transparent;
            letter-spacing: 0.5px;
        """)
        logo_layout.addWidget(logo_text)

        layout.addWidget(logo_widget)

        self._sep()
        layout.addWidget(self._make_sep())

        # Project name
        self.project_name = QLabel("Untitled Project")
        self.project_name.setStyleSheet("color: #ffffff; font-size: 13px; background: transparent;")
        layout.addWidget(self.project_name)

        layout.addStretch()

        # Edit tools
        self.undo_btn = self._make_tool_btn("↩", "Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo_clicked)
        layout.addWidget(self.undo_btn)

        self.redo_btn = self._make_tool_btn("↪", "Redo (Ctrl+Y)")
        self.redo_btn.clicked.connect(self.redo_clicked)
        layout.addWidget(self.redo_btn)

        layout.addWidget(self._make_sep())

        # Split / Delete
        self.split_btn = self._make_tool_btn("⎇", "Split Clip (Ctrl+B)")
        self.split_btn.clicked.connect(self.split_clicked)
        layout.addWidget(self.split_btn)

        self.delete_btn = self._make_tool_btn("🗑", "Delete (Del)")
        self.delete_btn.clicked.connect(self.delete_clicked)
        layout.addWidget(self.delete_btn)

        layout.addWidget(self._make_sep())

        # Import
        self.import_btn = self._make_icon_btn("+ Import", "#333333")
        self.import_btn.clicked.connect(self.import_clicked)
        layout.addWidget(self.import_btn)

        layout.addStretch()

        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.setFixedSize(90, 34)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #fe2c55;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover { background-color: #ff4060; }
            QPushButton:pressed { background-color: #e0243d; }
        """)
        self.export_btn.clicked.connect(self.export_clicked)
        layout.addWidget(self.export_btn)

    def _make_tool_btn(self, icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(icon)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #cccccc;
                font-size: 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: #333333; color: white; }
            QPushButton:pressed { background: #444444; }
        """)
        return btn

    def _make_icon_btn(self, text: str, bg: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: #cccccc;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 0 10px;
            }}
            QPushButton:hover {{ background: #444444; color: white; }}
        """)
        return btn

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(24)
        sep.setStyleSheet("color: #333333; background: #333333;")
        return sep

    def _sep(self):
        pass

    def set_project_name(self, name: str):
        self.project_name.setText(name)
