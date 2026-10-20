"""
Auto Subtitle Dialog — transcribe, edit, style and export subtitles.
"""

import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QFileDialog,
    QLineEdit, QSpinBox, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor

from src.core.subtitle_engine import SubtitleEngine, SubtitleTrack, is_whisper_available


_DARK = "background:#1a1a1a;color:#fff;"
_BTN  = ("QPushButton{background:#2a2a2a;color:#ccc;border-radius:6px;"
         "border:1px solid #3a3a3a;font-size:12px;padding:4px 10px;}"
         "QPushButton:hover{border-color:#fe2c55;color:white;}")
_BTN_RED = ("QPushButton{background:#fe2c55;color:white;border-radius:6px;"
            "border:none;font-size:12px;font-weight:bold;padding:4px 10px;}"
            "QPushButton:hover{background:#e0253f;}")


class _TranscribeWorker(QThread):
    progress   = pyqtSignal(float)
    finished   = pyqtSignal(object)   # SubtitleTrack
    error      = pyqtSignal(str)

    def __init__(self, media_path: str, language: str, model: str):
        super().__init__()
        self.media_path = media_path
        self.language   = language
        self.model      = model

    def run(self):
        try:
            track = SubtitleEngine.transcribe(
                self.media_path,
                language=self.language,
                model_name=self.model,
                progress_cb=lambda p: self.progress.emit(p),
            )
            self.finished.emit(track)
        except Exception as e:
            self.error.emit(str(e))


