"""
Main Window - professional layout
"""

import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog,
    QMessageBox, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QFont

from src.core.project import Project, Clip, ClipType, AudioTrack
from src.ui.preview_panel import PreviewPanel
from src.ui.timeline_panel import TimelinePanel
from src.ui.toolbar_panel import TopToolbar
from src.ui.media_panel import MediaPanel
from src.ui.properties_panel import PropertiesPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self.current_time_ms = 0
        self.is_playing = False
        self.play_timer = QTimer()
        self.play_timer.setInterval(33)  # ~30fps
        self.play_timer.timeout.connect(self._on_play_tick)

        self.setWindowTitle("VideoCut")
        self.setMinimumSize(1280, 720)
        self.resize(1600, 900)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._new_project()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top toolbar
        self.top_toolbar = TopToolbar(self)
        main_layout.addWidget(self.top_toolbar)

        # Main content splitter (horizontal)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(2)

        # Left: Media panel
        self.media_panel = MediaPanel(self)
        self.media_panel.setMinimumWidth(220)
        self.media_panel.setMaximumWidth(360)
        self.h_splitter.addWidget(self.media_panel)

        # Center: Preview + timeline (vertical splitter)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(2)

        # Preview panel
        self.preview_panel = PreviewPanel(self)
        self.v_splitter.addWidget(self.preview_panel)

        # Timeline panel
        self.timeline_panel = TimelinePanel(self)
        self.timeline_panel.setMinimumHeight(180)
        self.v_splitter.addWidget(self.timeline_panel)

        self.v_splitter.setSizes([500, 260])
        self.h_splitter.addWidget(self.v_splitter)

        # Right: Properties panel
        self.properties_panel = PropertiesPanel(self)
        self.properties_panel.setMinimumWidth(260)
        self.properties_panel.setMaximumWidth(340)
        self.h_splitter.addWidget(self.properties_panel)

        self.h_splitter.setSizes([280, 900, 300])
        main_layout.addWidget(self.h_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background: #111111; color: #aaaaaa; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("File")
        new_act = QAction("New Project", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_project)
        file_menu.addAction(new_act)

        open_act = QAction("Open Project...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._open_project)
        file_menu.addAction(open_act)

        save_act = QAction("Save Project", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_project)
        file_menu.addAction(save_act)

        save_as_act = QAction("Save Project As...", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        import_act = QAction("Import Media...", self)
        import_act.setShortcut(QKeySequence("Ctrl+I"))
        import_act.triggered.connect(self._import_media)
        file_menu.addAction(import_act)

        file_menu.addSeparator()

        export_act = QAction("Export Video...", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._export_video)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        exit_act = QAction("Exit", self)
        exit_act.setShortcut(QKeySequence.StandardKey.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Edit
        edit_menu = menubar.addMenu("Edit")
        undo_act = QAction("Undo", self)
        undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_act)

        redo_act = QAction("Redo", self)
        redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_act)

        edit_menu.addSeparator()

        split_act = QAction("Split Clip", self)
        split_act.setShortcut(QKeySequence("Ctrl+B"))
        split_act.triggered.connect(self._split_clip)
        edit_menu.addAction(split_act)

        delete_act = QAction("Delete Clip", self)
        delete_act.setShortcut(QKeySequence.StandardKey.Delete)
        delete_act.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_act)

        # View
        view_menu = menubar.addMenu("View")
        preview_full = QAction("Preview Fullscreen", self)
        preview_full.setShortcut(QKeySequence("F11"))
        view_menu.addAction(preview_full)
        scopes_act = QAction("Video Scopes", self)
        scopes_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        scopes_act.triggered.connect(self._show_scopes)
        view_menu.addAction(scopes_act)

        # AI Tools menu
        ai_menu = menubar.addMenu("✨ AI Tools")

        caption_act = QAction("🎙 Auto Captions (Whisper)...", self)
        caption_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        caption_act.triggered.connect(self._open_auto_captions)
        ai_menu.addAction(caption_act)

        rembg_act = QAction("🪄 Remove Background (AI)...", self)
        rembg_act.setShortcut(QKeySequence("Ctrl+Shift+B"))
        rembg_act.triggered.connect(self._open_bg_removal)
        ai_menu.addAction(rembg_act)

        ai_menu.addSeparator()

        beat_act = QAction("🥁 Auto Beat Sync...", self)
        beat_act.triggered.connect(self._open_beat_sync)
        ai_menu.addAction(beat_act)

        voice_act = QAction("🎤 Voice Changer...", self)
        voice_act.triggered.connect(self._open_voice_fx)
        ai_menu.addAction(voice_act)

        kenburns_act = QAction("🎬 Ken Burns Effect...", self)
        kenburns_act.triggered.connect(self._open_ken_burns)
        ai_menu.addAction(kenburns_act)

        keyframe_act = QAction("◆ Keyframe Animation...", self)
        keyframe_act.setShortcut(QKeySequence("Ctrl+K"))
        keyframe_act.triggered.connect(self._open_keyframes)
        ai_menu.addAction(keyframe_act)

        stab_act = QAction("📐 Stabilize Clip...", self)
        stab_act.triggered.connect(lambda: self._focus_motion_tab("Stabilize"))
        ai_menu.addAction(stab_act)
        slomo_act = QAction("🐢 Smooth Slow-mo...", self)
        slomo_act.triggered.connect(lambda: self._focus_motion_tab("Smooth slow-mo"))
        ai_menu.addAction(slomo_act)

        # Help
        help_menu = menubar.addMenu("Help")
        about_act = QAction("About VideoCut", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _connect_signals(self):
        # Media panel -> timeline
        self.media_panel.media_added.connect(self._on_media_added)
        self.media_panel.filter_selected.connect(self._on_filter_selected)
        self.media_panel.effect_applied.connect(self._on_effect_card)

        # Timeline -> preview
        self.timeline_panel.time_changed.connect(self._on_time_changed)
        self.timeline_panel.clip_selected.connect(self._on_clip_selected)
        self.timeline_panel.clip_deleted.connect(self._on_clip_deleted)

        # Preview controls -> playback
        self.preview_panel.play_toggled.connect(self._toggle_play)
        self.preview_panel.seek_requested.connect(self._seek_to)
        self.preview_panel.time_changed.connect(self._seek_to)

        # Properties -> project update
        self.properties_panel.clip_changed.connect(self._on_clip_property_changed)
        self.properties_panel.clip_timing_changed.connect(self._on_clip_timing_changed)
        self.properties_panel.freeze_requested.connect(self._freeze_frame)
        self.timeline_panel.freeze_requested.connect(self._freeze_frame)
        self.timeline_panel.reverse_requested.connect(self._toggle_reverse)
        self.properties_panel.effect_params_changed.connect(self._on_effect_params_changed)

        # Toolbar
        self.top_toolbar.export_clicked.connect(self._export_video)
        self.top_toolbar.split_clicked.connect(self._split_clip)
        self.top_toolbar.delete_clicked.connect(self._delete_selected)
        self.top_toolbar.import_clicked.connect(self._import_media)

    # ---- Project management ----

    def _new_project(self):
        self.project = Project()
        self.current_time_ms = 0
        self.is_playing = False
        self.play_timer.stop()
        self._refresh_all()
        self.setWindowTitle("VideoCut - Untitled Project")
        self.status_bar.showMessage("New project created")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "VideoCut Project (*.ccproj)"
        )
        if path:
            try:
                self.project = Project.load(path)
                self._refresh_all()
                self.setWindowTitle(f"VideoCut - {self.project.name}")
                self.status_bar.showMessage(f"Opened: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project:\n{e}")

    def _save_project(self):
        if not self.project.path:
            self._save_project_as()
        else:
            try:
                self.project.save(self.project.path)
                self.status_bar.showMessage(f"Saved: {self.project.path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project:\n{e}")

    def _save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", self.project.name, "VideoCut Project (*.ccproj)"
        )
        if path:
            if not path.endswith('.ccproj'):
                path += '.ccproj'
            self.project.name = os.path.splitext(os.path.basename(path))[0]
            self.project.save(path)
            self.setWindowTitle(f"VideoCut - {self.project.name}")
            self.status_bar.showMessage(f"Saved: {path}")

    def _import_media(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media", "",
            "Media Files (*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.aac *.jpg *.jpeg *.png *.gif *.bmp)"
        )
        for path in paths:
            self.media_panel.add_media_file(path)
        if paths:
            self.status_bar.showMessage(f"Imported {len(paths)} file(s)")

    def _export_video(self):
        from src.ui.export_dialog import ExportDialog
        dlg = ExportDialog(self.project, self)
        dlg.exec()

    def _refresh_all(self):
        self.timeline_panel.set_project(self.project)
        self.preview_panel.set_project(self.project)
        self.preview_panel.seek_to(0)
        self.properties_panel.clear()

    # ---- Playback ----

    def _toggle_play(self, playing: bool):
        self.is_playing = playing
        if playing:
            self.play_timer.start()
        else:
            self.play_timer.stop()

    def _on_play_tick(self):
        if not self.project.settings.duration:
            self.play_timer.stop()
            self.is_playing = False
            self.preview_panel.set_playing(False)
            return

        self.current_time_ms += 33
        if self.current_time_ms >= self.project.settings.duration:
            self.current_time_ms = 0
            self.play_timer.stop()
            self.is_playing = False
            self.preview_panel.set_playing(False)

        self.preview_panel.seek_to(self.current_time_ms)
        self.timeline_panel.set_playhead(self.current_time_ms)

    def _seek_to(self, time_ms: int):
        self.current_time_ms = max(0, time_ms)
        self.preview_panel.seek_to(self.current_time_ms)
        self.timeline_panel.set_playhead(self.current_time_ms)

    def _on_time_changed(self, time_ms: int):
        self.current_time_ms = time_ms
        self.preview_panel.seek_to(time_ms)

    # ---- Clips ----

    def _on_media_added(self, path: str):
        """Add media from media panel to timeline."""
        ext = os.path.splitext(path)[1].lower()
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        audio_exts = {'.mp3', '.wav', '.aac', '.ogg', '.flac'}
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

        if ext in video_exts:
            self._add_video_clip(path)
        elif ext in audio_exts:
            self._add_audio_clip(path)
        elif ext in image_exts:
            self._add_image_clip(path)

    def _add_video_clip(self, path: str):
        from src.core.video_player import VideoReader
        reader = VideoReader(path)
        duration = reader.duration_ms if reader.is_valid() else 5000
        reader.close()

        start = self.project.settings.duration
        clip = Clip(
            clip_type=ClipType.VIDEO,
            source_path=path,
            track=0,
            timeline_start=start,
            timeline_end=start + duration,
            source_start=0,
            source_end=duration,
        )
        self.project.add_clip(clip)
        self._refresh_timeline()

    def _add_image_clip(self, path: str):
        start = self.project.settings.duration
        clip = Clip(
            clip_type=ClipType.IMAGE,
            source_path=path,
            track=0,
            timeline_start=start,
            timeline_end=start + 5000,
            source_start=0,
            source_end=5000,
        )
        self.project.add_clip(clip)
        self._refresh_timeline()

    def _add_audio_clip(self, path: str):
        track = AudioTrack(
            source_path=path,
            name=os.path.basename(path),
            timeline_start=0,
            timeline_end=self.project.settings.duration or 30000,
        )
        self.project.add_audio_track(track)
        self._refresh_timeline()

    def _on_clip_selected(self, clip_id: str):
        clip = self.project.get_clip(clip_id)
        self.properties_panel.set_clip(clip)

    def _on_filter_selected(self, name: str, filter_id: str):
        clip = self._get_selected_clip()
        if not clip:
            self.status_bar.showMessage("Select a clip first to apply a filter")
            return
        clip.filter_id = filter_id
        self._on_clip_property_changed(clip.id)

    def _on_effect_card(self, name: str, card_id: str):
        """Effect card click: toggle the effect on the selected clip."""
        from src.core.renderer import CARD_EFFECTS, set_effect
        clip = self._get_selected_clip()
        if not clip:
            self.status_bar.showMessage("Select a clip first")
            return
        eid, params = CARD_EFFECTS[card_id]
        on = any(e.effect_id == eid for e in clip.effects)
        set_effect(clip, eid, {**params, 'enabled': not on})
        self.status_bar.showMessage(f"{name} {'removed' if on else 'applied'}")
        self._on_clip_property_changed(clip.id)

    def _on_effect_params_changed(self, effect_id: str, params: dict):
        from src.core.renderer import set_effect
        clip = self._get_selected_clip()
        if clip:
            set_effect(clip, effect_id, params)
            self._on_clip_property_changed(clip.id)

    def _on_clip_deleted(self, clip_id: str):
        self.project.remove_clip(clip_id)
        self.properties_panel.clear()
        self._refresh_timeline()

    def _on_clip_property_changed(self, clip_id: str):
        self.preview_panel.seek_to(self.current_time_ms)
        self.timeline_panel.update()

    def _on_clip_timing_changed(self, clip_id: str):
        self.project.retime_clip(clip_id)
        self._refresh_timeline()

    def _focus_motion_tab(self, what: str):
        pp = self.properties_panel
        if not self._get_selected_clip():
            self.status_bar.showMessage("Select a video clip first")
            return
        for i in range(pp.tabs.count()):
            if pp.tabs.tabText(i).startswith("Speed"):
                pp.tabs.setCurrentIndex(i)
        self.status_bar.showMessage(f"{what}: use the Speed tab")

    def _freeze_frame(self, clip_id: str):
        if self.project.freeze_frame(clip_id, self.current_time_ms):
            self._refresh_timeline()
            self.status_bar.showMessage("Freeze frame inserted")
        else:
            self.status_bar.showMessage("Move the playhead inside a video clip first")

    def _toggle_reverse(self, clip_id: str):
        clip = self.project.get_clip(clip_id)
        if clip and clip.clip_type in (ClipType.VIDEO, ClipType.AUDIO) and not clip.freeze:
            clip.reverse = not clip.reverse
            self._refresh_timeline()
            self.properties_panel.set_clip(clip)

    def _split_clip(self):
        sel = self.timeline_panel.selected_clip_id
        if sel:
            new_clip = self.project.split_clip(sel, self.current_time_ms)
            if new_clip:
                self._refresh_timeline()
                self.status_bar.showMessage("Clip split")

    def _delete_selected(self):
        sel = self.timeline_panel.selected_clip_id
        if sel:
            self.project.remove_clip(sel)
            self.properties_panel.clear()
            self._refresh_timeline()

    def _refresh_timeline(self):
        self.timeline_panel.set_project(self.project)
        self.preview_panel.set_project(self.project)
        self.preview_panel.seek_to(self.current_time_ms)

    # ---- AI Tools ----

    def _open_auto_captions(self):
        """Open auto-caption / subtitle dialog (Whisper)."""
        try:
            from src.ui.subtitle_dialog import SubtitleDialog
            dlg = SubtitleDialog(self.project, self)
            dlg.captions_ready.connect(self._on_captions_ready)
            dlg.exec()
        except ImportError as e:
            QMessageBox.warning(self, "Auto Captions",
                f"Could not load subtitle module:\n{e}\n\n"
                "Make sure openai-whisper is installed:\n  pip install openai-whisper")

    def _on_captions_ready(self, clips):
        """Add subtitle clips returned from SubtitleDialog to the timeline."""
        for clip in clips:
            self.project.add_clip(clip)
        self._refresh_timeline()
        self.status_bar.showMessage(f"Added {len(clips)} subtitle clip(s) to timeline")

    def _open_bg_removal(self):
        """Open AI background removal panel."""
        try:
            from src.ui.background_panel import BackgroundPanel
            # Show as a floating dock-style dialog
            dlg = BackgroundPanel(self)
            dlg.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
            dlg.setWindowTitle("AI Background Removal")
            dlg.resize(320, 480)
            dlg.bg_remove_toggled.connect(self._on_bg_remove_toggled)
            dlg.bg_replaced.connect(self._on_bg_replaced)
            dlg.show()
        except ImportError as e:
            QMessageBox.warning(self, "Background Removal",
                f"Could not load background module:\n{e}\n\n"
                "Make sure rembg is installed:\n  pip install rembg")

    def _on_bg_remove_toggled(self, enabled: bool):
        clip = self._get_selected_clip()
        if clip:
            clip.remove_background = enabled
            self._on_clip_property_changed(clip.id)

    def _on_bg_replaced(self, bg_path: str):
        clip = self._get_selected_clip()
        if clip:
            clip.background_path = bg_path
            self._on_clip_property_changed(clip.id)

    def _open_beat_sync(self):
        """Open beat sync dialog."""
        try:
            from src.core.beat_sync import BeatSyncEngine
            # Find audio tracks
            if not self.project.audio_tracks:
                QMessageBox.information(self, "Beat Sync",
                    "Add an audio/music track to the timeline first,\n"
                    "then use Beat Sync to snap clips to the beat.")
                return
            audio_path = self.project.audio_tracks[0].source_path
            engine = BeatSyncEngine()
            self.status_bar.showMessage("Detecting beats…")

            beats = engine.detect_beats(audio_path)
            if not beats:
                QMessageBox.information(self, "Beat Sync", "No beats detected in audio track.")
                return

            bpm = engine.get_bpm(audio_path)
            reply = QMessageBox.question(self, "Beat Sync",
                f"Detected {len(beats)} beats at ~{bpm:.1f} BPM.\n\n"
                "Sync main-track clips to beats?\n"
                "(clips will be snapped to nearest beat boundary)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                synced = engine.sync_clips_to_beats(
                    self.project.clips, beats, mode='snap')
                for clip in synced:
                    self.project.update_clip(clip)
                self._refresh_timeline()
                self.status_bar.showMessage(f"Synced {len(synced)} clips to {len(beats)} beats")
        except ImportError as e:
            QMessageBox.warning(self, "Beat Sync",
                f"Could not load beat sync module:\n{e}\n\n"
                "Make sure librosa is installed:\n  pip install librosa")

    def _open_voice_fx(self):
        """Open voice changer / audio FX dialog."""
        try:
            from src.ui.audio_fx_panel import AudioFxPanel
            dlg = AudioFxPanel(self.project, self)
            dlg.setWindowFlags(Qt.WindowType.Window)
            dlg.setWindowTitle("Voice Changer & Audio FX")
            dlg.resize(380, 560)
            dlg.show()
        except ImportError as e:
            QMessageBox.warning(self, "Voice Changer",
                f"Could not load audio FX module:\n{e}\n\n"
                "Make sure scipy is installed:\n  pip install scipy")

    def _show_scopes(self):
        from src.ui.scopes_panel import ScopesDialog
        if getattr(self, '_scopes', None) is None:
            self._scopes = ScopesDialog(self)
            self.preview_panel.frame_rendered.connect(self._scopes.update_frame)
        self._scopes.show()
        self._scopes.raise_()
        self.preview_panel.seek_to(self.preview_panel.current_time)

    def _open_ken_burns(self):
        """Apply Ken Burns (slow zoom/pan) effect to selected clip."""
        clip = self._get_selected_clip()
        if not clip:
            QMessageBox.information(self, "Ken Burns",
                "Select a video or image clip first.")
            return
        # zoom 1.0 -> 1.2 with a gentle pan right over the whole clip
        end = clip.duration / 1000.0
        clip.keyframes = [
            {'time': 0.0, 'props': {'scale': 1.0, 'pos_x': 0.0}, 'easing': 'ease_in_out'},
            {'time': end, 'props': {'scale': 1.2, 'pos_x': 0.1}, 'easing': 'ease_in_out'},
        ]
        self._on_clip_property_changed(clip.id)
        self.status_bar.showMessage(f"Ken Burns applied to clip: {clip.id[:8]}…")

    def _open_keyframes(self):
        """Open keyframe animation panel for selected clip."""
        clip = self._get_selected_clip()
        if not clip:
            QMessageBox.information(self, "Keyframe Animation",
                "Select a clip first, then open keyframe editor.")
            return
        try:
            from src.ui.keyframe_panel import KeyframePanel
            from src.core.keyframe_engine import KeyframeAnimator, KeyframeTrack
            animator = KeyframeAnimator()
            animator._tracks[clip.id] = KeyframeTrack.from_dict(
                {'clip_id': clip.id, 'keyframes': [k for k in clip.keyframes if 'props' in k]})
            dlg = KeyframePanel(animator, self)
            dlg.setWindowFlags(Qt.WindowType.Window)
            dlg.setWindowTitle(f"Keyframes — {os.path.basename(clip.source_path) or clip.clip_type.value}")
            dlg.resize(420, 640)
            dlg.set_clip(clip.id)
            dlg.set_time(max(0.0, (self.current_time_ms - clip.timeline_start) / 1000.0))
            sync = lambda *_: self._sync_keyframes(clip.id, animator)
            dlg.keyframe_changed.connect(sync)
            dlg.keyframe_removed.connect(sync)
            dlg.show()
        except ImportError as e:
            QMessageBox.warning(self, "Keyframes",
                f"Could not load keyframe panel:\n{e}")

    def _sync_keyframes(self, clip_id: str, animator):
        clip = self.project.get_clip(clip_id)
        if clip:
            clip.keyframes = animator.get_track(clip_id).to_dict()['keyframes']
            self.project.is_modified = True
            self._on_clip_property_changed(clip_id)

    def _get_selected_clip(self):
        """Return the currently selected Clip object, or None."""
        sel = self.timeline_panel.selected_clip_id
        return self.project.get_clip(sel) if sel else None

    def _show_about(self):
        QMessageBox.about(self, "About VideoCut",
            "<h2>VideoCut v3.0</h2>"
            "<p>A professional video editor professional video editor.</p>"
            "<p><b>Features:</b> 37 filters · Beauty retouch · Chroma key · "
            "Color grading (LUTs) · Shape masks · Auto captions (Whisper) · "
            "AI background removal · Beat sync · Keyframe animation · "
            "Motion blur · Ken Burns · Voice changer · Audio FX</p>"
            "<p>Built with Python, PyQt6, OpenCV, and SciPy.</p>"
            "<p>© 2026 HenokDev</p>"
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.preview_panel.toggle_play()
        elif event.key() == Qt.Key.Key_Left:
            self._seek_to(max(0, self.current_time_ms - 33))
        elif event.key() == Qt.Key.Key_Right:
            self._seek_to(self.current_time_ms + 33)
        elif event.key() == Qt.Key.Key_Home:
            self._seek_to(0)
        elif event.key() == Qt.Key.Key_End:
            self._seek_to(self.project.settings.duration)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.project.is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_project()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
