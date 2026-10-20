"""
Export Dialog - Export video with settings
"""

import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar, QLineEdit, QFileDialog,
    QGroupBox, QGridLayout, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject
from src.core.project import Project


class ExportWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, project: Project, settings: dict):
        super().__init__()
        self.project = project
        self.settings = settings
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            import cv2
            import numpy as np
            from src.core.video_player import VideoReader, ImageReader, FrameProcessor, frame_to_pixmap

            out_path = self.settings['output_path']
            fps = self.settings['fps']
            width = self.settings['width']
            height = self.settings['height']
            duration_ms = self.project.settings.duration

            if duration_ms == 0:
                self.finished.emit(False, "No content to export (empty timeline).")
                return

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

            readers = {}
            total_frames = int(duration_ms / 1000 * fps)

            for frame_idx in range(total_frames):
                if self._cancel:
                    writer.release()
                    self.finished.emit(False, "Export cancelled.")
                    return

                time_ms = int(frame_idx / fps * 1000)
                clips = self.project.get_clips_at_time(time_ms)

                # Render frame
                frame = np.zeros((height, width, 3), dtype=np.uint8)

                for clip in clips:
                    if clip.track != 0:
                        continue
                    path = clip.source_path
                    if clip.clip_type.value == "video":
                        if path not in readers:
                            r = VideoReader(path)
                            if r.is_valid():
                                readers[path] = r
                        reader = readers.get(path)
                        if reader:
                            dur = clip.duration
                            ratio = (time_ms - clip.timeline_start) / max(1, dur)
                            src_t = clip.source_start + int(ratio * (clip.source_end - clip.source_start))
                            raw = reader.read_frame(src_t)
                            if raw is not None:
                                raw = FrameProcessor.apply_flip(raw, clip.flip_h, clip.flip_v)
                                raw = FrameProcessor.apply_filter(raw, clip.filter_id, clip.filter_intensity)
                                raw = FrameProcessor.apply_color_correction(raw, clip)
                                resized = cv2.resize(raw, (width, height))
                                frame = resized
                    elif clip.clip_type.value == "image":
                        if path not in readers:
                            readers[path] = ImageReader(path)
                        reader = readers.get(path)
                        if reader:
                            raw = reader.read_frame()
                            if raw is not None:
                                raw = FrameProcessor.apply_color_correction(raw, clip)
                                resized = cv2.resize(raw, (width, height))
                                frame = resized

                # Write frame (BGR)
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                writer.write(bgr)

                progress = int((frame_idx + 1) / total_frames * 100)
                self.progress.emit(progress)

            writer.release()
            for r in readers.values():
                if hasattr(r, 'close'):
                    r.close()

            self.finished.emit(True, f"Exported to: {out_path}")

        except Exception as e:
            self.finished.emit(False, f"Export failed: {e}")


class ExportDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.worker = None
        self.thread = None
        self.setWindowTitle("Export Video")
        self.setMinimumWidth(480)
        self.setStyleSheet("""
            QDialog { background: #222222; color: white; }
            QLabel { color: #cccccc; }
            QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px;
                        color: #aaaaaa; font-size: 11px; font-weight: bold; padding-top: 6px; }
            QGroupBox::title { left: 10px; subcontrol-origin: margin; }
            QComboBox, QSpinBox, QLineEdit {
                background: #333333; color: white;
                border: 1px solid #555; border-radius: 4px; padding: 4px;
            }
            QPushButton { background: #333; color: white; border-radius: 6px; padding: 6px 14px; }
            QPushButton:hover { background: #444; }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Output file
        out_group = QGroupBox("Output")
        out_layout = QHBoxLayout(out_group)
        self.out_path = QLineEdit()
        self.out_path.setPlaceholderText("Choose output file...")
        out_layout.addWidget(self.out_path, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        out_layout.addWidget(browse_btn)
        layout.addWidget(out_group)

        # Video settings
        vid_group = QGroupBox("Video Settings")
        vid_layout = QGridLayout(vid_group)

        vid_layout.addWidget(QLabel("Resolution:"), 0, 0)
        self.resolution = QComboBox()
        self.resolution.addItems(["1920×1080 (1080p)", "1280×720 (720p)", "854×480 (480p)",
                                   "3840×2160 (4K)", "1080×1920 (9:16 Vertical)",
                                   "1080×1080 (Square)"])
        vid_layout.addWidget(self.resolution, 0, 1)

        vid_layout.addWidget(QLabel("Frame Rate:"), 1, 0)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24 fps", "25 fps", "30 fps", "60 fps"])
        self.fps_combo.setCurrentIndex(2)
        vid_layout.addWidget(self.fps_combo, 1, 1)

        vid_layout.addWidget(QLabel("Quality:"), 2, 0)
        self.quality = QComboBox()
        self.quality.addItems(["Low", "Medium", "High", "Ultra"])
        self.quality.setCurrentIndex(2)
        vid_layout.addWidget(self.quality, 2, 1)

        vid_layout.addWidget(QLabel("Format:"), 3, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (H.264)", "WebM", "AVI"])
        vid_layout.addWidget(self.format_combo, 3, 1)

        layout.addWidget(vid_group)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar { background: #333; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background: #fe2c55; border-radius: 4px; }
        """)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Ready to export")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet("""
            QPushButton { background: #fe2c55; color: white; font-weight: bold;
                          border-radius: 6px; padding: 8px 20px; font-size: 13px; }
            QPushButton:hover { background: #ff4060; }
        """)
        self.export_btn.clicked.connect(self._start_export)
        btn_row.addWidget(self.export_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.cancel_btn)

        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video As", "output.mp4",
            "MP4 Video (*.mp4);;WebM Video (*.webm);;AVI Video (*.avi)"
        )
        if path:
            self.out_path.setText(path)

    def _get_resolution(self):
        res_map = {
            0: (1920, 1080),
            1: (1280, 720),
            2: (854, 480),
            3: (3840, 2160),
            4: (1080, 1920),
            5: (1080, 1080),
        }
        return res_map.get(self.resolution.currentIndex(), (1920, 1080))

    def _get_fps(self):
        fps_map = {0: 24, 1: 25, 2: 30, 3: 60}
        return fps_map.get(self.fps_combo.currentIndex(), 30)

    def _start_export(self):
        out_path = self.out_path.text().strip()
        if not out_path:
            QMessageBox.warning(self, "Error", "Please choose an output file.")
            return

        w, h = self._get_resolution()
        fps = self._get_fps()

        settings = {
            'output_path': out_path,
            'width': w,
            'height': h,
            'fps': fps,
            'quality': self.quality.currentIndex(),
        }

        self.export_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Exporting...")

        self.thread = QThread()
        self.worker = ExportWorker(self.project, settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
        self.close()

    def _on_finished(self, success: bool, message: str):
        self.export_btn.setEnabled(True)
        if success:
            self.progress.setValue(100)
            self.status_label.setText("✓ " + message)
            QMessageBox.information(self, "Export Complete", message)
        else:
            self.status_label.setText("✗ " + message)
            QMessageBox.critical(self, "Export Failed", message)
