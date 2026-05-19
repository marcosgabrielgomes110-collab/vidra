from pathlib import Path

__root__ = Path(__file__).parent.parent
DATA = __root__ / "imbox"

DATA.mkdir(exist_ok=True)
