from src.core.input import get_input
from src.core.audio_manager import mp3_to_wav

def main(url):
    # baixar audios do input url
    get_input(url)
    print("[ ok ]")

if __name__ == '__main__':
    #url = input("url --> ")
    #main(url)
    teste = mp3_to_wav()
    print(teste)
