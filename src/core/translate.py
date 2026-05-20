from deep_translator import GoogleTranslator
from src.configs import LANG_TRANSLATE

def translate(text):
    translated = GoogleTranslator(
        source="auto",
        target=LANG_TRANSLATE
    ).translate(text)
    return translated 


