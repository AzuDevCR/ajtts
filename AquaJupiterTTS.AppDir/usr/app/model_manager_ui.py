from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QComboBox, QDialog, QProgressBar, QLabel
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from model_manager import list_models, model_exists_locally, download_model, delete_model

class DownloadThread(QThread):
    finished = Signal()

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name

    def run(self):
        download_model(self.model_name)
        self.finished.emit()

class ProgressDialog(QDialog):
    def __init__(self, text="Processing..."):
        super().__init__()
        self.setWindowTitle("Please wait")
        self.setModal(True)
        self.setFixedSize(300, 100)

        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        progress = QProgressBar()
        progress.setRange(0, 0)  # Indeterminado
        layout.addWidget(progress)

class ModelManagerWindow(QWidget):
    model_downloaded = Signal(str)
    model_deleted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Model Manager")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout(self)

        # Models list
        self.model_list_combo = QComboBox()
        self.model_list_combo.addItems(list_models())
        self.model_list_combo.currentTextChanged.connect(self.update_buttons)
        self.model_list_combo.activated.connect(self.user_selected_model)
        layout.addWidget(self.model_list_combo)

        # Download button
        self.btn_download = QPushButton("Download")
        self.btn_download.clicked.connect(self.download_selected)
        layout.addWidget(self.btn_download)

        # Delete button
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_selected)
        layout.addWidget(self.btn_delete)

        # Initial state
        self.update_buttons(self.model_list_combo.currentText())

        self.populate_model_list()

    def update_buttons(self, model_name):
        if model_exists_locally(model_name):
            self.btn_download.setEnabled(False)
            self.btn_delete.setEnabled(True)
        else:
            self.btn_download.setEnabled(True)
            self.btn_delete.setEnabled(False)

    def download_selected(self):
        model_name = self.model_list_combo.currentText()

        # Show Progress
        self.progress_dialog = ProgressDialog("Downloading model… Please wait")
        self.progress_dialog.show()

        # Start download thread
        self.download_thread = DownloadThread(model_name)
        self.download_thread.finished.connect(lambda: self.on_download_finished(model_name))
        self.download_thread.start()

    # def on_download_finished(self, model_name):
    #     self.progress_dialog.close()
    #     self.update_buttons(self.model_list_combo.currentText())
    #     self.model_downloaded.emit(model_name)

    #     self.populate_model_list()

    def on_download_finished(self, model_name):
        self.progress_dialog.close()
        self.update_buttons(model_name)
        self.populate_model_list()

        # Emit signal to set this model as active
        self.model_downloaded.emit(model_name)

    def delete_selected(self):
        model_name = self.model_list_combo.currentText()
        delete_model(model_name)
        self.update_buttons(model_name)
        self.populate_model_list()

        self.model_deleted.emit(model_name)
    

    def populate_model_list(self):
        self.model_list_combo.clear()

        combo_model = QStandardItemModel()

        for model in list_models():
            item = QStandardItem(model)
            if model_exists_locally(model):
                item.setForeground(Qt.green)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            combo_model.appendRow(item)

        self.model_list_combo.setModel(combo_model)

    def user_selected_model(self, index):
        model_name = self.model_list_combo.itemText(index)
        if model_exists_locally(model_name):
            self.model_downloaded.emit(model_name)
