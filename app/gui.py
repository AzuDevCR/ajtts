import sys, os
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QDial, QMenuBar, QMenu, QTextEdit, QProgressDialog,
    QComboBox
)
from PySide6.QtGui import QAction, QPixmap, QKeySequence, QShortcut
from PySide6.QtCore import Qt

# from model_manager_ui import ModelManagerWindow
from tts_engine import AquaTTS
from tts_engine import repair_text
from tts_engine import ensure_preinstalled_models

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

class AquaJupiterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaJupiterTTS")
        self.setFixedSize(770, 385)

        # --- Menu ---
        # menu_bar = QMenuBar()
        # settings_menu = QMenu("Settings", self)

        # manage_models_action = QAction("Manage Models", self)
        # manage_models_action.triggered.connect(self.open_model_manager)
        # settings_menu.addAction(manage_models_action)

        # menu_bar.addMenu(settings_menu)
        # self.setMenuBar(menu_bar)

        # --- Central Widget ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # --- Top bar (Optional, visual divider) ---
        # top_bar = QLabel("AquaJupiterTTS Interface")
        # top_bar.setAlignment(Qt.AlignCenter)
        # top_bar.setStyleSheet("font-size: 18px; color: #8cf; padding: 8px;")
        # main_layout.addWidget(top_bar)

        # --- Top bar ---
        top_bar = QHBoxLayout()
        self.voice_combo = QComboBox()

        #Model IDs
        self.voice_combo.addItem("Español - Vits", "tts_models/es/css10/vits")
        self.voice_combo.addItem("English - LjSpeech Vits--Neon", "tts_models/en/ljspeech/vits/neon")
        #More voices here Optional
        #self.voice_combo.addItem("English - Jenny", "tts_models/en/jenny/jenny")

        self.voice_combo.currentIndexChanged.connect(
            lambda idx: self.set_active_model(self.voice_combo.itemData(idx))
        )

        btn_speak = QPushButton("Speak (Ctrl+Shift+S)")
        btn_speak.clicked.connect(self.speak_from_clipboard)

        top_bar.addWidget(self.voice_combo, 1)
        top_bar.addWidget(btn_speak, 0)

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
        pitch_dial = QDial()
        pitch_dial.setNotchesVisible(True)
        pitch_label = QLabel("P")
        pitch_label.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(pitch_dial)
        left_panel.addWidget(pitch_label)

        # Repeat Button
        repeat_button = QPushButton("R")
        left_panel.addWidget(repeat_button)
        repeat_button.clicked.connect(self.repeat_last)

        # Volume Dial
        volume_dial = QDial()
        volume_dial.setNotchesVisible(True)
        volume_label = QLabel("V")
        volume_label.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(volume_dial)
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

        donate_button = QPushButton("Donate")
        donate_button.setMaximumWidth(100)
        bottom_bar.addWidget(donate_button)

        main_layout.addLayout(bottom_bar)

        try:
            if hasattr(self, "msg"):
                self.msg.show("Preparing built-in voices (first run only)...")
                logger = self.msg.show
            else:
                logger = print

            ok = ensure_preinstalled_models(BUILTIN_MODELS, log=logger)
            if not ok:
                logger("Some voices could not be prepared. Check internet / disk space.")
            else:
                logger("Voices ready.")

        except Exception as e:
            if hasattr(self, "msg"):
                self.msg.show(f"Error preparing voices: {e}")
            else:
                print(f"[ERROR] {e}")

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
        self.set_active_model(self.voice_combo.currentData())

        #For testing
        #AquaTTS("tts_models/en/jenny/jenny")

        # self.tts_engine = None

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

    def set_active_model(self, model_name: str):
        try:
            self.tts_engine = AquaTTS(model_name)
            info = getattr(self.tts_engine, "loaded_info", model_name)
            if hasattr(self, "msg"):
                self.msg.show(f"Model selected: {info}")
            else:
                self.status_box.setText(f"Model selected: {info}")
            print(f"[INFO] Active model set to: {info}")
        except Exception as e:
            if hasattr(self, "msg"):
                self.msg.show(f"Error loading model: {e}")
            else:
                self.status_box.setText(f"Error loading model: {e}")
            print(f"[ERROR] {e}")

    def speak_from_clipboard(self):
        if not self.tts_engine:
            print("No model selected. Please choose one from Manage Models.")
            self.msg.show("No model selected.")
            return

        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        self.msg.show("Processing text...")
        if mime.hasText():
            
            raw_text = mime.text()
            fixed_text = repair_text(raw_text)
            
            self.tts_engine.speak_text(fixed_text)
            self.msg.show("Speaking...")
            self.msg.show("Done.")
        elif self.tts_engine.last_text:
            self.tts_engine.repeat_last()
        else:
            print("No text in clipboard and no last text saved")

    def repeat_last(self):
        if not self.tts_engine:
            self.msg.show("No model selected. Please choose one from Manage Models.")
            return
        if self.tts_engine.last_text:
            self.msg.show("Processing last saved text...")
            self.tts_engine.repeat_last()
            self.msg.show("Speaking...")
            self.msg.show("Done.")
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
