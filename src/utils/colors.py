import sys

_ON = sys.stdout.isatty()

def _wrap(code: str, text: str) -> str:
    return f'\033[{code}m{text}\033[0m' if _ON else str(text)

green   = lambda t: _wrap('32', t)
yellow  = lambda t: _wrap('33', t)
blue    = lambda t: _wrap('34', t)
cyan    = lambda t: _wrap('36', t)
red     = lambda t: _wrap('31', t)
bold    = lambda t: _wrap('1', t)
