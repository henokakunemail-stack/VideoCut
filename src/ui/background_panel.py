"""Background removal panel: matting bake (Apply), instant style changes (mode/colour/feather), frame preview."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox,
    QLineEdit, QFileDialog, QProgressBar, QColorDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap

from src.ai import models
from src.ai.matting import DEFAULT_STYLE, QUALITY

_BTN = ("QPushButton{background:#2a2a2a;color:#ccc;border-radius:6px;border:1px solid #444;padding:6px 10px;}"
        "QPushButton:hover{background:#333;}QPushButton:disabled{color:#666;}")
_LBL = "color:#aaa;font-size:11px;background:transparent;"
MODES = [("Transparent", "transparent"), ("Solid colour", "color"), ("Image / video", "media")]


class BackgroundPanel(QWidget):
    bg_removal_requested = pyqtSignal(dict)   # {action: preview|apply|cancel|remove|style, quality, mode, color, bg_path, feather}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = DEFAULT_STYLE["color"]
        self._style_timer = QTimer(self)
        self._style_timer.setSingleShot(True)
        self._style_timer.setInterval(150)
        self._style_timer.timeout.connect(lambda: self._emit("style"))
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        def row(label, w):
            r = QHBoxLayout()
            lb = QLabel(label)
            lb.setFixedWidth(70)
            lb.setStyleSheet(_LBL)
            r.addWidget(lb)
            r.addWidget(w, 1)
            lay.addLayout(r)

        self.quality = QComboBox()
        for name, q in (("Fast (U2-Net small)", "fast"), ("High (IS-Net)", "high")):
            self.quality.addItem(name, q)
            if not models.available(QUALITY[q]):
                self.quality.model().item(self.quality.count() - 1).setEnabled(False)
        row("Quality", self.quality)
        self.have_model = models.available(QUALITY["fast"]) or models.available(QUALITY["high"])
        if self.have_model and not models.available(QUALITY["fast"]):
            self.quality.setCurrentIndex(1)

        self.mode = QComboBox()
        for name, m in MODES:
            self.mode.addItem(name, m)
        self.mode.currentIndexChanged.connect(self._style_changed)
        row("Background", self.mode)

        self.color_btn = QPushButton()
        self.color_btn.setFixedHeight(26)
        self.color_btn.clicked.connect(self._pick_color)
        row("Colour", self.color_btn)
        self._paint_color()

        self.media = QLineEdit()
        self.media.setReadOnly(True)
        self.media.setPlaceholderText("No image / video selected")
        b = QPushButton("Browse")
        b.setStyleSheet(_BTN)
        b.clicked.connect(self._browse)
        h = QHBoxLayout()
        h.addWidget(self.media, 1)
        h.addWidget(b)
        w = QWidget()
        w.setLayout(h)
        h.setContentsMargins(0, 0, 0, 0)
        row("Media", w)

        self.feather = QSlider(Qt.Orientation.Horizontal)
        self.feather.setRange(0, 20)
        self.feather.valueChanged.connect(self._style_changed)
        row("Feather", self.feather)

        self.preview = QLabel()
        self.preview.setMinimumHeight(140)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background:#111;border:1px solid #2a2a2a;" + _LBL)
        lay.addWidget(self.preview, 1)

        self.status = QLabel("" if self.have_model else
                             "Matting model not installed. Run: python tools/fetch_models.py")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(_LBL)
        lay.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        r = QHBoxLayout()
        self.preview_btn = QPushButton("Preview frame")
        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")
        self.remove_btn = QPushButton("Remove")
        for btn, act in ((self.preview_btn, "preview"), (self.apply_btn, "apply"),
                         (self.cancel_btn, "cancel"), (self.remove_btn, "remove")):
            btn.setStyleSheet(_BTN)
            btn.clicked.connect(lambda _=False, a=act: self._emit(a))
            r.addWidget(btn)
        self.apply_btn.setStyleSheet(_BTN.replace("#2a2a2a", "#fe2c55"))
        lay.addLayout(r)
        for btn in (self.preview_btn, self.apply_btn):
            btn.setEnabled(self.have_model)
        self.set_busy(False)
        self._sync_rows()

    # ---- state ----
    def _paint_color(self):
        self.color_btn.setStyleSheet(f"QPushButton{{background:{self._color};border:1px solid #555;border-radius:4px;}}")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Background colour")
        if c.isValid():
            self._color = c.name()
            self._paint_color()
            self._style_changed()

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Background image / video", "",
                                           "Media (*.png *.jpg *.jpeg *.bmp *.webp *.mp4 *.mov *.mkv *.avi *.webm)")
        if p:
            self.media.setText(p)
            self._style_changed()

    def _sync_rows(self):
        m = self.mode.currentData()
        self.color_btn.setEnabled(m == "color")
        self.media.setEnabled(m == "media")

    def _style_changed(self, *_):
        self._sync_rows()
        self._style_timer.start()

    def style(self) -> dict:
        return {"mode": self.mode.currentData(), "color": self._color, "path": self.media.text(),
                "feather": self.feather.value()}

    def set_style(self, st: dict):
        """Load a clip's matte_style without emitting."""
        for w in (self.mode, self.feather):
            w.blockSignals(True)
        st = {**DEFAULT_STYLE, **(st or {})}
        self.mode.setCurrentIndex(max(0, self.mode.findData(st["mode"])))
        self.feather.setValue(int(st["feather"]))
        self._color, _ = st["color"], self.media.setText(st["path"])
        self._paint_color()
        for w in (self.mode, self.feather):
            w.blockSignals(False)
        self._sync_rows()

    def _emit(self, action: str):
        self.bg_removal_requested.emit({"action": action, "quality": self.quality.currentData(), **self.style(),
                                        "bg_path": self.media.text()})

    # ---- called by the window ----
    def set_busy(self, busy: bool):
        self.apply_btn.setEnabled(self.have_model and not busy)
        self.preview_btn.setEnabled(self.have_model and not busy)
        self.remove_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.progress.setVisible(busy)
        if not busy:
            self.progress.setValue(0)

    def set_progress(self, pct: int):
        self.progress.setValue(int(pct))

    def set_status(self, text: str):
        self.status.setText(text)

    def set_preview(self, rgb):
        """rgb: HxWx3 uint8 ndarray."""
        h, w = rgb.shape[:2]
        img = QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(img).scaled(
            self.preview.width(), self.preview.height(), Qt.AspectRatioMode.KeepAspectRatio))
