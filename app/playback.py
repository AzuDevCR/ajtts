# AquaJupiterTTS
# Copyright (C) 2025  AzuDevCR (INL Creations)
# Licensed under GPLv3 (see LICENSE file for details).

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
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
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.playbackStateChanged.connect(self._on_state_changed)

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
        if not os.path.exists(file_path):
            self.error.emit(f"File not found: {file_path}")
            return
        self._release_media()
        self._current_path = file_path
        self._emitted_start = False
        self._emitted_end   = False
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._player.play()

    def stop(self):
        """Stop playback immediately (user action)"""
        self._stopped_by_user = True
        self._emitted_end = True

        if self._player.playbackState() != QMediaPlayer.StoppedState:
            self._player.stop()
        self._release_media()
        self.stopped.emit()
        self._schedule_cleanup()

    def _on_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlayingState and not self._emitted_start:
            self._emitted_start = True
            self.started.emit(self._current_path)
        if state == QMediaPlayer.StoppedState:
            self._maybe_finish()

    def _on_media_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            self._maybe_finish()

    def _maybe_finish(self):
        if self._stopped_by_user:
            return
        if not self._emitted_end and self._current_path:
            self._emitted_end = True
            self.finished.emit(self._current_path)
            self._schedule_cleanup()

    def _release_media(self):
        try:
            if self._player.playbackState() != QMediaPlayer.StoppedState:
                self._player.stop()
        except Exception:
            pass

        self._player.setSource(QUrl())

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

    def _on_media_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            self.finished.emit(self._current_path)
            
            self._schedule_cleanup()

    def _schedule_cleanup(self):
        if not getattr(self, "_auto_cleanup", True):
            return
        path = self._current_path
        if not path:
            return
        
        def attempt(retries=6, delay_ms=100):
            if not os.path.exists(path):
                return
            try:
                os.remove(path)
                if self._current_path == path:
                    self._current_path = ""
            except FileNotFoundError:
                return
            except PermissionError as e:
                if retries > 0:
                    QTimer.singleShot(delay_ms, lambda: attempt(retries - 1, min(delay_ms * 2, 1000)))
                else:
                    self.error.emit(f"Could not remove temp file after retries: {e}")
            except Exception as e:
                self.error.emit(f"Could not remove temp file: {e}")
        self._release_media()
        QTimer.singleShot(120, attempt)

    def _on_media_status_changed(self, status):
        # EndOfMedia
        pass

    def set_auto_cleanup(self, enabled: bool):
        self._auto_cleanup = bool(enabled)

    def _cleanup_file(self):
        try:
            if getattr(self, "_auto_cleanup", True):
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
