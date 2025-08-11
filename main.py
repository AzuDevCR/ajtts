import os

from TTS.api import TTS
from TTS.utils.manage import ModelManager

def tts_test():
    os.environ["COQUI_TOS_AGREED"] = "1"
    # Usamos el administrador de modelos
    model_manager = ModelManager()
    available_models = model_manager.list_models()

    # Podés imprimirlos si querés ver la lista
    print("Modelos disponibles:")
    for model in available_models:
        print("-", model)

    # Elegimos uno (por ahora el primero)
    model_name = "tts_models/es/mai/tacotron2-DDC"

    tts = TTS(model_name)
    tts.tts_to_file(text="Esta es una nueva prueba para ver qué está sucediendo", file_path="/output/toSay.wav")

    print("¡Audio generado con Coqui TTS!")

if __name__ == "__main__":
    tts_test()