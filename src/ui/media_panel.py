"""
Media Panel - Left panel with media library, filters, effects, text, stickers, audio
EXPANDED: 37 filters, beauty tools, chroma key, LUTs, masking, beat sync, keyframes
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QTabWidget, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QFileDialog, QSlider, QComboBox, QCheckBox,
    QSpinBox, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont, QIcon

from src.core.project import ClipType


FILTER_LIST = [
    ("None", ""),
    # Classic
    ("Vintage", "vintage"),
    ("Vivid", "vivid"),
    ("Cool", "cool"),
    ("Warm", "warm"),
    ("B&W", "bw"),
    ("Sepia", "sepia"),
    ("Fade", "fade"),
    # Portrait/People
    ("Portrait", "portrait"),
    ("Dreamy", "dreamy"),
    ("Pastel", "pastel"),
    ("Rose", "rose"),
    # Nature
    ("Food", "food"),
    ("Sky", "sky"),
    ("Natural", "natural"),
    ("Tropical", "tropical"),
    ("Ocean", "ocean"),
    ("Mint", "mint"),
    # Time of Day
    ("Dawn", "dawn"),
    ("Dusk", "dusk"),
    ("Golden", "golden"),
    ("Autumn", "autumn"),
    ("Coffee", "coffee"),
    # Cinematic
    ("Cinema", "cinema"),
    ("Film", "film"),
    ("Matte", "matte"),
    ("Moody", "moody"),
    ("Noir", "noir"),
    # Creative
    ("Neon", "neon"),
    ("Lomo", "lomo"),
    ("Polaroid", "polaroid"),
    ("Cross", "cross"),
    ("Ink", "ink"),
    ("Urban", "urban"),
    ("Vibrant", "vibrant"),
    ("Futuristic", "futuristic"),
    ("Retro 80s", "retro80"),
]

EFFECTS_LIST = [
    ("Blur", "blur"),
    ("Glow", "glow"),
    ("Glitch", "glitch"),
    ("Shake", "shake"),
    ("Zoom In", "zoom_in"),
    ("Zoom Out", "zoom_out"),
    ("Spin", "spin"),
    ("Flash", "flash"),
    ("Wave", "wave"),
    ("Mirror", "mirror"),
    ("TV Noise", "tv_noise"),
    ("VHS", "vhs"),
    ("Rain", "rain"),
    ("Snow", "snow"),
    ("Fire", "fire"),
    ("Particles", "particles"),
    # NEW effects
    ("Pixelate", "pixelate"),
    ("Mosaic", "mosaic"),
    ("Old Film", "old_film"),
    ("Glare", "glare"),
    ("Lens Flare", "lens_flare"),
    ("Scanlines", "scanlines"),
    ("Hologram", "hologram"),
    ("Chromatic", "chromatic"),
]

TRANSITIONS_LIST = [
    ("Fade", "fade"),
    ("Wipe Left", "wipe_left"),
    ("Wipe Right", "wipe_right"),
    ("Wipe Up", "wipe_up"),
    ("Wipe Down", "wipe_down"),
    ("Slide Left", "slide_left"),
    ("Slide Right", "slide_right"),
    ("Zoom In", "zoom_in"),
    ("Zoom Out", "zoom_out"),
    ("Rotate", "rotate"),
    ("Dissolve", "dissolve"),
    ("Flash", "flash"),
    ("Blur", "blur"),
    ("Glitch", "glitch"),
    # NEW transitions
    ("Split H", "split_h"),
    ("Split V", "split_v"),
    ("Page Turn", "page_turn"),
    ("Swirl", "swirl"),
    ("Cube", "cube"),
    ("Flip", "flip"),
]

MUSIC_GENRES = [
    "Pop 🎵", "Hip-Hop 🎤", "Electronic 🎛", "Cinematic 🎬",
    "Acoustic 🎸", "Jazz 🎷", "Chill 😌", "Upbeat ⚡",
    "Romantic 💕", "Motivational 💪", "Funny 😂", "Horror 👻",
    "R&B 🎶", "Classical 🎻", "Lo-Fi 🌙", "Dance 🕺",
]

LUT_LIST = [
    ("None", ""),
    ("Bleach Bypass", "bleach_bypass"),
    ("Day for Night", "day_for_night"),
    ("Teal & Orange", "teal_orange"),
    ("Blockbuster", "blockbuster"),
    ("Cinematic Cool", "cinematic_cool"),
    ("Warm Film", "warm_film"),
    ("Faded", "faded"),
    ("Cyberpunk", "cyberpunk"),
    ("Mono Noir", "mono_noir"),
    ("Vivid", "vivid"),
]

MASK_LIST = [
    ("None", ""),
    ("Circle", "circle"),
    ("Rectangle", "rect"),
    ("Star", "star"),
    ("Heart", "heart"),
]

TEXT_PRESETS_EXTENDED = [
    ("Default Text", "default"),
    ("Title", "title"),
    ("Subtitle", "subtitle"),
    ("Bold Text", "bold"),
    ("Neon Text", "neon"),
    ("Graffiti", "graffiti"),
    ("Typewriter", "typewriter"),
    ("Fade In", "fade_in"),
    # New presets
    ("Outline", "outline"),
    ("Shadow Only", "shadow_only"),
    ("Bubble", "bubble"),
    ("Glitch Text", "glitch_text"),
]


class MediaThumb(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, path: str, name: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(96, 54)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background: #333333; border-radius: 4px;")
        layout.addWidget(self.thumb_label)

        name_label = QLabel(name[:14] + ("…" if len(name) > 14 else ""))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #aaaaaa; font-size: 10px; background: transparent;")
        layout.addWidget(name_label)

        self.setStyleSheet("""
            QWidget { background: #2a2a2a; border-radius: 6px; }
            QWidget:hover { background: #3a3a3a; border: 1px solid #fe2c55; }
        """)

        QTimer.singleShot(0, lambda: self._load_thumb(path))

    def _load_thumb(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

        pixmap = None
        if ext in video_exts:
            try:
                from src.core.video_player import VideoReader
                reader = VideoReader(path)
                if reader.is_valid():
                    frame = reader.read_thumbnail((96, 54))
                    if frame is not None:
                        import numpy as np
                        h, w, c = frame.shape
                        qimg = QImage(frame.data, w, h, c * w, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                reader.close()
            except Exception:
                pass
        elif ext in image_exts:
            pixmap = QPixmap(path).scaled(96, 54, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)

        if pixmap and not pixmap.isNull():
            self.thumb_label.setPixmap(pixmap)
        else:
            self.thumb_label.setText(ext.upper())
            self.thumb_label.setStyleSheet("background: #333333; color: #aaaaaa; border-radius: 4px; font-size: 11px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)


class FilterCard(QWidget):
    filter_selected = pyqtSignal(str, str)

    def __init__(self, name: str, filter_id: str, parent=None):
        super().__init__(parent)
        self.filter_name = name
        self.filter_id = filter_id
        self._selected = False
        self.setFixedSize(80, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.preview = QLabel()
        self.preview.setFixedSize(72, 52)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background: #333333; border-radius: 4px;")
        self._render_filter_preview()
        layout.addWidget(self.preview)

        lbl = QLabel(name)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #aaaaaa; font-size: 10px; background: transparent;")
        layout.addWidget(lbl)

        self.setStyleSheet("QWidget { background: #252525; border-radius: 6px; }")

    def _render_filter_preview(self):
        import numpy as np
        img = np.zeros((52, 72, 3), dtype=np.uint8)
        for x in range(72):
            r = int(x / 72 * 255)
            g = int(128)
            b = int(255 - x / 72 * 255)
            img[:, x] = [r, g, b]

        from src.core.video_player import FrameProcessor
        if self.filter_id:
            try:
                preview = FrameProcessor.apply_filter(img.copy(), self.filter_id, 1.0)
            except Exception:
                preview = img
        else:
            preview = img

        h, w, c = preview.shape
        qimg = QImage(preview.data, w, h, c * w, QImage.Format.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(qimg))

    def set_selected(self, sel: bool):
        self._selected = sel
        if sel:
            self.setStyleSheet("QWidget { background: #3a3a3a; border: 2px solid #fe2c55; border-radius: 6px; }")
        else:
            self.setStyleSheet("QWidget { background: #252525; border-radius: 6px; }")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.filter_selected.emit(self.filter_name, self.filter_id)


class EffectCard(QWidget):
    effect_applied = pyqtSignal(str, str)

    COLORS = {
        'blur': '#607d8b', 'glow': '#ffeb3b', 'glitch': '#f44336',
        'shake': '#ff9800', 'zoom_in': '#4caf50', 'zoom_out': '#4caf50',
        'spin': '#2196f3', 'flash': '#fff176', 'wave': '#00bcd4',
        'mirror': '#9c27b0', 'tv_noise': '#795548', 'vhs': '#78909c',
        'rain': '#29b6f6', 'snow': '#e1f5fe', 'fire': '#ff5722',
        'particles': '#e91e63', 'pixelate': '#673ab7', 'mosaic': '#3f51b5',
        'old_film': '#8d6e63', 'glare': '#ffee58', 'lens_flare': '#fff9c4',
        'scanlines': '#546e7a', 'hologram': '#00e5ff', 'chromatic': '#e040fb',
    }

    ICONS = {
        'blur': '💧', 'glow': '✨', 'glitch': '⚡', 'shake': '📳',
        'zoom_in': '🔍', 'zoom_out': '🔎', 'spin': '🌀', 'flash': '💥',
        'wave': '〰', 'mirror': '🪞', 'tv_noise': '📺', 'vhs': '📼',
        'rain': '🌧', 'snow': '❄', 'fire': '🔥', 'particles': '✦',
        'pixelate': '⬜', 'mosaic': '🔲', 'old_film': '🎞', 'glare': '☀',
        'lens_flare': '🌟', 'scanlines': '〓', 'hologram': '💠', 'chromatic': '🌈',
    }

    def __init__(self, name: str, effect_id: str, parent=None):
        super().__init__(parent)
        self.effect_name = name
        self.effect_id = effect_id
        self.setFixedSize(90, 68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        color = self.COLORS.get(effect_id, '#555555')
        icon = self.ICONS.get(effect_id, '✨')
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedHeight(38)
        icon_lbl.setStyleSheet(f"background: {color}33; border-radius: 4px; font-size: 18px;")
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("color: #cccccc; font-size: 10px; background: transparent;")
        layout.addWidget(name_lbl)

        self.setStyleSheet("""
            QWidget { background: #252525; border-radius: 6px; }
            QWidget:hover { background: #333333; border: 1px solid #fe2c55; }
        """)

    def mousePressEvent(self, event):
        self.effect_applied.emit(self.effect_name, self.effect_id)


class MediaPanel(QWidget):
    media_added = pyqtSignal(str)
    filter_selected = pyqtSignal(str, str)
    effect_applied = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_files = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { padding: 5px 8px; font-size: 10px; }
        """)

        self.tabs.addTab(self._build_media_tab(), "📂 Media")
        self.tabs.addTab(self._build_filter_tab(), "🎨 Filter")
        self.tabs.addTab(self._build_effects_tab(), "✨ FX")
        self.tabs.addTab(self._build_text_tab(), "📝 Text")
        self.tabs.addTab(self._build_stickers_tab(), "🎭 Stickers")
        self.tabs.addTab(self._build_audio_tab(), "🎵 Audio")
        self.tabs.addTab(self._build_transitions_tab(), "🔀 Transition")
        self.tabs.addTab(self._build_beauty_tab(), "💄 Beauty")
        self.tabs.addTab(self._build_color_grading_tab(), "🎬 Grade")
        self.tabs.addTab(self._build_overlay_tab(), "🖼 Overlay")

        layout.addWidget(self.tabs)

    def _build_media_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        btn = QPushButton("+ Import Media")
        btn.setStyleSheet("""
            QPushButton {
                background: #333333; color: white; border: 2px dashed #555555;
                border-radius: 8px; padding: 10px; font-size: 12px;
            }
            QPushButton:hover { border-color: #fe2c55; color: #fe2c55; }
        """)
        btn.clicked.connect(self._import_media)
        layout.addWidget(btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.media_container = QWidget()
        self.media_layout = QGridLayout(self.media_container)
        self.media_layout.setContentsMargins(0, 0, 0, 0)
        self.media_layout.setSpacing(6)
        scroll.setWidget(self.media_container)

        self.empty_label = QLabel("Drop media here\nor click Import")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #555555; font-size: 12px;")
        self.media_layout.addWidget(self.empty_label, 0, 0, 1, 2)

        layout.addWidget(scroll, 1)
        return w

    def _build_filter_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        intensity_row = QHBoxLayout()
        intensity_row.addWidget(QLabel("Intensity"))
        self.filter_intensity = QSlider(Qt.Orientation.Horizontal)
        self.filter_intensity.setRange(0, 100)
        self.filter_intensity.setValue(100)
        intensity_row.addWidget(self.filter_intensity, 1)
        intensity_lbl = QLabel("100%")
        intensity_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.filter_intensity.valueChanged.connect(lambda v: intensity_lbl.setText(f"{v}%"))
        intensity_row.addWidget(intensity_lbl)
        layout.addLayout(intensity_row)

        # Category filter
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category"))
        self.filter_cat = QComboBox()
        self.filter_cat.addItems(["All", "Classic", "Portrait", "Nature", "Time of Day", "Cinematic", "Creative"])
        self.filter_cat.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 3px;")
        cat_row.addWidget(self.filter_cat, 1)
        layout.addLayout(cat_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        self._filter_cards = {}
        for i, (name, fid) in enumerate(FILTER_LIST):
            card = FilterCard(name, fid)
            card.filter_selected.connect(self._on_filter_selected)
            grid.addWidget(card, i // 2, i % 2)
            self._filter_cards[fid] = card

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return w

    def _build_effects_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        lbl = QLabel("Video Effects")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        for i, (name, eid) in enumerate(EFFECTS_LIST):
            card = EffectCard(name, eid)
            card.effect_applied.connect(self.effect_applied)
            grid.addWidget(card, i // 2, i % 2)

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return w

    def _build_text_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        lbl = QLabel("Text Styles")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(4)

        for name, preset_id in TEXT_PRESETS_EXTENDED:
            btn = QPushButton(f"Aa  {name}")
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background: #2a2a2a; color: white; font-size: 13px;
                    border: 1px solid #333; border-radius: 6px;
                    text-align: left; padding: 0 12px;
                }
                QPushButton:hover { background: #333; border-color: #fe2c55; }
            """)
            btn.clicked.connect(lambda checked, p=preset_id: self._add_text(p))
            vlay.addWidget(btn)

        vlay.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        add_btn = QPushButton("+ Add Text")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(lambda: self._add_text("default"))
        layout.addWidget(add_btn)
        return w

    def _build_stickers_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        stickers = [
            "❤️", "🔥", "⭐", "💯", "😂", "😍", "🎉", "✨",
            "🌈", "🦋", "🌸", "🎵", "💫", "🌙", "☀️", "⚡",
            "💪", "👑", "🎀", "🌺", "🦄", "🍕", "🌊", "🎸",
            "🏆", "🎤", "🎬", "📸", "🌍", "💎", "🚀", "🎯",
            # New stickers
            "🎭", "🌟", "💥", "🔮", "🎪", "🌀", "🎆", "🎇",
            "🌻", "🍀", "🌴", "❄️", "🎋", "🌮", "🍜", "☕",
        ]

        lbl = QLabel("Stickers & Emoji")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        imp = QPushButton("Import PNG sticker…")
        imp.clicked.connect(self._import_sticker)
        layout.addWidget(imp)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        for i, sticker in enumerate(stickers):
            btn = QPushButton(sticker)
            btn.setFixedSize(48, 48)
            btn.setStyleSheet("""
                QPushButton { background: #2a2a2a; font-size: 22px; border: none; border-radius: 8px; }
                QPushButton:hover { background: #3a3a3a; border: 1px solid #fe2c55; }
            """)
            btn.clicked.connect(lambda checked, s=sticker: self._add_sticker(s))
            grid.addWidget(btn, i // 4, i % 4)

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return w

    def _build_audio_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        import_btn = QPushButton("+ Import Audio")
        import_btn.setStyleSheet("""
            QPushButton { background: #333; color: white; border: 2px dashed #555;
                border-radius: 8px; padding: 8px; font-size: 12px; }
            QPushButton:hover { border-color: #fe2c55; color: #fe2c55; }
        """)
        import_btn.clicked.connect(self._import_audio)
        layout.addWidget(import_btn)

        lbl = QLabel("Music Library")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(4)

        for genre in MUSIC_GENRES:
            btn = QPushButton(genre)
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton { background: #2a2a2a; color: #cccccc; font-size: 12px;
                    border: 1px solid #333; border-radius: 6px;
                    text-align: left; padding: 0 12px; }
                QPushButton:hover { background: #333; color: white; }
            """)
            vlay.addWidget(btn)

        vlay.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Beat sync
        beat_grp = QGroupBox("Beat Sync")
        beat_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        beat_lay = QVBoxLayout(beat_grp)
        beat_lay.setSpacing(4)

        auto_beat_btn = QPushButton("⚡ Auto Beat Sync")
        auto_beat_btn.setFixedHeight(32)
        auto_beat_btn.setStyleSheet("QPushButton { background: #333; color: #ccc; border-radius: 4px; } QPushButton:hover { background: #fe2c55; color: white; }")
        beat_lay.addWidget(auto_beat_btn)

        bpm_row = QHBoxLayout()
        bpm_row.addWidget(QLabel("BPM"))
        bpm_spin = QSpinBox()
        bpm_spin.setRange(60, 200)
        bpm_spin.setValue(120)
        bpm_spin.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px;")
        bpm_row.addWidget(bpm_spin)
        bpm_row.addStretch()
        beat_lay.addLayout(bpm_row)
        layout.addWidget(beat_grp)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("🔊 Volume"))
        vol_slider = QSlider(Qt.Orientation.Horizontal)
        vol_slider.setRange(0, 200)
        vol_slider.setValue(100)
        vol_row.addWidget(vol_slider, 1)
        vol_lbl = QLabel("100%")
        vol_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        vol_slider.valueChanged.connect(lambda v: vol_lbl.setText(f"{v}%"))
        vol_row.addWidget(vol_lbl)
        layout.addLayout(vol_row)
        return w

    def _build_transitions_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        lbl = QLabel("Transitions")
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duration"))
        self.trans_duration = QSlider(Qt.Orientation.Horizontal)
        self.trans_duration.setRange(1, 30)
        self.trans_duration.setValue(5)
        dur_row.addWidget(self.trans_duration, 1)
        dur_lbl = QLabel("0.5s")
        dur_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.trans_duration.valueChanged.connect(lambda v: dur_lbl.setText(f"{v/10:.1f}s"))
        dur_row.addWidget(dur_lbl)
        layout.addLayout(dur_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        TRANS_ICONS = {
            "fade": "◑", "wipe_left": "◀", "wipe_right": "▶",
            "wipe_up": "▲", "wipe_down": "▼", "slide_left": "⇐",
            "slide_right": "⇒", "zoom_in": "⊕", "zoom_out": "⊖",
            "rotate": "↻", "dissolve": "⬡", "flash": "⚡",
            "blur": "⬤", "glitch": "⚠", "split_h": "⇔",
            "split_v": "⇕", "page_turn": "📄", "swirl": "🌀",
            "cube": "⬛", "flip": "🔄",
        }

        for i, (name, tid) in enumerate(TRANSITIONS_LIST):
            card = QWidget()
            card.setFixedSize(90, 72)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)
            card_layout.setSpacing(2)

            icon = QLabel(TRANS_ICONS.get(tid, "▷"))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedHeight(44)
            icon.setStyleSheet("background: #333333; border-radius: 4px; font-size: 22px; color: white;")
            card_layout.addWidget(icon)

            lbl2 = QLabel(name)
            lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl2.setStyleSheet("color: #aaaaaa; font-size: 10px; background: transparent;")
            card_layout.addWidget(lbl2)

            card.setStyleSheet("QWidget { background: #252525; border-radius: 6px; } QWidget:hover { background: #333; border: 1px solid #fe2c55; }")
            card.setToolTip(f"Apply '{name}' at the start of the selected clip")
            card.mousePressEvent = lambda ev, t=tid: self._apply_transition(t)
            grid.addWidget(card, i // 2, i % 2)

        none_btn = QPushButton("Remove transition")
        none_btn.clicked.connect(lambda: self._apply_transition(""))
        layout.addWidget(none_btn)

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return w

    def _build_beauty_tab(self) -> QWidget:
        """Beauty tools — skin smooth, whitening, slimming, etc."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Beauty Retouch")
        title.setStyleSheet("color: #fe2c55; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(8)

        beauty_controls = [
            ("Skin Smooth", "skin_smooth", 0, 100, 0),
            ("Whitening", "whitening", 0, 100, 0),
            ("Noise Reduce", "noise_reduction", 0, 100, 0),
            ("Skin Tone", "skin_tone", -50, 50, 0),
            ("Eye Enhance", "eye_enhance", 0, 100, 0),
            ("Clarity", "clarity", 0, 100, 0),
            ("Grain", "grain", 0, 100, 0),
            ("Dehaze", "dehaze", 0, 100, 0),
        ]

        for label, attr, mn, mx, default in beauty_controls:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
            row.addWidget(lbl)

            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(mn, mx)
            sl.setValue(default)
            row.addWidget(sl, 1)

            val_lbl = QLabel(f"{default}")
            val_lbl.setFixedWidth(30)
            val_lbl.setStyleSheet("color: #ccc; font-size: 11px; background: transparent;")
            sl.valueChanged.connect(lambda v, vl=val_lbl, a=attr: (vl.setText(str(v)), self._apply_beauty(a, v)))
            row.addWidget(val_lbl)

            vlay.addLayout(row)

        vlay.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        reset_btn = QPushButton("Reset All Beauty")
        reset_btn.setStyleSheet("QPushButton { background: #333; color: #ccc; border-radius: 4px; padding: 6px; } QPushButton:hover { background: #444; }")
        layout.addWidget(reset_btn)
        return w

    def _build_color_grading_tab(self) -> QWidget:
        """Professional color grading — LUTs, HSL, curves"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Color Grading")
        title.setStyleSheet("color: #fe2c55; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        # LUT section
        lut_grp = QGroupBox("LUT Presets")
        lut_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        lut_lay = QVBoxLayout(lut_grp)

        self.lut_combo = QComboBox()
        for name, lut_id in LUT_LIST:
            self.lut_combo.addItem(name, lut_id)
        self.lut_combo.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 4px;")
        self.lut_combo.currentIndexChanged.connect(self._apply_lut)
        lut_lay.addWidget(self.lut_combo)

        lut_intensity_row = QHBoxLayout()
        lut_intensity_row.addWidget(QLabel("Strength"))
        self.lut_strength = QSlider(Qt.Orientation.Horizontal)
        self.lut_strength.setRange(0, 100)
        self.lut_strength.setValue(100)
        lut_intensity_row.addWidget(self.lut_strength, 1)
        lut_lbl = QLabel("100%")
        lut_lbl.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.lut_strength.valueChanged.connect(lambda v: lut_lbl.setText(f"{v}%"))
        lut_intensity_row.addWidget(lut_lbl)
        lut_lay.addLayout(lut_intensity_row)
        layout.addWidget(lut_grp)

        hint = QLabel("Wheels, HSL & curves: Properties > Grade")
        hint.setStyleSheet("color: #888; font-size: 10px; background: transparent;")
        layout.addWidget(hint)

        # Mask section
        mask_grp = QGroupBox("Shape Mask")
        mask_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        mask_lay = QVBoxLayout(mask_grp)

        self.mask_combo = QComboBox()
        for name, mid in MASK_LIST:
            self.mask_combo.addItem(name, mid)
        self.mask_combo.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 4px;")
        mask_lay.addWidget(self.mask_combo)

        feather_row = QHBoxLayout()
        feather_row.addWidget(QLabel("Feather"))
        self.mask_feather = QSlider(Qt.Orientation.Horizontal)
        self.mask_feather.setRange(0, 50)
        self.mask_feather.setValue(10)
        feather_row.addWidget(self.mask_feather, 1)
        feather_lbl = QLabel("10%")
        feather_lbl.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.mask_feather.valueChanged.connect(lambda v: feather_lbl.setText(f"{v}%"))
        feather_row.addWidget(feather_lbl)
        mask_lay.addLayout(feather_row)
        layout.addWidget(mask_grp)

        layout.addStretch()
        return w

    def _build_overlay_tab(self) -> QWidget:
        """Overlay tools: chroma key, picture-in-picture, watermark"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Overlay & FX")
        title.setStyleSheet("color: #fe2c55; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        # Chroma key
        chroma_grp = QGroupBox("Chroma Key (Green Screen)")
        chroma_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        chroma_lay = QVBoxLayout(chroma_grp)

        self.chroma_enable = QCheckBox("Enable Chroma Key")
        self.chroma_enable.setStyleSheet("color: white; font-size: 12px;")
        chroma_lay.addWidget(self.chroma_enable)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Key Color"))
        self.chroma_color_btn = QPushButton()
        self.chroma_color_btn.setFixedSize(36, 24)
        self.chroma_color_btn.setStyleSheet("background: #00b140; border-radius: 4px; border: 1px solid #555;")
        color_row.addWidget(self.chroma_color_btn)

        self.chroma_preset = QComboBox()
        self.chroma_preset.addItems(["Green", "Blue", "Custom"])
        self.chroma_preset.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 3px;")
        color_row.addWidget(self.chroma_preset)
        chroma_lay.addLayout(color_row)

        tol_row = QHBoxLayout()
        tol_row.addWidget(QLabel("Tolerance"))
        self.chroma_tolerance = QSlider(Qt.Orientation.Horizontal)
        self.chroma_tolerance.setRange(1, 80)
        self.chroma_tolerance.setValue(30)
        tol_row.addWidget(self.chroma_tolerance, 1)
        tol_lbl = QLabel("30")
        tol_lbl.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.chroma_tolerance.valueChanged.connect(lambda v: tol_lbl.setText(str(v)))
        tol_row.addWidget(tol_lbl)
        chroma_lay.addLayout(tol_row)
        layout.addWidget(chroma_grp)

        # PIP / Watermark
        pip_grp = QGroupBox("Picture-in-Picture / Watermark")
        pip_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        pip_lay = QVBoxLayout(pip_grp)

        add_pip_btn = QPushButton("+ Add Overlay Image")
        add_pip_btn.setStyleSheet("QPushButton { background: #333; color: #ccc; border-radius: 4px; padding: 6px; } QPushButton:hover { background: #444; }")
        add_pip_btn.clicked.connect(self._import_overlay)
        pip_lay.addWidget(add_pip_btn)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity"))
        self.pip_opacity = QSlider(Qt.Orientation.Horizontal)
        self.pip_opacity.setRange(0, 100)
        self.pip_opacity.setValue(100)
        opacity_row.addWidget(self.pip_opacity, 1)
        op_lbl = QLabel("100%")
        op_lbl.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.pip_opacity.valueChanged.connect(lambda v: op_lbl.setText(f"{v}%"))
        opacity_row.addWidget(op_lbl)
        pip_lay.addLayout(opacity_row)
        layout.addWidget(pip_grp)

        # Keyframe animation
        kf_grp = QGroupBox("Keyframe Animation")
        kf_grp.setStyleSheet("QGroupBox { color: #aaa; border: 1px solid #333; border-radius: 6px; margin-top: 8px; padding-top: 6px; }")
        kf_lay = QVBoxLayout(kf_grp)

        add_kf_btn = QPushButton("◆ Add Keyframe at Playhead")
        add_kf_btn.setFixedHeight(32)
        add_kf_btn.setStyleSheet("QPushButton { background: #333; color: #ccc; border-radius: 4px; } QPushButton:hover { background: #fe2c55; color: white; }")
        kf_lay.addWidget(add_kf_btn)

        kf_props = QComboBox()
        kf_props.addItems(["Position", "Scale", "Rotation", "Opacity", "Brightness", "Saturation"])
        kf_props.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 3px;")
        kf_lay.addWidget(kf_props)

        easing_row = QHBoxLayout()
        easing_row.addWidget(QLabel("Easing"))
        easing = QComboBox()
        easing.addItems(["Linear", "Ease In", "Ease Out", "Ease In-Out", "Bounce", "Elastic"])
        easing.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 3px;")
        easing_row.addWidget(easing, 1)
        kf_lay.addLayout(easing_row)
        layout.addWidget(kf_grp)

        layout.addStretch()
        return w

    # ---- Actions ----

    def add_media_file(self, path: str):
        if path in self.media_files:
            return
        self.media_files.append(path)
        if self.empty_label:
            self.empty_label.hide()

        name = os.path.basename(path)
        thumb = MediaThumb(path, name)
        thumb.clicked.connect(self.media_added)

        count = len(self.media_files) - 1
        self.media_layout.addWidget(thumb, count // 2, count % 2)

    def _import_media(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media", "",
            "Media Files (*.mp4 *.mov *.avi *.mkv *.webm *.jpg *.jpeg *.png *.gif *.bmp)"
        )
        for p in paths:
            self.add_media_file(p)

    def _import_audio(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Audio", "",
            "Audio Files (*.mp3 *.wav *.aac *.ogg *.flac)"
        )
        for p in paths:
            self.add_media_file(p)

    def _import_overlay(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Overlay Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp)"
        )
        if path:
            self.add_media_file(path)

    def _on_filter_selected(self, name: str, fid: str):
        for f_id, card in self._filter_cards.items():
            card.set_selected(f_id == fid)
        self.filter_selected.emit(name, fid)

    def _selected_clip(self):
        getter = getattr(self.window(), '_get_selected_clip', None)
        return getter() if getter else None

    def _notify_clip_changed(self, clip):
        cb = getattr(self.window(), '_on_clip_property_changed', None)
        if cb:
            cb(clip.id)

    def _apply_beauty(self, attr: str, value: int):
        clip = self._selected_clip()
        if clip and hasattr(clip, attr):
            setattr(clip, attr, value / 100.0)
            self._notify_clip_changed(clip)

    def _apply_lut(self, idx: int):
        clip = self._selected_clip()
        if clip:
            clip.lut_id = self.lut_combo.itemData(idx) or ""
            self._notify_clip_changed(clip)

    def _add_text(self, preset: str):
        from src.ui.text_dialog import TextDialog
        from PyQt6.QtWidgets import QDialog
        parent = self.window()
        dlg = TextDialog(self, preset)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            clip = dlg.get_clip()
            if clip and hasattr(parent, 'project'):
                parent.project.add_clip(clip)
                if hasattr(parent, '_refresh_timeline'):
                    parent._refresh_timeline()

    def _apply_transition(self, tid: str):
        clip = self._selected_clip()
        if not clip:
            return
        clip.transition_in = tid
        clip.transition_in_duration = self.trans_duration.value() * 100
        self._notify_clip_changed(clip)

    @staticmethod
    def _emoji_png(emoji: str) -> str:
        """Render an emoji to a transparent PNG (cached in %TEMP%/videocut_stickers)."""
        import os, tempfile
        from PyQt6.QtGui import QImage, QPainter, QFont, QColor
        d = os.path.join(tempfile.gettempdir(), 'videocut_stickers')
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, '-'.join(f'{ord(c):x}' for c in emoji) + '.png')
        if not os.path.exists(path):
            img = QImage(256, 256, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            p = QPainter(img)
            f = QFont('Segoe UI Emoji')
            f.setPixelSize(200)
            p.setFont(f)
            p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
            p.end()
            img.save(path)
        return path

    def _add_sticker(self, emoji: str):
        self._add_sticker_file(self._emoji_png(emoji))

    def _import_sticker(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import PNG Sticker", "", "Images (*.png *.webp *.jpg *.jpeg)")
        if path:
            self._add_sticker_file(path)

    def _add_sticker_file(self, path: str):
        from src.core.project import Clip, ClipType
        parent = self.window()
        if hasattr(parent, 'project'):
            start = parent.project.settings.duration
            clip = Clip(
                clip_type=ClipType.STICKER, source_path=path, track=1,
                timeline_start=start, timeline_end=start + 3000,
                source_start=0, source_end=3000,
            )
            parent.project.add_clip(clip)
            if hasattr(parent, '_refresh_timeline'):
                parent._refresh_timeline()
