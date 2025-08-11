import os

from TTS.api import TTS
from TTS.utils.manage import ModelManager

def model_list():
    os.environ["COQUI_TOS_AGREED"] = "1"
    # Usamos el administrador de modelos
    model_manager = ModelManager()
    available_models = model_manager.list_models()

    # Podés imprimirlos si querés ver la lista
    print("Modelos disponibles:")
    for model in available_models:
        print("-", model)

model_list()