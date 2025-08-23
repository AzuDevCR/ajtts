# AquaJupiterTTS
# Copyright (C) 2025  AzuDevCR (INL Creations)
# Licensed under GPLv3 (see LICENSE file for details).

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import os

class AudioController(QObject):
    started = Signal(str) # file path when playback starts
    finished = Signal(str) # file path when playback reaches EndOfMedia
    stopped = Signal() # User stop or interruption
    error = Signal(str) # error str

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._auto_cleanup = True

        self._current_path = ""

        # Connections
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

        try:
            self._player.errorOccurred.connect(self._on_error)
        except Exception:
            try:
                self._player.error.connect(lambda: self._on_error(self._player.errorString())) # older API
            except Exception:
                pass

        # Defaults
        self.set_volume(80)
        self.set_rate(1.0)

    # Public API
    def play(self, file_path: str):
        """Play a local WAV/MP3/OGG file. Replaces any current playback."""
        if not file_path or not os.path.exists(file_path):
            self.error.emit(f"File not found: {file_path}")
            return
        self._current_path = file_path
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._player.play()

    def stop(self):
        """Stop playback immediately"""
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._player.stop()
            self.stopped.emit()
            self._cleanup_file()

    def set_volume(self, vol: int):
        """Set output volume 0..100."""
        v = max(0, min(100, int(vol)))
        self._audio.setVolume(v / 100.0)

    def set_rate(self, rate: float):
        """Set playback rate (speed). Common 0.5..0.2."""
        try:
            self._player.setPlaybackRate(float(rate))
        except Exception:
            pass

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    
    def current_path(self) -> str:
        return self._current_path
    
    # Slots
    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.started.emit(self._current_path)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            pass

    def _on_media_status_changed(self, status):
        # EndOfMedia
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.finished.emit(self._current_path)
            self._cleanup_file()

    def set_auto_cleanup(self, enabled: bool):
        self._auto_cleanup = bool(enabled)

    def _cleanup_file(self):
        try:
            if getattr(self, "auto_cleanup", True):
                p = getattr(self, "_current_path", "")
                if p and os.path.exists(p):
                    os.remove(p)
        except Exception as e:
            self.error.emit(f"Could not remove temp file: {e}")

    def _on_error(self, *args):
        try:
            msg = self._player.errorString()
        except Exception:
            msg = ""
        if not msg and args:
            msg = " ".join(str(a) for a in args if a)
        if not msg:
            msg = "Unknown audio error"
        self.error.emit(msg)
