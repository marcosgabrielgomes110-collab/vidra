from src.core.input import download_mp4
from src.core.input import download_audio
from src.core.audio_manager import mp3_to_wav
from src.core.audio_manager import transcribe
from src.core.audio_manager import clean_save

def main(url):
    # baixar video e audio do input
    movie = download_mp4(url)

    audio_file = download_audio(url)

    # converter para .wav 
    wav_file = mp3_to_wav(audio_file)

    transcription = transcribe(wav_file, with_timestamps=True)
    print(f'\n📝 {len(transcription)} segmentos transcritos')

    archive = clean_save(transcription)
    print(f'  SRT:  {archive}')
    print(f'  JSON: {archive.replace(".srt", ".json")}')

if __name__ == '__main__':
    url = input("url --> ")
    main(url)
    
