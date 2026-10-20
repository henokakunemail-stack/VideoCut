"""
Timeline Panel - professional multi-track timeline
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QPixmap,
    QLinearGradient, QMouseEvent, QPainterPath
)

from src.core.project import Project, Clip, ClipType


TRACK_HEIGHT = 56
HEADER_WIDTH = 60
PIXELS_PER_SECOND = 80
MIN_ZOOM = 20
MAX_ZOOM = 400


class TimelineRuler(QWidget):
    """Ruler showing time markers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.pixels_per_second = PIXELS_PER_SECOND
        self.offset = 0
        self.setStyleSheet("background: #111111;")

    def set_zoom(self, pps: float):
        self.pixels_per_second = pps
        self.update()

    def set_offset(self, offset: int):
        self.offset = offset
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111111"))

        # Grid lines + labels
        pps = self.pixels_per_second
        w = self.width()

        # Determine interval based on zoom
        if pps >= 200:
            interval_sec = 0.5
        elif pps >= 80:
            interval_sec = 1
        elif pps >= 40:
            interval_sec = 2
        elif pps >= 20:
            interval_sec = 5
        else:
            interval_sec = 10

        start_sec = self.offset / pps
        end_sec = start_sec + w / pps

        painter.setPen(QColor("#555555"))
        painter.setFont(QFont("Segoe UI", 8))

        t = (int(start_sec / interval_sec)) * interval_sec
        while t <= end_sec:
            x = int((t - start_sec) * pps)
            painter.drawLine(x, 12, x, 24)
            label = self._fmt_time(t)
            painter.drawText(x + 3, 11, label)
            t += interval_sec

        # Sub-interval marks
        sub_interval = interval_sec / 4
        if sub_interval * pps > 6:
            t = (int(start_sec / sub_interval)) * sub_interval
            while t <= end_sec:
                x = int((t - start_sec) * pps)
                painter.drawLine(x, 18, x, 24)
                t += sub_interval

    @staticmethod
    def _fmt_time(secs: float) -> str:
        m = int(secs // 60)
        s = int(secs % 60)
        dec = int((secs - int(secs)) * 10)
        if dec:
            return f"{m}:{s:02d}.{dec}"
        return f"{m}:{s:02d}"


class ClipWidget(QWidget):
    """A single clip block on the timeline."""
    COLORS = {
        ClipType.VIDEO: ("#3a7bd5", "#2c5faa"),
        ClipType.IMAGE: ("#4caf50", "#388e3c"),
        ClipType.AUDIO: ("#ff9800", "#e65100"),
        ClipType.TEXT: ("#9c27b0", "#6a1b9a"),
        ClipType.STICKER: ("#f44336", "#b71c1c"),
    }

    def __init__(self, clip: Clip, pixels_per_second: float, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.pixels_per_second = pixels_per_second
        self._selected = False
        self._thumbnail = None
        self._update_geometry()
        self.setMouseTracking(True)

    def _update_geometry(self):
        pps = self.pixels_per_second
        x = int(self.clip.timeline_start / 1000 * pps)
        w = max(4, int(self.clip.duration / 1000 * pps))
        self.setGeometry(x, 0, w, TRACK_HEIGHT - 4)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def set_thumbnail(self, pixmap: QPixmap):
        self._thumbnail = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = self.COLORS.get(self.clip.clip_type, ("#3a7bd5", "#2c5faa"))
        c1 = QColor(colors[0])
        c2 = QColor(colors[1])

        rect = self.rect().adjusted(1, 1, -1, -1)

        # Background gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 4, 4)

        # Thumbnail
        if self._thumbnail and not self._thumbnail.isNull():
            thumb_rect = QRect(2, 2, min(self._thumbnail.width(), rect.width() - 4), rect.height() - 4)
            painter.setOpacity(0.35)
            painter.drawPixmap(thumb_rect, self._thumbnail)
            painter.setOpacity(1.0)

        # Name label
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        name = os.path.basename(self.clip.source_path) if self.clip.source_path else self.clip.text_content
        fm = painter.fontMetrics()
        text = fm.elidedText(name, Qt.TextElideMode.ElideRight, rect.width() - 8)
        painter.drawText(rect.adjusted(4, 4, -4, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)

        # Speed indicator
        if self.clip.speed != 1.0:
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(rect.adjusted(4, 0, -4, -4),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                           f"{self.clip.speed:.1f}x")

        # Selection border
        if self._selected:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # Resize handles
        if self._selected:
            handle_color = QColor("#ffffff")
            painter.setBrush(handle_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(0, rect.height() // 2 - 8, 4, 16)
            painter.drawRect(rect.width() - 4, rect.height() // 2 - 8, 4, 16)


class TrackView(QWidget):
    """One horizontal track in the timeline."""

    def __init__(self, track_index: int, track_name: str, parent=None):
        super().__init__(parent)
        self.track_index = track_index
        self.track_name = track_name
        self.setFixedHeight(TRACK_HEIGHT)
        self.setStyleSheet("background: #222222;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#222222" if self.track_index % 2 == 0 else "#1e1e1e"))

        # Track separator
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class TimelineCanvas(QWidget):
    """The main scrollable timeline area where clips are placed."""
    clip_selected = pyqtSignal(str)
    clip_deleted = pyqtSignal(str)
    time_changed = pyqtSignal(int)
    clip_moved = pyqtSignal(str, int)  # clip_id, new_start_ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.pixels_per_second = PIXELS_PER_SECOND
        self.clip_widgets: dict[str, ClipWidget] = {}
        self.selected_clip_id = None
        self.playhead_x = 0
        self.total_duration_ms = 0

        self._dragging = False
        self._drag_clip_id = None
        self._drag_offset_x = 0
        self._resizing = False
        self._resize_clip_id = None
        self._resize_side = None  # 'left' or 'right'

        self.setMouseTracking(True)
        self.setMinimumHeight(TRACK_HEIGHT * 4)
        self.setStyleSheet("background: #222222;")

        self._num_tracks = 4  # main, overlay1, overlay2, audio

    def set_project(self, project: Project):
        self.project = project
        self._rebuild()

    def set_zoom(self, pps: float):
        self.pixels_per_second = pps
        self._rebuild()

    def _rebuild(self):
        # Remove old widgets
        for w in self.clip_widgets.values():
            w.setParent(None)
        self.clip_widgets.clear()

        if not self.project:
            return

        self.total_duration_ms = self.project.settings.duration
        canvas_width = max(800, int(self.total_duration_ms / 1000 * self.pixels_per_second) + 200)
        self.setMinimumWidth(canvas_width)
        self.setMinimumHeight(TRACK_HEIGHT * self._num_tracks)

        for clip in self.project.clips:
            self._create_clip_widget(clip)

        self.update()

    def _create_clip_widget(self, clip: Clip):
        widget = ClipWidget(clip, self.pixels_per_second, self)
        track_y = clip.track * TRACK_HEIGHT + 2
        widget.move(widget.x(), track_y)
        widget.show()
        self.clip_widgets[clip.id] = widget

        # Load thumbnail async-ish
        self._load_thumbnail(clip.id)

    def _load_thumbnail(self, clip_id: str):
        widget = self.clip_widgets.get(clip_id)
        if not widget:
            return
        clip = widget.clip
        if clip.clip_type == ClipType.VIDEO and clip.source_path:
            try:
                from src.core.video_player import VideoReader, frame_to_pixmap
                reader = VideoReader(clip.source_path)
                if reader.is_valid():
                    frame = reader.read_thumbnail((160, 40))
                    if frame is not None:
                        import numpy as np
                        from PyQt6.QtGui import QImage
                        h, w, c = frame.shape
                        qimg = QImage(frame.data, w, h, c * w, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                        widget.set_thumbnail(pixmap)
                reader.close()
            except Exception:
                pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background tracks
        for i in range(self._num_tracks):
            y = i * TRACK_HEIGHT
            color = QColor("#222222") if i % 2 == 0 else QColor("#1e1e1e")
            painter.fillRect(0, y, self.width(), TRACK_HEIGHT, color)
            # Track separator
            painter.setPen(QPen(QColor("#2d2d2d"), 1))
            painter.drawLine(0, y + TRACK_HEIGHT - 1, self.width(), y + TRACK_HEIGHT - 1)

        # Grid lines (per second)
        pps = self.pixels_per_second
        painter.setPen(QPen(QColor("#2a2a2a"), 1))
        x = 0
        while x < self.width():
            painter.drawLine(x, 0, x, self.height())
            x += int(pps)

        # Playhead
        painter.setPen(QPen(QColor("#fe2c55"), 2))
        painter.drawLine(self.playhead_x, 0, self.playhead_x, self.height())

        # Playhead triangle
        path = QPainterPath()
        path.moveTo(self.playhead_x - 6, 0)
        path.lineTo(self.playhead_x + 6, 0)
        path.lineTo(self.playhead_x, 10)
        path.closeSubpath()
        painter.setBrush(QColor("#fe2c55"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def set_playhead(self, time_ms: int):
        self.playhead_x = int(time_ms / 1000 * self.pixels_per_second)
        self.update()

    def select_clip(self, clip_id: str):
        for cid, w in self.clip_widgets.items():
            w.set_selected(cid == clip_id)
        self.selected_clip_id = clip_id
        self.clip_selected.emit(clip_id)

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()

        # Check if clicking on a clip
        for cid, widget in self.clip_widgets.items():
            if widget.geometry().contains(pos):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.select_clip(cid)
                    self._dragging = True
                    self._drag_clip_id = cid
                    self._drag_offset_x = pos.x() - widget.x()
                elif event.button() == Qt.MouseButton.RightButton:
                    self._show_clip_menu(cid, event.globalPosition().toPoint())
                return

        # Click on empty area -> move playhead
        if event.button() == Qt.MouseButton.LeftButton:
            t = int(pos.x() / self.pixels_per_second * 1000)
            self.set_playhead(t)
            self.time_changed.emit(t)
            # Deselect
            for w in self.clip_widgets.values():
                w.set_selected(False)
            self.selected_clip_id = None

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and self._drag_clip_id:
            pos = event.position().toPoint()
            new_x = pos.x() - self._drag_offset_x
            new_x = max(0, new_x)
            widget = self.clip_widgets.get(self._drag_clip_id)
            if widget:
                # Snap to grid (per 10 frames at current fps)
                snap_px = int(self.pixels_per_second / 30 * 10)  # 10 frames
                snapped_x = round(new_x / max(1, snap_px)) * snap_px
                widget.move(snapped_x, widget.y())
                # Update clip start
                new_start_ms = int(snapped_x / self.pixels_per_second * 1000)
                clip = widget.clip
                dur = clip.duration
                clip.timeline_start = new_start_ms
                clip.timeline_end = new_start_ms + dur
        elif self._dragging is False:
            # Change cursor near edges of clips
            pos = event.position().toPoint()
            for cid, widget in self.clip_widgets.items():
                if widget.geometry().contains(pos):
                    local_x = pos.x() - widget.x()
                    if local_x < 6 or local_x > widget.width() - 6:
                        self.setCursor(Qt.CursorShape.SizeHorCursor)
                    else:
                        self.setCursor(Qt.CursorShape.OpenHandCursor)
                    return
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging and self._drag_clip_id:
            widget = self.clip_widgets.get(self._drag_clip_id)
            if widget:
                ms = int(widget.x() / self.pixels_per_second * 1000)
                self.clip_moved.emit(self._drag_clip_id, ms)
                if self.project:
                    self.project._update_duration()
        self._dragging = False
        self._drag_clip_id = None

    def _show_clip_menu(self, clip_id: str, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #222222; border: 1px solid #444; border-radius: 6px; }
            QMenu::item { padding: 6px 20px; color: white; }
            QMenu::item:selected { background: #fe2c55; }
        """)
        cut_act = menu.addAction("✂  Split Here")
        dup_act = menu.addAction("⎘  Duplicate")
        menu.addSeparator()
        del_act = menu.addAction("🗑  Delete")

        action = menu.exec(pos)
        if action == del_act:
            self.clip_deleted.emit(clip_id)
        elif action == cut_act:
            # Split at current playhead
            t = int(self.playhead_x / self.pixels_per_second * 1000)
            if self.project:
                new_clip = self.project.split_clip(clip_id, t)
                if new_clip:
                    self._rebuild()

    def contextMenuEvent(self, event):
        pass  # handled in mousePressEvent


class TrackHeader(QWidget):
    """Left track labels."""
    LABELS = ["Main", "Overlay 1", "Overlay 2", "Audio"]
    ICONS = ["🎬", "🎭", "🎭", "🎵"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(HEADER_WIDTH)
        self.setStyleSheet("background: #161616;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#161616"))
        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 9))

        for i, (label, icon) in enumerate(zip(self.LABELS, self.ICONS)):
            y = i * TRACK_HEIGHT
            painter.fillRect(0, y, self.width(), TRACK_HEIGHT,
                           QColor("#161616") if i % 2 == 0 else QColor("#141414"))
            # Icon
            painter.drawText(4, y + TRACK_HEIGHT // 2 - 6, icon)
            # Label
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(4, y + TRACK_HEIGHT // 2 + 8, label)
            # Separator
            painter.setPen(QPen(QColor("#2d2d2d"), 1))
            painter.drawLine(0, y + TRACK_HEIGHT - 1, self.width(), y + TRACK_HEIGHT - 1)


class TimelinePanel(QWidget):
    time_changed = pyqtSignal(int)
    clip_selected = pyqtSignal(str)
    clip_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_clip_id = None
        self.pixels_per_second = PIXELS_PER_SECOND
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar: zoom + add media button
        topbar = QWidget()
        topbar.setFixedHeight(36)
        topbar.setStyleSheet("background: #161616; border-bottom: 1px solid #2a2a2a;")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(8, 4, 8, 4)
        topbar_layout.setSpacing(6)

        # Add clip buttons
        add_video_btn = self._small_btn("+ Video", "#333333")
        add_video_btn.clicked.connect(self._add_video_clicked)
        topbar_layout.addWidget(add_video_btn)

        add_text_btn = self._small_btn("T Text", "#333333")
        add_text_btn.clicked.connect(self._add_text_clicked)
        topbar_layout.addWidget(add_text_btn)

        add_audio_btn = self._small_btn("♪ Audio", "#333333")
        topbar_layout.addWidget(add_audio_btn)

        topbar_layout.addStretch()

        # Zoom
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        topbar_layout.addWidget(zoom_label)

        from PyQt6.QtWidgets import QSlider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(MIN_ZOOM, MAX_ZOOM)
        self.zoom_slider.setValue(self.pixels_per_second)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        topbar_layout.addWidget(self.zoom_slider)

        layout.addWidget(topbar)

        # Ruler + canvas row
        canvas_row = QWidget()
        canvas_row_layout = QHBoxLayout(canvas_row)
        canvas_row_layout.setContentsMargins(0, 0, 0, 0)
        canvas_row_layout.setSpacing(0)

        # Track headers
        self.track_header = TrackHeader()
        canvas_row_layout.addWidget(self.track_header)

        # Timeline area (ruler + scrollable canvas)
        timeline_area = QWidget()
        timeline_area_layout = QVBoxLayout(timeline_area)
        timeline_area_layout.setContentsMargins(0, 0, 0, 0)
        timeline_area_layout.setSpacing(0)

        # Ruler
        self.ruler = TimelineRuler()
        timeline_area_layout.addWidget(self.ruler)

        # Scrollable canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: #222222; }
        """)

        self.canvas = TimelineCanvas()
        self.canvas.clip_selected.connect(self._on_clip_selected)
        self.canvas.clip_deleted.connect(self.clip_deleted)
        self.canvas.time_changed.connect(self.time_changed)
        self.scroll_area.setWidget(self.canvas)

        # Sync ruler scroll with canvas scroll
        self.scroll_area.horizontalScrollBar().valueChanged.connect(
            lambda v: self.ruler.set_offset(v)
        )

        timeline_area_layout.addWidget(self.scroll_area, 1)
        canvas_row_layout.addWidget(timeline_area, 1)

        layout.addWidget(canvas_row, 1)

    def _small_btn(self, text: str, bg: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: #cccccc;
                font-size: 11px;
                border: none;
                border-radius: 4px;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: #444; color: white; }}
        """)
        return btn

    def _on_zoom_changed(self, value: int):
        self.pixels_per_second = value
        self.ruler.set_zoom(value)
        self.canvas.set_zoom(value)

    def _on_clip_selected(self, clip_id: str):
        self.selected_clip_id = clip_id
        self.clip_selected.emit(clip_id)

    def set_project(self, project: Project):
        self.canvas.set_project(project)

    def set_playhead(self, time_ms: int):
        self.canvas.set_playhead(time_ms)
        # Auto-scroll to keep playhead visible
        playhead_x = int(time_ms / 1000 * self.pixels_per_second)
        visible_start = self.scroll_area.horizontalScrollBar().value()
        visible_end = visible_start + self.scroll_area.width()
        if playhead_x > visible_end - 40:
            self.scroll_area.horizontalScrollBar().setValue(playhead_x - 40)
        elif playhead_x < visible_start:
            self.scroll_area.horizontalScrollBar().setValue(max(0, playhead_x - 40))

    def _add_video_clicked(self):
        from PyQt6.QtWidgets import QFileDialog
        parent = self.window()
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Video", "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm)"
        )
        for p in paths:
            if hasattr(parent, '_add_video_clip'):
                parent._add_video_clip(p)

    def _add_text_clicked(self):
        from src.ui.text_dialog import TextDialog
        dlg = TextDialog(self)
        if dlg.exec():
            clip = dlg.get_clip()
            if clip and self.canvas.project:
                self.canvas.project.add_clip(clip)
                self.canvas._rebuild()
