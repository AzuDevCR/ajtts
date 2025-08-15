import sys, os
import threading
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QDial, QMenuBar, QMenu, QTextEdit, QProgressDialog,
    QComboBox
)
from PySide6.QtGui import QAction, QPixmap, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QThread

# from model_manager_ui import ModelManagerWindow
from tts_engine import AquaTTS
from tts_engine import repair_text
from tts_engine import ensure_preinstalled_models
from playback import AudioController

def getPath(relPath):
    if getattr(sys, 'frozen', False):
        basePath = sys._MEIPASS
    else:
        basePath = os.path.abspath(".")
    return os.path.join(basePath, relPath)

BUILTIN_MODELS = [
    "tts_models/es/css10/vits",
    "tts_models/en/ljspeech/vits",
]

class MessageManager:
    def __init__(self, text_edit: QTextEdit, idle: str = ""):
        self.view = text_edit
        self.idle = idle
        self.active = ""

    def set_idle(self, msg: str):
        self.idle = msg
        if not self.active:
            self.view.setText(self.idle)

    def show(self, msg: str):
        self.active = msg
        self.view.setText(self.active)

    def clear(self):
        self.active = ""
        self.view.setText(self.idle)

class PreloadWorker(QObject):
    progress = Signal(str)
    finished = Signal(bool)

    def __init__(self, models):
        super().__init__()
        self.models = models

    def run(self):
        def _log(msg):
            self.progress.emit(str(msg))
        try:
            ok = ensure_preinstalled_models(self.models, log=_log)
            self.finished.emit(bool(ok))
        except Exception as e:
            self.progress.emit(f"Preload error: {e}")
            self.finished.emit(False)

class SpeakWorker(QObject):
    progress = Signal(str)
    finished = Signal(bool)
    ready_wav = Signal(str)

    def __init__(self, tts_engine, text):
        super().__init__()
        self.tts_engine = tts_engine
        self.text = text

    def run(self):
        try:
            self.progress.emit("Synthesizing...")
            wav_path = self.tts_engine.synthesize_to_wav(self.text)
            self.ready_wav.emit(wav_path)
            self.finished.emit(True)
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            self.finished.emit(False)

class AquaJupiterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaJupiterTTS")
        self.setFixedSize(770, 385)

        self.speaking = False
        self.last_text = None

        self.audio = AudioController(self)

        # Playback Status
        self.audio.started.connect(lambda p: (setattr(self, "speaking", True), self.msg.show("Speaking...")))
        self.audio.finished.connect(lambda p: (setattr(self, "speaking", False), self.msg.show("Ready.")))
        self.audio.stopped.connect(lambda: (setattr(self, "speaking", False), self.msg.show("Ready.")))
        self.audio.error.connect(lambda m: self.msg.show(f"Audio error: {m}"))

        # --- Menu ---
        # menu_bar = QMenuBar()
        # settings_menu = QMenu("Settings", self)

        # manage_models_action = QAction("Manage Models", self)
        # manage_models_action.triggered.connect(self.open_model_manager)
        # settings_menu.addAction(manage_models_action)

        # menu_bar.addMenu(settings_menu)
        # self.setMenuBar(menu_bar)

        # --- Top bar (Optional, visual divider) ---
        # top_bar = QLabel("AquaJupiterTTS Interface")
        # top_bar.setAlignment(Qt.AlignCenter)
        # top_bar.setStyleSheet("font-size: 18px; color: #8cf; padding: 8px;")
        # main_layout.addWidget(top_bar)

        # --- Central Widget ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # --- Top bar ---
        top_bar = QHBoxLayout()
        self.voice_combo = QComboBox()

        #Model IDs
        self.voice_combo.addItem("Español - Vits", "tts_models/es/css10/vits")
        self.voice_combo.addItem("English - LjSpeech Vits--Neon", "tts_models/en/ljspeech/vits/neon")
        #More voices here Optional
        #self.voice_combo.addItem("English - Jenny", "tts_models/en/jenny/jenny")

        self.speak_btn = QPushButton("Speak (Ctrl+Shift+S)")
        self.speak_btn.clicked.connect(self.speak_from_clipboard)
        self.speak_btn.setEnabled(False)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.audio.stop)

        top_bar.addWidget(self.voice_combo, 1)
        top_bar.addWidget(self.speak_btn, 0)
        top_bar.addWidget(self.btn_stop, 0)

        top_bar_container = QWidget()
        top_bar_container.setLayout(top_bar)
        main_layout.addWidget(top_bar_container)

        # --- Main content area ---
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout, stretch=1)

        # --- Left Panel ---
        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignTop)

        # Pitch Dial
        self.dial_rate = QDial()
        self.dial_rate.setNotchesVisible(True)
        self.dial_rate.setWrapping(False)
        self.dial_rate.setRange(50, 200)
        self.dial_rate.setValue(200)
        rate_label = QLabel("Speed")
        rate_label.setAlignment(Qt.AlignCenter)
        self.dial_rate.valueChanged.connect(lambda v: self.audio.set_rate(v / 100.0))
        left_panel.addWidget(self.dial_rate)
        left_panel.addWidget(rate_label)

        # Repeat Button
        repeat_button = QPushButton("Repeat")
        left_panel.addWidget(repeat_button)
        repeat_button.clicked.connect(self.repeat_last)

        # Volume Dial
        self.dial_volume = QDial()
        self.dial_volume.setNotchesVisible(True)
        self.dial_volume.setWrapping(False)
        self.dial_volume.setRange(0, 100)
        self.dial_volume.setValue(100)
        volume_label = QLabel("Volume")
        volume_label.setAlignment(Qt.AlignCenter)
        self.dial_volume.valueChanged.connect(lambda v: self.audio.set_volume(v))
        left_panel.addWidget(self.dial_volume)
        left_panel.addWidget(volume_label)

        content_layout.addLayout(left_panel)

        # --- Waifu Area ---
        waifu_area = QVBoxLayout()
        self.waifu_label = QLabel()
        self.waifu_label.setPixmap(QPixmap(getPath("config/waifus/NOVA.png")).scaled(200, 250, Qt.KeepAspectRatio))
        self.waifu_label.setAlignment(Qt.AlignCenter)
        waifu_area.addWidget(self.waifu_label)

        # self.waifu_voice_checkbox = QCheckBox("Use Waifu Voice")
        # waifu_area.addWidget(self.waifu_voice_checkbox)

        content_layout.addLayout(waifu_area)

        # --- Bottom info/status bar ---
        bottom_bar = QHBoxLayout()

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("")
        self.status_box.setMaximumHeight(50)
        self.msg = MessageManager(self.status_box, idle="Clip → Speak. Press Ctrl+Shift+S.")
        bottom_bar.addWidget(self.status_box, stretch=3)

        self.preload_thread = QThread(self)
        self.preload_worker = PreloadWorker(BUILTIN_MODELS)
        self.preload_worker.moveToThread(self.preload_thread)

        self.preload_thread.started.connect(self.preload_worker.run)
        self.preload_worker.progress.connect(self.msg.show)
        self.preload_worker.finished.connect(lambda ok: self.msg.show("Voices ready." if ok else "Some voices could not be prepared."))
        self.preload_worker.finished.connect(self._on_preload_finished)

        # Cleaning
        self.preload_worker.finished.connect(self.preload_thread.quit)
        self.preload_worker.finished.connect(self.preload_worker.deleteLater)
        self.preload_thread.finished.connect(self.preload_thread.deleteLater)

        self.msg.show("Preparing built-in voices (first run only)...")
        self.preload_thread.start()

        donate_button = QPushButton("Donate")
        donate_button.setMaximumWidth(100)
        bottom_bar.addWidget(donate_button)

        main_layout.addLayout(bottom_bar)

        self.voice_combo.clear()
        self.voice_combo.addItem("Español — CSS10 (VITS)", "tts_models/es/css10/vits")
        self.voice_combo.addItem("English — LJSpeech (VITS)", "tts_models/en/ljspeech/vits")

        # Default English
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == "tts_models/en/ljspeech/vits":
                self.voice_combo.setCurrentIndex(i)
                break

        # Set the engine and notify
        self.voice_combo.currentIndexChanged.connect(
            lambda idx: self.set_active_model(self.voice_combo.itemData(idx))
        )
        # self.set_active_model(self.voice_combo.currentData())


        #Shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        shortcut.activated.connect(self.speak_from_clipboard)

    # def open_model_manager(self):
    #     '''Open the Model Manager window'''
    #     self.model_window = ModelManagerWindow()
    #     self.model_window.model_downloaded.connect(self.set_active_model)
    #     self.model_window.model_deleted.connect(self.on_model_deleted)
    #     self.model_window.show()

    def _on_preload_finished(self, ok: bool):
        idx = self.voice_combo.findData("tts_models/en/ljspeech/vits")
        if idx != -1:
            self.voice_combo.setCurrentIndex(idx)

        self.set_active_model(self.voice_combo.currentData())

        if hasattr(self, "speak_btn"):
            self.speak_btn.setEnabled(True)

    def speak_async(self, text: str):
        if not text or not self.tts_engine:
            return
        
        # No Overlaps
        if self.speaking:
            self.msg.show("Already speaking...")
            return
        
        # A new thread for every new speech
        thread = QThread(self)
        worker = SpeakWorker(self.tts_engine, text)
        worker.moveToThread(thread)

        # Save refs and flags
        self.speak_thread = thread
        self.speak_worker = worker

        # Signals
        thread.started.connect(worker.run)
        worker.progress.connect(self.msg.show)

        worker.ready_wav.connect(lambda path: self.audio.play(path))

        # Disable btn while speaking
        if hasattr(self, "speak_btn"):
            worker.progress.connect(lambda _=None: self.speak_btn.setEnabled(False))
            worker.finished.connect(lambda _=None: self.speak_btn.setEnabled(True))

        # Cleaning
        
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()

    def set_active_model(self, model_name: str):
        if not model_name:
            return
        try:
            from tts_engine import debug_model_status
            self.msg.show(debug_model_status(model_name))
            self.tts_engine = AquaTTS(model_name)
            info = getattr(self.tts_engine, "loaded_info", model_name)
            self.msg.show(f"Model selected: {info}")
            print(f"[INFO] Active model set to: {info}")
        except Exception as e:
            self.msg.show(f"Error loading model: {e}")
            print(f"[ERROR] {e}")

    def speak_from_clipboard(self):
        if not getattr(self, "tts_engine", None):
            self.msg.show("No model selected.")
            return

        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        
        if mime.hasText():
            raw_text = mime.text()
            fixed_text = repair_text(raw_text)
            self.speak_async(fixed_text)
            self.last_text = fixed_text
        elif self.tts_engine.last_text:
            self.speak_async(self.tts_engine.last_text)
        else:
            print("Clipboard is empty.")

    def repeat_last(self):
        if not getattr(self, "tts_engine", None):
            self.msg.show("No model selected.")
            return
        if self.tts_engine.last_text:
            self.speak_async(self.last_text or "")
        else:
            self.msg.show("No previous text to repeat.")

    def show_processing_dialog(self, message):
        '''Progress bar for processing text'''
        dlg = QProgressDialog(message, None, 0, 0, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setAutoClose(True)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        dlg.show()
        QApplication.processEvents
        self.processing_dialog = dlg

    def close_processing_dialog(self):
        if hasattr(self, "processing_dialog") and self.processing_dialog:
            self.processing_dialog.close()

    def on_model_deleted(self, model_name):
        if self.tts_engine and self.tts_engine.model_name == model_name:
            self.tts_engine = None
            self.status_box.setText("Model deleted. No model selected.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = AquaJupiterGUI()
    gui.show()
    sys.exit(app.exec())
