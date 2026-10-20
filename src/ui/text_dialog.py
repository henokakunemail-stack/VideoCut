"""
Text Dialog - Add/edit text clips
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QDialogButtonBox,
    QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from src.core.project import Clip, ClipType, TextStyle


TEXT_PRESETS = {
    "default": {"font_family": "Arial", "font_size": 48, "bold": False, "italic": False,
                "color": "#ffffff", "stroke_width": 0, "shadow": False},
    "title":   {"font_family": "Impact", "font_size": 72, "bold": True, "italic": False,
                "color": "#ffffff", "stroke_width": 2, "stroke_color": "#000000", "shadow": True},
    "subtitle": {"font_family": "Arial", "font_size": 36, "bold": False, "italic": True,
                 "color": "#eeeeee", "stroke_width": 1, "shadow": False},
    "bold":    {"font_family": "Arial", "font_size": 56, "bold": True, "italic": False,
                "color": "#ffffff", "stroke_width": 3, "stroke_color": "#000000", "shadow": False},
    "neon":    {"font_family": "Arial", "font_size": 52, "bold": True, "italic": False,
                "color": "#00ffff", "stroke_width": 2, "stroke_color": "#0044ff", "shadow": True},
    "graffiti": {"font_family": "Impact", "font_size": 64, "bold": True, "italic": True,
                 "color": "#ff3300", "stroke_width": 3, "stroke_color": "#000000", "shadow": True},
    "typewriter": {"font_family": "Courier New", "font_size": 40, "bold": False, "italic": False,
                   "color": "#dddddd", "stroke_width": 0, "shadow": False},
    "fade_in": {"font_family": "Arial", "font_size": 48, "bold": False, "italic": False,
                "color": "#ffffff", "stroke_width": 0, "shadow": False},
}


class TextDialog(QDialog):
    def __init__(self, parent=None, preset: str = "default"):
        super().__init__(parent)
        self.setWindowTitle("Add Text")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog { background: #222222; color: white; }
            QLabel { color: #cccccc; }
            QLineEdit, QComboBox, QSpinBox {
                background: #333333; color: white;
                border: 1px solid #555555; border-radius: 4px; padding: 4px;
            }
        """)
        self._preset = preset
        self._color = "#ffffff"
        self._stroke_color = "#000000"
        self._build_ui()
        self._apply_preset(preset)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Text
        layout.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter your text here...")
        layout.addWidget(self.text_input)

        # Font
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()
        fonts = ["Arial", "Helvetica", "Times New Roman", "Courier New",
                 "Georgia", "Verdana", "Impact", "Comic Sans MS",
                 "Trebuchet MS", "Palatino"]
        self.font_combo.addItems(fonts)
        font_row.addWidget(self.font_combo, 1)
        layout.addLayout(font_row)

        # Size + Style
        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Size:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(48)
        style_row.addWidget(self.font_size)

        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(28, 28)
        self.bold_btn.setStyleSheet("""
            QPushButton { font-weight: bold; background: #444; color: white; border-radius: 4px; }
            QPushButton:checked { background: #fe2c55; }
        """)
        style_row.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(28, 28)
        self.italic_btn.setStyleSheet("""
            QPushButton { font-style: italic; background: #444; color: white; border-radius: 4px; }
            QPushButton:checked { background: #fe2c55; }
        """)
        style_row.addWidget(self.italic_btn)
        style_row.addStretch()
        layout.addLayout(style_row)

        # Colors
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 24)
        self.color_btn.setStyleSheet("background: #ffffff; border-radius: 4px;")
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        # Shadow
        self.shadow_check = QCheckBox("Shadow")
        layout.addWidget(self.shadow_check)

        # Duration
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duration (sec):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(3)
        dur_row.addWidget(self.duration_spin)
        dur_row.addStretch()
        layout.addLayout(dur_row)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.setStyleSheet("""
            QPushButton { background: #333; color: white; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background: #444; }
        """)
        layout.addWidget(btns)

    def _apply_preset(self, preset: str):
        p = TEXT_PRESETS.get(preset, TEXT_PRESETS["default"])
        idx = self.font_combo.findText(p.get("font_family", "Arial"))
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        self.font_size.setValue(p.get("font_size", 48))
        self.bold_btn.setChecked(p.get("bold", False))
        self.italic_btn.setChecked(p.get("italic", False))
        self._color = p.get("color", "#ffffff")
        self._stroke_color = p.get("stroke_color", "#000000")
        self.color_btn.setStyleSheet(f"background: {self._color}; border-radius: 4px;")
        self.shadow_check.setChecked(p.get("shadow", False))

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._color), self)
        if col.isValid():
            self._color = col.name()
            self.color_btn.setStyleSheet(f"background: {self._color}; border-radius: 4px;")

    def get_clip(self) -> Clip:
        text = self.text_input.text().strip()
        if not text:
            text = "Text"

        style = TextStyle(
            font_family=self.font_combo.currentText(),
            font_size=self.font_size.value(),
            bold=self.bold_btn.isChecked(),
            italic=self.italic_btn.isChecked(),
            color=self._color,
            stroke_color=self._stroke_color,
            shadow=self.shadow_check.isChecked(),
        )

        duration_ms = self.duration_spin.value() * 1000

        # Find current end time in parent project
        parent = self.parent()
        start = 0
        while parent:
            if hasattr(parent, 'project'):
                start = parent.project.settings.duration
                break
            parent = parent.parent()

        clip = Clip(
            clip_type=ClipType.TEXT,
            text_content=text,
            text_style=style,
            track=1,
            timeline_start=start,
            timeline_end=start + duration_ms,
        )
        return clip
