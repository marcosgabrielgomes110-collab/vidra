from src.core.input import get_input

def main(url):
    # baixar audios do input url
    get_input(url)
    print("[ ok ]")

if __name__ == '__main__':
    url = input("url --> ")
    main(url)
