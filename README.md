🌊 AquaJupiterTTS

AquaJupiterTTS is a free-forever text-to-speech desktop application built with PySide6
 and Coqui TTS
.
It focuses on a clean GUI, instant playback, and a philosophy of Free Forever, supported by the community.

✨ Features

📋 Clipboard capture → copy any text and hear it instantly.

🔁 Repeat last spoken text even after the clipboard changes.

🌐 Multilingual → English and Spanish voices included by default.

⚡ Stable number handling (fixed in v1.0.1) → no more crashes when reading years, versions, or symbols.

❤️ Free Forever → no paywalls, just an optional Ko-fi support link
.

📦 Requirements (for source code build)

Before running from source, make sure you have these installed:

sudo apt update
sudo apt install python3 python3-pip espeak-ng


Then install dependencies:

pip install -r requirements.txt

🚀 Running

From source:

python3 app/gui.py


Or download the latest AppImage release from:
👉 Itch.io page

👉 Archive.org mirror

⚠️ Notes

Temporary audio files are generated in output/tmp/ and deleted after playback.

Some TTS models require espeak-ng to function properly.

Windows builds are planned for upcoming releases.

📜 License

This project uses free and open-source components:

Coqui TTS (MPL 2.0)

PySide6 (LGPL)

GPLv3
