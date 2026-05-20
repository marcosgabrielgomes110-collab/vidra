from src.core.input import download_mp4
from src.core.input import download_audio
from src.core.audio_manager import mp3_to_wav
from src.core.audio_manager import transcribe

def main(url):
    # baixar video e audio do input
    movie = download_mp4(url)

    audio_file = download_audio(url)

    # converter para .wav 
    wav_file = mp3_to_wav(audio_file)

    transcription = transcribe(wav_file)
    print(f'\n📝 Transcrição:\n{transcription}')

if __name__ == '__main__':
    url = input("url --> ")
    main(url)
    
