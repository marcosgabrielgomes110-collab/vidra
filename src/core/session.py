"""Sistema de checkpoint/resume para pipeline do VIDRA.

Cada sessão é identificada pelo hash MD5 da URL.
O progresso é salvo em .vidra/checkpoints/<session_id>.json
"""

import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger('vidra')

_STEPS = [
    'download',
    'convert',
    'transcribe',
    'translate',
    'tts',
    'dub',
    'merge',
]


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


class Session:
    """Gerencia checkpoint de uma pipeline.

    Uso:
        session = Session(checkpoint_dir, url, source='en', target='pt')
        if not session.is_complete('download'):
            video = download(url)
            session.mark('download', {'movie': video, 'audio': audio})

        # No resume:
        session = Session.load(checkpoint_dir, url)
        paths = session.get('download')  # → {'movie': ..., 'audio': ...}
    """

    def __init__(self, checkpoint_dir: Path, url: str,
                 source: str = 'en', target: str = 'pt',
                 input_type: str = 'url'):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.url = url
        self.input_type = input_type  # 'url' | 'file'
        self._session_id = _url_hash(url)
        self.source = source
        self.target = target
        self.completed: set[str] = set()
        self.paths: dict[str, any] = {}
        self.created_at = datetime.now().isoformat()
        self._dirty = False

    # ── propriedades ──────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def checkpoint_path(self) -> Path:
        return self.checkpoint_dir / f'{self._session_id}.json'

    # ── persistência ──────────────────────────────────────

    def save(self):
        data = {
            'url':         self.url,
            'session_id':  self._session_id,
            'input_type':  self.input_type,
            'source':      self.source,
            'target':      self.target,
            'completed':   sorted(self.completed),
            'paths':       self.paths,
            'created_at':  self.created_at,
            'updated_at':  datetime.now().isoformat(),
        }
        self.checkpoint_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        self._dirty = False

    @classmethod
    def load(cls, checkpoint_dir: Path, url_or_id: str):
        """Carrega sessão por URL ou session_id. Retorna None se não existir."""
        cdir = Path(checkpoint_dir)
        if not cdir.is_dir():
            return None

        # Tenta como session_id direto
        path = cdir / f'{url_or_id}.json'
        if not path.exists():
            # Tenta como URL → hash
            sid = _url_hash(url_or_id)
            path = cdir / f'{sid}.json'

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning('Checkpoint corrompido: %s', exc)
            return None

        ses = cls(cdir, data.get('url', url_or_id),
                   input_type=data.get('input_type', 'url'))
        ses._session_id = data.get('session_id', sid)
        ses.source = data.get('source', 'en')
        ses.target = data.get('target', 'pt')
        ses.completed = set(data.get('completed', []))
        ses.paths = data.get('paths', {})
        ses.created_at = data.get('created_at', ses.created_at)
        return ses

    # ── API de checkpoint ─────────────────────────────────

    def is_complete(self, step: str) -> bool:
        """True se o step já foi completado."""
        return step in self.completed

    def mark(self, step: str, paths: dict | str | None = None):
        """Marca step como completo e opcionalmente armazena paths.

        paths pode ser:
          - dict: {'movie': '...', 'audio': '...'}
          - str:  '/path/to/file'  →  armazenado como {step: path}
          - None: só marca completo
        """
        self.completed.add(step)
        if isinstance(paths, dict):
            self.paths[step] = paths
        elif isinstance(paths, str):
            self.paths[step] = paths
        self.save()
        log.info('  ✔ checkpoint [%s] salvo', step)

    def get(self, step: str, default=None):
        """Retorna paths armazenados para o step."""
        return self.paths.get(step, default)

    def remaining(self) -> list[str]:
        """Steps ainda não executados na ordem da pipeline."""
        return [s for s in _STEPS if s not in self.completed]

    def progress_str(self) -> str:
        total = len(_STEPS)
        done = len(self.completed)
        return f'{done}/{total} steps'

    def __repr__(self):
        return (f'<Session {self._session_id} '
                f'{self.progress_str()} '
                f'{self.source}→{self.target}>')
