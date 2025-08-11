import os
import re
import tempfile
import platform
import shutil
import subprocess
from pathlib import Path
from TTS.api import TTS

os.environ["COQUI_TOS_AGREED"] = "1"

# TEMP_AUDIO_DIR = Path(__file__).parent / ".." / "output" / "tmp"
# TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class AquaTTS:
    def __init__(self, model_name: str):
        if not shutil.which("espeak-ng") and not shutil.which("espeak"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Missing Dependency",
                "This model may require 'espeak-ng' o 'espeak'.\n"
                "Install it with:\n\nsudo apt install espeak-ng espeak"
            )
        try:
            self.model_name = model_name
            self.tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
        except Exception as e:
            if "No espeak backend found" in str(e):
                raise RuntimeError(
                    "This model requires 'espeak-ng' or 'espeak'.\n"
                    "Install it with: sudo apt install espeak-ng espeak"
                )
            else:
                raise e
            
        self.last_text = None

    def speak_text(self, text: str):
        '''Generate audio, speak, delete'''
        if not text or not text.strip():
            print("No text to speak.")
            return
        
        self.last_text = text

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            wav_path = tmp.name

        #Audio generation
        self.tts.tts_to_file(text=text, file_path=wav_path)

        #Play Audio
        self.play_audio(wav_path)

        #Delete audio
        try:
            Path(wav_path).unlink()
        except FileNotFoundError:
            pass

    def repeat_last(self):
        '''Repeat last saved text'''
        if not self.last_text:
            print("No previous text to repeat.")
            return
        self.speak_text(self.last_text)

    def play_audio(self, file_path: str):
        '''Play a wav file using the system audio...'''
        if platform.system() == "Linux":
            subprocess.run(["aplay", file_path])
        elif platform.system() == "Windows":
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
        else:
            subprocess.run(["afplay", file_path]) #mac OS

def repair_text(text: str) -> str:
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"(?<![.!?])\n", " ", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()