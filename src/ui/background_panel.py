"""
Background Removal Panel — AI rembg / GrabCut, bg color/video, feathering.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QRadioButton, QButtonGroup,
    QLineEdit, QFileDialog, QProgressBar, QColorDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QColor

from src.core.bg_remover import is_rembg_available


def _sec(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:#fe2c55;font-size:11px;font-weight:bold;"
        "background:transparent;margin-top:6px;"
    )
    return lbl


def _div() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:#2a2a2a;")
    return f


class BackgroundPanel(QWidget):
    bg_removal_requested = pyqtSignal(dict)

    _PRESET_COLORS = [
        ("Transparent", (0, 0, 0, 0)),
        ("Black",       (0, 0, 0, 255)),
        ("White",       (255, 255, 255, 255)),
        ("Green",       (0, 177, 64, 255)),
        ("Blue",        (0, 120, 215, 255)),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color = (0, 177, 64)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet("background:#111111;border-bottom:1px solid #2a2a2a;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 12, 0)
        title = QLabel("🎭 AI Background Removal")
        title.setStyleSheet("color:#fff;font-size:13px;font-weight:bold;background:transparent;")
        hdr_lay.addWidget(title)
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        # ── Method ────────────────────────────────────────────────────
        lay.addWidget(_sec("METHOD"))
        self._method_group = QButtonGroup(self)
        rembg_ok = is_rembg_available()

        for label, val in [("Auto AI", "auto"), ("rembg (AI)", "rembg"), ("GrabCut (fast)", "grabcut")]:
            rb = QRadioButton(label if val != "rembg" or rembg_ok
                              else "rembg (AI) — not installed")
            rb.setProperty("method_val", val)
            rb.setEnabled(val != "rembg" or rembg_ok)
            rb.setStyleSheet(
                "QRadioButton{color:#ccc;font-size:12px;background:transparent;spacing:6px;}"
                "QRadioButton::indicator{width:14px;height:14px;}"
                "QRadioButton::indicator:checked{background:#fe2c55;border-radius:7px;}"
                "QRadioButton::indicator:unchecked{background:#333;border:1px solid #555;border-radius:7px;}"
            )
            self._method_group.addButton(rb)
            lay.addWidget(rb)
            if val == "auto":
                rb.setChecked(True)

        lay.addWidget(_div())

        # ── Background color ──────────────────────────────────────────
        lay.addWidget(_sec("BACKGROUND"))

        color_row = QHBoxLayout()
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(36, 28)
        self._update_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self._color_btn)

        color_lbl = QLabel("Custom color")
        color_lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
        color_row.addWidget(color_lbl)
        color_row.addStretch()
        lay.addLayout(color_row)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for name, rgba in self._PRESET_COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(name)
            if rgba[3] == 0:
                btn.setStyleSheet(
                    "QPushButton{background: qlineargradient("
                    "x1:0,y1:0,x2:1,y2:1,"
                    "stop:0 #fff,stop:0.5 #ccc,stop:1 #fff);"
                    "border-radius:4px;border:1px solid #555;}"
                )
            else:
                r, g, b, _ = rgba
                btn.setStyleSheet(
                    f"QPushButton{{background:rgb({r},{g},{b});border-radius:4px;"
                    "border:1px solid #555;}"
                    "QPushButton:hover{border:2px solid #fe2c55;}"
                )
            rgb = rgba[:3]
            btn.clicked.connect(lambda _, c=rgb: self._set_color(c))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        lay.addLayout(preset_row)
        lay.addWidget(_div())

        # ── Background video ──────────────────────────────────────────
        lay.addWidget(_sec("BACKGROUND VIDEO (optional)"))

        vid_row = QHBoxLayout()
        self._vid_path = QLineEdit()
        self._vid_path.setPlaceholderText("No video selected…")
        self._vid_path.setReadOnly(True)
        self._vid_path.setStyleSheet(
            "background:#2a2a2a;color:#ccc;border:1px solid #3a3a3a;"
            "border-radius:4px;padding:4px;font-size:11px;"
        )
        vid_row.addWidget(self._vid_path, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(28)
        browse_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#ccc;border-radius:4px;"
            "border:1px solid #3a3a3a;font-size:11px;padding:0 8px;}"
            "QPushButton:hover{border-color:#fe2c55;}"
        )
        browse_btn.clicked.connect(self._browse_video)
        vid_row.addWidget(browse_btn)

        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#888;border-radius:4px;"
            "border:1px solid #3a3a3a;}"
            "QPushButton:hover{color:#fe2c55;}"
        )
        clear_btn.clicked.connect(lambda: self._vid_path.clear())
        vid_row.addWidget(clear_btn)
        lay.addLayout(vid_row)
        lay.addWidget(_div())

        # ── Feathering ────────────────────────────────────────────────
        lay.addWidget(_sec("EDGE FEATHERING"))

        feat_row = QHBoxLayout()
        feat_lbl = QLabel("Feather")
        feat_lbl.setFixedWidth(82)
        feat_lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
        feat_row.addWidget(feat_lbl)

        self._feather_slider = QSlider(Qt.Orientation.Horizontal)
        self._feather_slider.setRange(0, 20)
        self._feather_slider.setValue(2)
        feat_row.addWidget(self._feather_slider, 1)

        self._feather_lbl = QLabel("2px")
        self._feather_lbl.setFixedWidth(34)
        self._feather_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._feather_lbl.setStyleSheet("color:#ccc;font-size:11px;background:transparent;")
        feat_row.addWidget(self._feather_lbl)

        self._feather_slider.valueChanged.connect(
            lambda v: self._feather_lbl.setText(f"{v}px")
        )
        lay.addLayout(feat_row)

        # ── Progress bar ──────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar{background:#2a2a2a;border-radius:4px;height:8px;}"
            "QProgressBar::chunk{background:#fe2c55;border-radius:4px;}"
        )
        lay.addWidget(self._progress)

        lay.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # Footer
        footer = QWidget()
        footer.setStyleSheet("background:#111111;border-top:1px solid #2a2a2a;")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(12, 8, 12, 8)
        foot_lay.setSpacing(8)

        preview_btn = QPushButton("▶  Preview Frame")
        preview_btn.setFixedHeight(34)
        preview_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#ccc;border-radius:6px;"
            "border:1px solid #444;font-size:12px;}"
            "QPushButton:hover{background:#333;}"
        )
        preview_btn.clicked.connect(lambda: self._emit("preview"))
        foot_lay.addWidget(preview_btn)

        apply_btn = QPushButton("✓  Apply to Clip")
        apply_btn.setFixedHeight(34)
        apply_btn.setStyleSheet(
            "QPushButton{background:#fe2c55;color:white;border-radius:6px;"
            "border:none;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#e0253f;}"
        )
        apply_btn.clicked.connect(lambda: self._emit("apply"))
        foot_lay.addWidget(apply_btn)

        root.addWidget(footer)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _update_color_btn(self):
        r, g, b = self._bg_color
        self._color_btn.setStyleSheet(
            f"QPushButton{{background:rgb({r},{g},{b});border-radius:4px;"
            "border:1px solid #555;}"
            "QPushButton:hover{border:2px solid #fe2c55;}"
        )

    def _set_color(self, rgb: tuple):
        self._bg_color = rgb
        self._update_color_btn()

    def _pick_color(self):
        r, g, b = self._bg_color
        c = QColorDialog.getColor(QColor(r, g, b), self, "Pick Background Color")
        if c.isValid():
            self._set_color((c.red(), c.green(), c.blue()))

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Video", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;All Files (*)"
        )
        if path:
            self._vid_path.setText(path)

    def _get_method(self) -> str:
        for btn in self._method_group.buttons():
            if btn.isChecked():
                return btn.property("method_val") or "auto"
        return "auto"

    def _emit(self, action: str):
        self.bg_removal_requested.emit({
            "action":    action,
            "method":    self._get_method(),
            "bg_color":  self._bg_color,
            "bg_video":  self._vid_path.text() or None,
            "feather":   self._feather_slider.value(),
        })

    def set_progress(self, value: float):
        pct = int(value * 100)
        self._progress.setVisible(pct > 0 and pct < 100)
        self._progress.setValue(pct)
