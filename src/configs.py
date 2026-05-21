from pathlib import Path

__root__ = Path(__file__).parent.parent
DATA = __root__ / "imbox"

DATA.mkdir(exist_ok=True)

MODEL = __root__ / "models" / "vosk-model-small-en-us-0.15"

LANG_TRANSLATE = "pt"

MODEL_TTS = __root__ / "models" / "tts" / "pt_BR-faber-medium.onnx"
