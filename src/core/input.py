import re
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

#if __name__ == "__main__":
#    print(DATA)
#    url = "https://www.youtube.com/watch?v=gd7BXuUQ91w"
#    url = "https://www.youtube.com/shorts/v8QsUPOcrrU"
#    download_mp4(url)
#    download_audio(url)
