# hook-TTS.py
from PyInstaller.utils.hooks import get_package_paths

# Ubicar el directorio real del paquete TTS en el venv
pkg_base, pkg_dir = get_package_paths('TTS')

# Incluir explícitamente el dotfile que falta dentro del paquete TTS
# El segundo valor 'TTS' asegura que vaya a .../_internal/TTS/.models.json
datas = [
    (pkg_dir + '/.models.json', 'TTS'),
]
