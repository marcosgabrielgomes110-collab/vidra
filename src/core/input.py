import re
import shutil
import subprocess
from pathlib import Path

import yt_dlp

from src.configs import DATA

_SANITIZE = re.compile(r'[^\w\- ]+')

def _title(url):
    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
        return ydl.extract_info(url, download=False)['title']

def _safe_name(title):
    return _SANITIZE.sub('', title).strip()

def download_mp4(url):
    title = _safe_name(_title(url))
    path = DATA / f'{title}.mp4'
    if not path.exists():
        yt_dlp.YoutubeDL({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(path),
            'merge_output_format': 'mp4',
            'quiet': True, 'no_warnings': True,
        }).download([url])
    return str(path)

def download_audio(url):
    title = _safe_name(_title(url))
    path = DATA / f'{title}.mp3'
    if not path.exists():
        yt_dlp.YoutubeDL({
            'format': 'bestaudio/best',
            'outtmpl': str(DATA / f'{title}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True, 'no_warnings': True,
        }).download([url])
    return str(path)


# ── importação de vídeo local ─────────────────────────────

def import_local_video(video_path: str) -> tuple[str, str]:
    """Copia um vídeo local para a área de trabalho e extrai o áudio MP3.

    Returns:
        (caminho_do_mp4, caminho_do_mp3)
    """
    src = Path(video_path)
    if not src.exists():
        raise FileNotFoundError(f'Arquivo não encontrado: {video_path}')

    DATA.mkdir(parents=True, exist_ok=True)

    # Copia o vídeo para .vidra/tmp/ com nome sanitizado
    stem = _safe_name(src.stem) or 'video'
    movie = DATA / f'{stem}.mp4'
    shutil.copy2(str(src), str(movie))

    # Extrai o áudio MP3
    audio = DATA / f'{stem}.mp3'
    subprocess.run([
        'ffmpeg', '-y', '-i', str(movie),
        '-vn', '-acodec', 'libmp3lame', '-ab', '192k',
        str(audio),
    ], check=True, capture_output=True)

    return str(movie), str(audio)
