from pathlib import Path

from src.configs import DATA, LANG_TRANSLATE
from src.core.input import download_mp4, download_audio
from src.core.audio_manager import (
    clean_save,
    dub,
    mp3_to_wav,
    speak,
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

    wav_dir = DATA / 'wav_output'
    wav_dir.mkdir(parents=True, exist_ok=True)
    for i, seg in enumerate(translated, 1):
        wav_path = wav_dir / f'{i}.wav'
        speak(seg['text'], wav_path)
    print(f'\n🔊 {len(translated)} áudios gerados em: {wav_dir}/')

    title = Path(movie).stem
    final_path = DATA / f'{title}_final.mp3'
    dub(audio_file, translated, wav_dir, final_path)
    print(f'\n🎬 Áudio dublado salvo em: {final_path}')

if __name__ == '__main__':
    url = input("url --> ")
    main(url)
    
