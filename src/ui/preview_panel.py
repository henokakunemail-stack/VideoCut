"""
Preview Panel - video preview with playback controls
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QImage

from src.core.video_player import VideoReader, ImageReader, FrameProcessor, frame_to_pixmap
from src.core.project import Project, ClipType


class VideoCanvas(QLabel):
    """The actual preview canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._bg = QColor(0, 0, 0)
        self._pixmap = None
        self._text_overlays = []

        self.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border-radius: 4px;
            }
        """)

    def set_frame(self, pixmap: QPixmap, texts=None):
        self._pixmap = pixmap
        self._text_overlays = texts or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._bg)

        if self._pixmap and not self._pixmap.isNull():
            # Center the pixmap
            pw = self._pixmap.width()
            ph = self._pixmap.height()
            cw = self.width()
            ch = self.height()
            x = (cw - pw) // 2
            y = (ch - ph) // 2
            painter.drawPixmap(x, y, self._pixmap)

            # Draw text overlays
            for text_info in self._text_overlays:
                self._draw_text_overlay(painter, text_info, x, y, pw, ph)

    @staticmethod
    def _draw_text_overlay(painter, info, off_x, off_y, pw, ph):
        content = info.get('content', '')
        style = info.get('style', {})
        pos_x = info.get('pos_x', 0.5)
        pos_y = info.get('pos_y', 0.5)

        font = QFont(style.get('font_family', 'Arial'))
        font.setPixelSize(max(12, int(style.get('font_size', 48) * pw / 1920)))
        font.setBold(style.get('bold', False))
        font.setItalic(style.get('italic', False))
        painter.setFont(font)

        text_x = off_x + int(pos_x * pw)
        text_y = off_y + int(pos_y * ph)

        # Shadow
        if style.get('shadow', False):
            painter.setPen(QColor(0, 0, 0, 180))
            painter.drawText(text_x + 2, text_y + 2, content)

        # Stroke
        stroke_w = style.get('stroke_width', 0)
        if stroke_w > 0:
            stroke_color = QColor(style.get('stroke_color', '#000000'))
            pen = QPen(stroke_color, stroke_w)
            painter.setPen(pen)
            for dx in range(-stroke_w, stroke_w + 1):
                for dy in range(-stroke_w, stroke_w + 1):
                    if dx != 0 or dy != 0:
                        painter.drawText(text_x + dx, text_y + dy, content)

        # Main text
        color = QColor(style.get('color', '#ffffff'))
        painter.setPen(color)
        painter.drawText(text_x, text_y, content)

    def get_canvas_rect(self):
        if self._pixmap:
            pw = self._pixmap.width()
            ph = self._pixmap.height()
            x = (self.width() - pw) // 2
            y = (self.height() - ph) // 2
            return QRect(x, y, pw, ph)
        return self.rect()


class TimeDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__("00:00 / 00:00", parent)
        self.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_time(self, current_ms: int, total_ms: int):
        cur = self._fmt(current_ms)
        tot = self._fmt(total_ms)
        self.setText(f"{cur} / {tot}")

    @staticmethod
    def _fmt(ms: int) -> str:
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"


class PreviewPanel(QWidget):
    play_toggled = pyqtSignal(bool)
    seek_requested = pyqtSignal(int)
    time_changed = pyqtSignal(int)
    frame_rendered = pyqtSignal(object)   # RGB uint8 ndarray of the composed frame

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self._readers = {}   # path -> reader
        self.current_time = 0
        self.total_time = 0
        self._playing = False

        self.setStyleSheet("background: #1a1a1a;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Canvas
        self.canvas = VideoCanvas(self)
        layout.addWidget(self.canvas, 1)

        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        layout.addWidget(self.seek_slider)

        # Controls
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        # Skip to start
        self.btn_start = self._ctrl_btn("⏮", "Go to Start")
        self.btn_start.clicked.connect(lambda: self.seek_to(0))
        controls.addWidget(self.btn_start)

        # Step back
        self.btn_back = self._ctrl_btn("◁◁", "Step Back")
        self.btn_back.clicked.connect(self._step_back)
        controls.addWidget(self.btn_back)

        # Play/Pause - bigger
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(44, 44)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background: #fe2c55;
                color: white;
                font-size: 16px;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover { background: #ff4060; }
            QPushButton:pressed { background: #d42047; }
        """)
        self.btn_play.clicked.connect(self.toggle_play)
        controls.addWidget(self.btn_play)

        # Step forward
        self.btn_fwd = self._ctrl_btn("▷▷", "Step Forward")
        self.btn_fwd.clicked.connect(self._step_forward)
        controls.addWidget(self.btn_fwd)

        # Skip to end
        self.btn_end = self._ctrl_btn("⏭", "Go to End")
        self.btn_end.clicked.connect(lambda: self.seek_to(self.total_time))
        controls.addWidget(self.btn_end)

        controls.addStretch()

        # Time display
        self.time_display = TimeDisplay(self)
        controls.addWidget(self.time_display)

        controls.addStretch()

        # Volume
        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("color: #aaaaaa; background: transparent;")
        controls.addWidget(vol_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        controls.addWidget(self.volume_slider)

        # Resolution label
        self.res_label = QLabel("1920×1080")
        self.res_label.setStyleSheet("color: #666666; font-size: 11px; background: transparent;")
        controls.addWidget(self.res_label)

        layout.addLayout(controls)

    def _ctrl_btn(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaaaaa;
                font-size: 13px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: #333333; color: white; }
        """)
        return btn

    def set_project(self, project: Project):
        self.project = project
        self._readers.clear()
        self.total_time = project.settings.duration
        self.res_label.setText(f"{project.settings.width}×{project.settings.height}")
        self.seek_to(0)

    def seek_to(self, time_ms: int):
        self.current_time = time_ms
        self._render_frame(time_ms)
        self.time_display.update_time(time_ms, self.total_time)
        if self.total_time > 0:
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(int(time_ms / self.total_time * 1000))
            self.seek_slider.blockSignals(False)

    def _render_frame(self, time_ms: int):
        if not self.project:
            return

        w = max(1, self.canvas.width() - 4)
        h = max(1, self.canvas.height() - 4)

        # Maintain aspect ratio
        proj_aspect = self.project.settings.width / max(1, self.project.settings.height)
        if w / h > proj_aspect:
            render_w = int(h * proj_aspect)
            render_h = h
        else:
            render_w = w
            render_h = int(w / proj_aspect)

        # Get clips at this time
        clips = self.project.get_clips_at_time(time_ms)
        if not clips:
            # Black frame
            self.canvas.set_frame(QPixmap(render_w, render_h))
            return

        from src.core.renderer import compose_frame, text_infos_at
        base_frame = compose_frame(self.project, time_ms, self._get_clip_frame,
                                   size=(render_w - render_w % 2 or 2, render_h - render_h % 2 or 2))
        text_infos = text_infos_at(self.project, time_ms)
        if base_frame is None:
            self.canvas.set_frame(QPixmap(render_w, render_h), text_infos)
            return

        self.frame_rendered.emit(base_frame)
        pixmap = frame_to_pixmap(base_frame, render_w, render_h)
        self.canvas.set_frame(pixmap, text_infos)

    def _get_clip_frame(self, clip, time_ms: int):
        from src.core.renderer import fetch_clip_frame
        return fetch_clip_frame(self._readers, clip, time_ms, fast=self._playing)

    def toggle_play(self):
        self._playing = not self._playing
        self.btn_play.setText("⏸" if self._playing else "▶")
        self.play_toggled.emit(self._playing)

    def set_playing(self, playing: bool):
        self._playing = playing
        self.btn_play.setText("⏸" if playing else "▶")

    def _on_slider_pressed(self):
        pass

    def _on_slider_moved(self, value: int):
        if self.total_time > 0:
            t = int(value / 1000 * self.total_time)
            self.time_changed.emit(t)

    def _step_back(self):
        self.seek_requested.emit(max(0, self.current_time - 100))

    def _step_forward(self):
        self.seek_requested.emit(self.current_time + 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render_frame(self.current_time)
