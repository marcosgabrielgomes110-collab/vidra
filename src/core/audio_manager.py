import os
import subprocess
from src.configs import DATA

def get_mp3():
    return next(os.path.join(DATA, f) for f in os.listdir(DATA) if f.endswith(".mp3"))

def mp3_to_wav():
    mp3_file = get_mp3()

    if not mp3_file:
        print("nenhum mp3 encontrado")
        return None

    wav_file = mp3_file.replace(".mp3", ".wav")

    subprocess.run([
        "ffmpeg",
        "-i", mp3_file,
        wav_file
    ])

    return wav_file


