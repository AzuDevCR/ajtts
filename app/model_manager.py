import os
import shutil
from pathlib import Path
from TTS.utils.manage import ModelManager

os.environ["COQUI_TOS_AGREED"] = "1"
model_manager = ModelManager()

BASE_DIR = Path.home() / ".local/share/tts"

def list_models():
    """Lista solo modelos en inglés y español."""
    all_models = model_manager.list_models()
    filtered = [m for m in all_models if m.startswith("tts_models/en") or m.startswith("tts_models/es") or m.startswith("tts_models/multilingual")]
    return filtered

def normalize_model_name(model_name: str) -> str:
    return model_name.replace("/", "--")

def find_model_path(model_name: str) -> Path | None:
    if not BASE_DIR.exists():
        return None

    normalized_name = normalize_model_name(model_name).lower()

    for folder in BASE_DIR.iterdir():
        if folder.name.lower() == normalized_name:
            return folder
    return None

def model_exists_locally(model_name: str) -> bool:
    return find_model_path(model_name) is not None

def download_model(model_name: str):
    if not model_exists_locally(model_name):
        print(f"Descargando modelo: {model_name}")
        model_manager.download_model(model_name)
    else:
        print(f"El modelo '{model_name}' ya está instalado.")

def delete_model(model_name: str):
    path = find_model_path(model_name)
    if path and path.exists():
        print(f"Eliminando modelo: {path}")
        shutil.rmtree(path)
    else:
        print(f"El modelo '{model_name}' no está instalado.")
