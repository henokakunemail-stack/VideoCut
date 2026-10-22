"""Thin QMediaPlayer wrapper. The player is created lazily so projects without audio never touch QtMultimedia."""

from PyQt6.QtCore import QObject, QUrl


class AudioPreview(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = None
        self._out = None
        self._volume = 1.0
        self.source = None

    def _ensure(self):
        if self._player is None:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
            self._player, self._out = QMediaPlayer(self), QAudioOutput(self)
            self._player.setAudioOutput(self._out)
            self._out.setVolume(self._volume)
        return self._player

    def set_source(self, wav):
        if wav == self.source:
            return
        self.source = wav
        if wav:
            self._ensure().setSource(QUrl.fromLocalFile(wav))
        elif self._player:
            self._player.stop()
            self._player.setSource(QUrl())

    @property
    def ready(self):
        return bool(self.source and self._player)

    def play(self, from_ms=0):
        if self.ready:
            self._player.setPosition(int(from_ms))
            self._player.play()

    def pause(self):
        if self._player:
            self._player.pause()

    def seek(self, ms):
        if self.ready:
            self._player.setPosition(int(ms))

    def set_volume(self, v):
        self._volume = max(0.0, min(1.0, v))
        if self._out:
            self._out.setVolume(self._volume)

    def position_ms(self):
        """None unless actually playing, so the caller falls back to its own clock."""
        if not self.ready:
            return None
        from PyQt6.QtMultimedia import QMediaPlayer
        if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return None
        return self._player.position()
