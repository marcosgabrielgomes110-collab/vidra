import argparse
import shutil
import sys
from pathlib import Path

# Redireciona __pycache__ para um diretório global (antes dos imports do projeto)
_CACHE = Path(__file__).resolve().parent / '.pycache'
_CACHE.mkdir(exist_ok=True)
sys.pycache_prefix = str(_CACHE)

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
from src.utils.logger import setup_logging

log = setup_logging()


def main(url):
    log.info(f'\n{cyan("[vidra]")} iniciando pipeline para: {url}')

    log.info(f'{cyan("[download]")} baixando video e audio...')
    movie = download_mp4(url)
    audio_file = download_audio(url)

    wav_file = mp3_to_wav(audio_file)

    log.info(f'{cyan("[transcricao]")} transcrevendo...')
    transcription = transcribe(wav_file, with_timestamps=True)
    log.info(f'  {len(transcription)} segmentos')
    archive = clean_save(transcription)
    log.info(f'  SRT:  {archive}')
    log.info(f'  JSON: {archive.replace(".srt", ".json")}')

    translated = translate_segments(transcription)
    lang_path = DATA / f'output_{LANG_TRANSLATE}'
    t_archive = clean_save(translated, lang_path)
    log.info(f'{green("[traducao]")} {LANG_TRANSLATE}:')
    log.info(f'  SRT:  {t_archive}')
    log.info(f'  JSON: {t_archive.replace(".srt", ".json")}')

    wav_dir = DATA / 'wav_output'
    wav_dir.mkdir(parents=True, exist_ok=True)
    log.info(f'{yellow("[tts]")} gerando {len(translated)} audios...')
    for i, seg in enumerate(translated, 1):
        wav_path = wav_dir / f'{i}.wav'
        speak(seg['text'], wav_path)
    log.info(f'  {len(translated)} audios -> {wav_dir}/')

    title = Path(movie).stem
    final_path = DATA / f'{title}_final.mp3'
    dub(audio_file, translated, wav_dir, final_path)
    log.info(f'{blue("[dub]")} audio dublado: {final_path}')

    output_dir = ROOT / 'output'
    final_video = output_dir / f'{title}_final.mp4'
    merge_video_audio(movie, final_path, final_video)
    log.info(f'{bold(green("[merge]"))} video final: {final_video}')

    log.info(f'{red("[cleanup]")} limpando {DATA}...')
    shutil.rmtree(DATA)
    DATA.mkdir(exist_ok=True)
    log.info('  imbox/ limpo')
    log.info(f'{bold(green("[vidra]"))} concluido!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='vidra — tradutor de vídeos')
    parser.add_argument('-u', '--url', help='URL do YouTube')
    parser.add_argument('-v', '--verbose', action='store_true', help='Log detalhado')
    args = parser.parse_args()

    if args.verbose:
        log = setup_logging(verbose=True)

    url = args.url or input('URL do YouTube: ')
    main(url)
