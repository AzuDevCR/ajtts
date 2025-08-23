# hook-TTS.py
from PyInstaller.utils.hooks import get_package_paths


pkg_base, pkg_dir = get_package_paths('TTS')


datas = [
    (pkg_dir + '/.models.json', 'TTS'),
]
