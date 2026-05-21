import shutil
import sys
from pathlib import Path

from src.configs import DATA, LANG_TRANSLATE, ROOT
from src.core.input import download_mp4, download_audio
from src.core.audio_manager import (
    clean_save,
    dub,
    merge_video_audio,
    mp3_to_wav,
    speak,
    translate_segments,
    transcribe,
)
from src.utils.colors import blue, bold, cyan, green, red, yellow


def main(url):
    movie = download_mp4(url)
    audio_file = download_audio(url)

    wav_file = mp3_to_wav(audio_file)

    transcription = transcribe(wav_file, with_timestamps=True)
    print(f'\n{cyan("[transcricao]")} {len(transcription)} segmentos')
    archive = clean_save(transcription)
    print(f'  SRT:  {archive}')
    print(f'  JSON: {archive.replace(".srt", ".json")}')

    translated = translate_segments(transcription)
    lang_path = DATA / f'output_{LANG_TRANSLATE}'
    t_archive = clean_save(translated, lang_path)
    print(f'\n{green("[traducao]")} {LANG_TRANSLATE}:')
    print(f'  SRT:  {t_archive}')
    print(f'  JSON: {t_archive.replace(".srt", ".json")}')

    wav_dir = DATA / 'wav_output'
    wav_dir.mkdir(parents=True, exist_ok=True)
    for i, seg in enumerate(translated, 1):
        wav_path = wav_dir / f'{i}.wav'
        speak(seg['text'], wav_path)
    print(f'\n{yellow("[tts]")} {len(translated)} audios -> {wav_dir}/')

    title = Path(movie).stem
    final_path = DATA / f'{title}_final.mp3'
    dub(audio_file, translated, wav_dir, final_path)
    print(f'\n{blue("[dub]")} audio dublado: {final_path}')

    output_dir = ROOT / 'output'
    final_video = output_dir / f'{title}_final.mp4'
    merge_video_audio(movie, final_path, final_video)
    print(f'\n{bold(green("[merge]"))} video final: {final_video}')

    print(f'\n{red("[cleanup]")} limpando {DATA}...')
    shutil.rmtree(DATA)
    DATA.mkdir(exist_ok=True)
    print(f'  imbox/ limpo')


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else input('URL do YouTube: ')
    main(url)
