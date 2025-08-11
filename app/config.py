import os
import json

CONFIG_PATH = os.path.join("user_data", "config.json")
DEFAULT_CONFIG = {
    "language": "es",
    "use_waifu_voice": True,
    "selected_waifu": "Lucia",
    "waifu_language": "es",
    "voice_model": "tts_models/es/mai/tacotron2-DDC",
    "hotkey": "ctrl+alt+h",
}

def load_config():
    if not os.path.exist(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)