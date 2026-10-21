"""Floating video scopes: histogram, waveform, vectorscope. Rendered only while visible."""

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt

from src.core import grading


class ScopesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Video Scopes")
        self.setStyleSheet("background:#151515;color:#aaa;")
        row = QHBoxLayout(self)
        self._labels = {}
        for key, title in (("hist", "Histogram"), ("wave", "Waveform"), ("vec", "Vectorscope")):
            col = QVBoxLayout()
            t = QLabel(title)
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img = QLabel()
            img.setFixedSize(256, 160 if key == "vec" else 128)
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(t)
            col.addWidget(img)
            row.addLayout(col)
            self._labels[key] = img

    def update_frame(self, frame):
        if not self.isVisible() or frame is None:
            return
        for key, fn in (("hist", grading.histogram), ("wave", grading.waveform), ("vec", grading.vectorscope)):
            a = fn(frame).copy()
            h, w = a.shape[:2]
            self._labels[key].setPixmap(QPixmap.fromImage(QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()))