class SubtitleDialog(QDialog):
    subtitles_applied = pyqtSignal(object)   # SubtitleTrack

    def __init__(self, media_path: str = "", parent=None):
        super().__init__(parent)
        self._media_path = media_path
        self._track: SubtitleTrack | None = None
        self._worker: _TranscribeWorker | None = None
        self.setWindowTitle("Auto Subtitle / Captions")
        self.setMinimumSize(700, 560)
        self.setStyleSheet(_DARK)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(16, 16, 16, 16)

        # ── Source row ────────────────────────────────────────────────
        src_row = QHBoxLayout()
        src_lbl = QLabel("Video:")
        src_lbl.setFixedWidth(44)
        src_lbl.setStyleSheet("color:#aaa;")
        src_row.addWidget(src_lbl)

        self._src_edit = QLineEdit(self._media_path)
        self._src_edit.setStyleSheet(
            "background:#2a2a2a;color:#ccc;border:1px solid #3a3a3a;"
            "border-radius:4px;padding:4px;"
        )
        src_row.addWidget(self._src_edit, 1)

        browse = QPushButton("Browse")
        browse.setStyleSheet(_BTN)
        browse.clicked.connect(self._browse_src)
        src_row.addWidget(browse)
        lay.addLayout(src_row)

        # ── Settings row ──────────────────────────────────────────────
        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(12)

        lang_lbl = QLabel("Language:")
        lang_lbl.setStyleSheet("color:#aaa;font-size:12px;")
        cfg_row.addWidget(lang_lbl)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems([
            "auto", "id", "en", "zh", "ja", "ko", "es",
            "fr", "de", "pt", "ru", "ar", "hi", "th", "vi",
        ])
        self._lang_combo.setStyleSheet(
            "QComboBox{background:#2a2a2a;color:#ccc;border:1px solid #3a3a3a;"
            "border-radius:4px;padding:3px 8px;min-width:80px;}"
            "QComboBox QAbstractItemView{background:#2a2a2a;color:#ccc;}"
        )
        cfg_row.addWidget(self._lang_combo)

        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet("color:#aaa;font-size:12px;")
        cfg_row.addWidget(model_lbl)

        self._model_combo = QComboBox()
        self._model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self._model_combo.setCurrentText("base")
        self._model_combo.setStyleSheet(self._lang_combo.styleSheet())
        cfg_row.addWidget(self._model_combo)

        whisper_lbl = QLabel("✓ Whisper ready" if is_whisper_available()
                              else "⚠ Whisper not installed — pip install openai-whisper")
        whisper_lbl.setStyleSheet(
            f"color:{'#4caf50' if is_whisper_available() else '#ff9800'};font-size:11px;"
        )
        cfg_row.addWidget(whisper_lbl)
        cfg_row.addStretch()

        transcribe_btn = QPushButton("🎙  Transcribe")
        transcribe_btn.setStyleSheet(_BTN_RED)
        transcribe_btn.clicked.connect(self._start_transcribe)
        cfg_row.addWidget(transcribe_btn)
        lay.addLayout(cfg_row)

        # ── Progress bar ──────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar{background:#2a2a2a;border-radius:4px;height:6px;}"
            "QProgressBar::chunk{background:#fe2c55;border-radius:4px;}"
        )
        lay.addWidget(self._progress)

        # ── Subtitle table ────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#2a2a2a;color:#ccc;border:1px solid #333;padding:4px;}"
        )
        self._table.setStyleSheet(
            "QTableWidget{background:#1a1a1a;color:#ccc;gridline-color:#2a2a2a;"
            "border:1px solid #2a2a2a;}"
            "QTableWidget::item:selected{background:#fe2c5540;}"
        )
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 80)
        lay.addWidget(self._table, 1)

        # ── Style settings ────────────────────────────────────────────
        style_row = QHBoxLayout()
        style_row.setSpacing(12)

        sz_lbl = QLabel("Font size:")
        sz_lbl.setStyleSheet("color:#aaa;font-size:12px;")
        style_row.addWidget(sz_lbl)

        self._font_size = QSpinBox()
        self._font_size.setRange(10, 72)
        self._font_size.setValue(24)
        self._font_size.setStyleSheet(
            "background:#2a2a2a;color:white;border:1px solid #444;border-radius:4px;padding:2px;"
        )
        style_row.addWidget(self._font_size)

        pos_lbl = QLabel("Position:")
        pos_lbl.setStyleSheet("color:#aaa;font-size:12px;")
        style_row.addWidget(pos_lbl)

        self._pos_combo = QComboBox()
        self._pos_combo.addItems(["bottom", "top", "center"])
        self._pos_combo.setStyleSheet(self._lang_combo.styleSheet())
        style_row.addWidget(self._pos_combo)

        self._burn_check = QCheckBox("Burn into video")
        self._burn_check.setStyleSheet(
            "QCheckBox{color:#ccc;font-size:12px;spacing:6px;}"
            "QCheckBox::indicator{width:14px;height:14px;}"
            "QCheckBox::indicator:checked{background:#fe2c55;border-radius:3px;}"
            "QCheckBox::indicator:unchecked{background:#333;border:1px solid #555;border-radius:3px;}"
        )
        style_row.addWidget(self._burn_check)
        style_row.addStretch()
        lay.addLayout(style_row)

        # ── Footer buttons ────────────────────────────────────────────
        foot_row = QHBoxLayout()

        export_srt = QPushButton("Export SRT")
        export_srt.setStyleSheet(_BTN)
        export_srt.clicked.connect(lambda: self._export("srt"))
        foot_row.addWidget(export_srt)

        export_vtt = QPushButton("Export VTT")
        export_vtt.setStyleSheet(_BTN)
        export_vtt.clicked.connect(lambda: self._export("vtt"))
        foot_row.addWidget(export_vtt)

        foot_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(_BTN)
        cancel_btn.clicked.connect(self.reject)
        foot_row.addWidget(cancel_btn)

        apply_btn = QPushButton("✓  Apply Subtitles")
        apply_btn.setStyleSheet(_BTN_RED)
        apply_btn.clicked.connect(self._on_apply)
        foot_row.addWidget(apply_btn)

        lay.addLayout(foot_row)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _browse_src(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;All (*)"
        )
        if path:
            self._src_edit.setText(path)
            self._media_path = path

    def _start_transcribe(self):
        path = self._src_edit.text().strip()
        if not path or not os.path.exists(path):
            return

        self._progress.setVisible(True)
        self._progress.setValue(0)

        self._worker = _TranscribeWorker(
            media_path=path,
            language=self._lang_combo.currentText(),
            model=self._model_combo.currentText(),
        )
        self._worker.progress.connect(lambda p: self._progress.setValue(int(p * 100)))
        self._worker.finished.connect(self._on_transcribed)
        self._worker.error.connect(lambda e: self._progress.setVisible(False))
        self._worker.start()

    @pyqtSlot(object)
    def _on_transcribed(self, track: SubtitleTrack):
        self._track = track
        self._progress.setVisible(False)
        self._populate_table(track)

    def _populate_table(self, track: SubtitleTrack):
        self._table.setRowCount(0)
        for sub in track.subtitles:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(str(sub.id)))
            self._table.setItem(row, 1, QTableWidgetItem(f"{sub.start:.2f}"))
            self._table.setItem(row, 2, QTableWidgetItem(f"{sub.end:.2f}"))
            self._table.setItem(row, 3, QTableWidgetItem(sub.text))

    def _read_table_back(self):
        """Sync edits from table back to track."""
        if not self._track:
            return
        for row in range(self._table.rowCount()):
            if row < len(self._track.subtitles):
                sub = self._track.subtitles[row]
                try:
                    sub.start = float(self._table.item(row, 1).text())
                    sub.end   = float(self._table.item(row, 2).text())
                    sub.text  = self._table.item(row, 3).text()
                except Exception:
                    pass

    def _export(self, fmt: str):
        if not self._track:
            return
        self._read_table_back()
        ext = f".{fmt}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", f"subtitles{ext}", f"*{ext}"
        )
        if path:
            if fmt == "srt":
                SubtitleEngine.save_srt(self._track, path)
            elif fmt == "vtt":
                SubtitleEngine.save_vtt(self._track, path)

    def _on_apply(self):
        if not self._track:
            return
        self._read_table_back()
        self.subtitles_applied.emit(self._track)
        self.accept()
