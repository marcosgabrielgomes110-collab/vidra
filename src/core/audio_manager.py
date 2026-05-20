import os
import subprocess
import wave 
import json 

from src.configs import DATA
from src.configs import MODEL

from vosk import Model, KaldiRecognizer

def get_mp3():
    return next(
        (os.path.join(DATA, f) for f in os.listdir(DATA) if f.endswith(".mp3")),
        None
    )

def mp3_to_wav(mp3_path=None):
    mp3_file = mp3_path or get_mp3()
    if not mp3_file:
        print("nenhum mp3 encontrado")
        return None

    wav_file = mp3_file.replace(".mp3", ".wav")

    subprocess.run([
        "ffmpeg",
        "-i", mp3_file,
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        wav_file
    ])

    return wav_file

def transcribe(wav_file):
    wf = wave.open(wav_file, "rb")

    model = Model(str(MODEL))
    rec = KaldiRecognizer(model, wf.getframerate())

    txt = []

    while True:
        data = wf.readframes(4000)
        if not data:
            break

        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            txt.append(res.get("text", ""))

    final = json.loads(rec.FinalResult())
    txt.append(final.get("text", ""))
    return " ".join(txt)
