from src.core.audio_manager import speak
from src.core.translate import translate

text = 'hello world, its me marcos gomes test two nine'

traducao = translate(text)
print(traducao)

out = speak(traducao, 'imbox/wav_output/teste')
print(f'áudio salvo em: {out}')
