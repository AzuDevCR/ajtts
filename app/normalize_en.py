# AquaJupiterTTS
# Copyright (C) 2025  AzuDevCR (INL Creations)
# Licensed under GPLv3 (see LICENSE file for details).

import re

def normalize_text_en(text: str) -> str:
    text = re.sub(r'(?<=\w)\.(?=\w)', " dot ", text)

    text = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', text)

    text = re.sub(r'(\d+)\+', r'\1 plus', text)

    text = re.sub(r'\d{10,}', "[this incredible huge number]", text)

    return re.sub(r'\s+', ' ', text).strip()
