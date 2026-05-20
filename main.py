from src.configs import DATA, LANG_TRANSLATE
from src.core.input import download_mp4, download_audio
from src.core.audio_manager import (
    clean_save,
    mp3_to_wav,
    translate_segments,
    transcribe,
)

def main(url):
    movie = download_mp4(url)
    audio_file = download_audio(url)

    wav_file = mp3_to_wav(audio_file)

    transcription = transcribe(wav_file, with_timestamps=True)
    print(f'\n📝 {len(transcription)} segmentos transcritos')

    archive = clean_save(transcription)
    print(f'  SRT:  {archive}')
    print(f'  JSON: {archive.replace(".srt", ".json")}')

    translated = translate_segments(transcription)
    lang_path = DATA / f'output_{LANG_TRANSLATE}'
    t_archive = clean_save(translated, lang_path)
    print(f'\n🌐 Traduzido para "{LANG_TRANSLATE}":')
    print(f'  SRT:  {t_archive}')
    print(f'  JSON: {t_archive.replace(".srt", ".json")}')

if __name__ == '__main__':
    url = input("url --> ")
    main(url)
    
