import os
import yt_dlp 

from src.configs import DATA

def download_mp4(url):
    opts = {
        'format': 'bestvideo[ext=mp4]',
        'merge_output_format': 'mp4',
        'outtmpl': str(DATA / '%(title)s.%(ext)s'),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_audio(url):
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(DATA / '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def get_input(url):
    movie = download_mp4(url)
    aud = download_audio(url)
    print(f"download sucessfull\nmovie -> {movie}\naudio -> {aud}")
    
#if __name__ == "__main__":
#    print(DATA)
#    url = "https://www.youtube.com/watch?v=gd7BXuUQ91w"
#    url = "https://www.youtube.com/shorts/v8QsUPOcrrU"
#    download_mp4(url)
#    download_audio(url)
