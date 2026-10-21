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
            from src.core.exporter import export_project
            ok, msg = export_project(self.project, self.settings, self.progress.emit, lambda: self._cancel)
            self.finished.emit(ok, msg)
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
        self.format_combo.addItems(["MP4 (H.264)", "MP4 (H.265/HEVC)", "MOV (ProRes 422 HQ)", "WebM (VP9)", "AVI (MPEG-4)"])
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
            "MP4 Video (*.mp4);;MOV Video (*.mov);;WebM Video (*.webm);;AVI Video (*.avi)"
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
            'codec': ['h264', 'h265', 'prores', 'vp9', 'mpeg4'][self.format_combo.currentIndex()],
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
