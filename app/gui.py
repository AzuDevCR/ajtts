import sys
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QCheckBox, QDial, QMenuBar, QMenu, QTextEdit, QProgressDialog
)
from PySide6.QtGui import QAction, QPixmap, QKeySequence, QShortcut
from PySide6.QtCore import Qt

from model_manager_ui import ModelManagerWindow
from tts_engine import AquaTTS
from tts_engine import repair_text

class AquaJupiterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaJupiterTTS")
        self.setFixedSize(770, 770)

        # --- Menu ---
        menu_bar = QMenuBar()
        settings_menu = QMenu("Settings", self)

        manage_models_action = QAction("Manage Models", self)
        manage_models_action.triggered.connect(self.open_model_manager)
        settings_menu.addAction(manage_models_action)

        menu_bar.addMenu(settings_menu)
        self.setMenuBar(menu_bar)

        # --- Central Widget ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # --- Top bar (Optional, visual divider) ---
        top_bar = QLabel("AquaJupiterTTS Interface")
        top_bar.setAlignment(Qt.AlignCenter)
        top_bar.setStyleSheet("font-size: 18px; color: #8cf; padding: 8px;")
        main_layout.addWidget(top_bar)

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
        self.waifu_label.setPixmap(QPixmap("config/waifus/waifu1.png").scaled(400, 500, Qt.KeepAspectRatio))
        self.waifu_label.setAlignment(Qt.AlignCenter)
        waifu_area.addWidget(self.waifu_label)

        self.waifu_voice_checkbox = QCheckBox("Use Waifu Voice")
        waifu_area.addWidget(self.waifu_voice_checkbox)

        content_layout.addLayout(waifu_area)

        # --- Bottom info/status bar ---
        bottom_bar = QHBoxLayout()

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("")
        self.status_box.setMaximumHeight(50)
        bottom_bar.addWidget(self.status_box, stretch=3)

        donate_button = QPushButton("Donate")
        donate_button.setMaximumWidth(100)
        bottom_bar.addWidget(donate_button)

        main_layout.addLayout(bottom_bar)

        #For testing
        #AquaTTS("tts_models/en/jenny/jenny")
        self.tts_engine = None

        #Shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        shortcut.activated.connect(self.speak_from_clipboard)

    def open_model_manager(self):
        '''Open the Model Manager window'''
        self.model_window = ModelManagerWindow()
        self.model_window.model_downloaded.connect(self.set_active_model)
        self.model_window.model_deleted.connect(self.on_model_deleted)
        self.model_window.show()

    def set_active_model(self, model_name: str):
        '''Activate the downloaded model'''
        from tts_engine import AquaTTS
        self.tts_engine = AquaTTS(model_name)
        self.status_box.setText(f"Model selected: {model_name}")
        print(f"[INFO] Active model set to: {model_name}")

    def speak_from_clipboard(self):
        if not self.tts_engine:
            print("No model selected. Please choose one from Manage Models.")
            self.status_box.setText("No model selected. Please choose one from Manage Models.")

        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        self.status_box.setText("Processing text...")
        if mime.hasText():
            
            raw_text = mime.text()
            fixed_text = repair_text(raw_text)
            
            self.tts_engine.speak_text(fixed_text)
            self.status_box.setText("Speaking...")
            self.status_box.setText("Done.")
        elif self.tts_engine.last_text:
            self.tts_engine.repeat_last()
        else:
            print("No text in clipboard and no last text saved")

    def repeat_last(self):
        if not self.tts_engine:
            self.status_box.setText("No model selected. Please choose one from Manage Models.")
            return
        if self.tts_engine.last_text:
            self.status_box.setText("Processing last saved text...")
            self.tts_engine.repeat_last()
            self.status_box.setText("Speaking...")
            self.status_box.setText("Done.")
        else:
            self.status_box.setText("No previous text to repeat.")

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
