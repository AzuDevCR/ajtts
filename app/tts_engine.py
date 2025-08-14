import os
import re
import tempfile
import platform
import shutil
import subprocess

import torch, collections
try:
    from TTS.utils.radam import RAdam
    torch.serialization.add_safe_globals([RAdam])
except Exception:
    pass

try:
    torch.serialization.add_safe_globals([collections.defaultdict])
except Exception:
    pass

from pathlib import Path
from TTS.api import TTS
from TTS.utils.manage import ModelManager

os.environ["COQUI_TOS_AGREED"] = "1"

from glob import glob

ASSETS_MODELS_DIR = Path(__file__).resolve().parent / "assets" / "models"
CACHE_DIR = Path.home() / ".local" / "share" / "tts"
model_manager = ModelManager()

def _norm(model_id: str) -> str:
    return model_id.replace("/", "--")

def _asset_dir(model_id: str) -> Path:
    return (Path(__file__).resolve().parent / "assets" / "models" / _norm(model_id))

def _cache_dir(model_id: str) -> Path:
    return (CACHE_DIR / _norm(model_id))

def _has_weights(folder: Path) -> bool:
    if not folder.exists():
        return False
    
    has_cfg = (folder / "config.json").exists()
    has_w = any(folder.glob("*.pth")) or any(folder.glob("*.pt")) or any(folder.glob("*.onnx"))
    return has_cfg and has_w

def _copy_model_tree(src: Path, dst: Path):
    # dst.mkdir(parents=True, exist_ok=True)
    # #Config
    # cfg = src / "config.json"
    # if cfg.exists():
    #     shutil.copy2(cfg, dst / "config.json")
    # #Weights
    # for pat in ("*.pth", "*.pt", "*.onnx"):
    #     for f in src.glob(pat):
    #         shutil.copy2(f, dst / f.name)

    dst.mkdir(parents=True, exist_ok=True)
    # config
    for name in ("config.json", "scale_stats.npy"):
        f = src / name
        if f.exists():
            shutil.copy2(f, dst / f.name)
    # pesos y extras comunes
    for pat in ("*.pth", "*.pt", "*.onnx", "vocoder*.pth", "*.json", "*.txt"):
        for f in src.glob(pat):
            if f.name == "config.json":  # ya copiada
                continue
            shutil.copy2(f, dst / f.name)

def ensure_model_local(model_id: str, log=None):
    log = log or (lambda *_: None)
    cdir = _cache_dir(model_id)
    if _has_weights(cdir):
        log(f"Cached: {model_id}")
        return True
    log(f"Downloading: {model_id}")
    os.environ["COQUI_TOS_AGREED"] = "1"
    model_manager.download_model(model_id)
    return _has_weights(cdir)

def ensure_preinstalled_models(models: list[str], log=None):
    ok_all = True
    for m in models:
        ok = ensure_model_local(m, log=log)
        ok_all = ok_all and ok
    return ok_all

def _normalize_name(model_id: str) -> str:
    return model_id.replace("/", "--")

def resolve_model(id_or_path: str):
    p = Path(id_or_path)
    if p.exists():
        return _find_paths_in(p)
    
    # 1- assets
    folder =  ASSETS_MODELS_DIR / _normalize_name(id_or_path)
    if folder.exists():
        return _find_paths_in(folder)
    
    # 2- cache (~/.local/share/tts/...)
    cfolder = CACHE_DIR / _normalize_name(id_or_path)
    if cfolder.exists():
        return _find_paths_in(cfolder)
    
    return (None, None)

def _find_paths_in(folder: Path):
    model_path = None
    for pat in ("*.pth","*.pt","*.onnx"):
        hits = list(folder.glob(pat))
        if hits:
            model_path = hits[0]
            break
    config_path = folder / "config.json" if (folder / "config.json").exists() else None
    return (model_path, config_path)

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

        self.model_name = model_name
        self.last_text = None

        model_path, config_path = resolve_model(model_name)

        try:
            if model_path and config_path:
                self.tts = TTS(
                    model_path=str(model_path),
                    config_path=str(config_path),
                    progress_bar=False,
                    gpu=False
                )
                src_root = Path(model_path).parent
                self.source = "cache" if str(src_root).startswith(str(CACHE_DIR)) else "local"
            else:
                self.tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
                self.source = "remote"
        except Exception as e:
            if "No espeak backend found" in str(e):
                raise RuntimeError(
                    "This model requires 'espeak-ng' or 'espeak'.\n"
                    "Install it with: sudo apt install espeak-ng espeak"
                )
            else:
                raise

        self.loaded_info = f"{self.model_name} [{self.source}]"

        try:
            if not hasattr(self.tts, "is_multi_lingual"):
                self.tts.__class__.is_multi_lingual = property(lambda _self: False)
            if not hasattr(self.tts, "speakers"):
                self.tts.__class__.speakers = property(lambda _self: None)
        except Exception:
            pass

        

        self.loaded_info = f"{self.model_name} [{self.source}]"

    def synthesize_to_wav(self, text: str) -> str:
        """Returns a temporal WAV(path) with the speech do not talk"""
        if not text:
            raise ValueError("Empty text")
        self.last_text = text

        tmp = tempfile.NamedTemporaryFile(prefix="ajtts_", suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        try:
            self.tts.tts_to_file(text=text, file_path=str(tmp_path))
        except AttributeError:
            raise RuntimeError("This TTS backend lacks tts_to_file(...)")
        return str(tmp_path)

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

def debug_model_status(model_id: str) -> str:
    folder = ASSETS_MODELS_DIR / _normalize_name(model_id)
    parts = [f"[check] {model_id}",
             f"assets_dir: {folder}",
             f"exists: {folder.exists()}"]
    
    if folder.exists():
        hits_w = []
        for pat in ("*.pth", "*.pt", "*.onnx"):
            hits_w += [p.name for p in folder.glob(pat)]
        parts.append(f"weights: {hits_w or '—'}")
        parts.append(f"has_config: {(folder / 'config.json').exists()}")
    cdir = _cache_dir(model_id)
    parts.append(f"cache_dir: {cdir} (exists: {cdir.exists()})")
    return "\n".join(parts)
