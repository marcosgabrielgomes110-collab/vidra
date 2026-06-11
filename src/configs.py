"""Configuração do VIDRA — lê de vidra.json com fallback para defaults."""

import json
import logging
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# ── busca do config file ───────────────────────────────────
_CONFIG_SEARCH = [
    _ROOT / 'vidra.json',
    Path.home() / '.config' / 'vidra' / 'vidra.json',
]

_DEFAULTS = {
    'language': {'source': 'en', 'target': 'pt'},
    'models': {
        'vosk': {'en': 'models/vosk-model-small-en-us-0.15', 'pt': 'models/vosk-model-small-pt-0.3'},
        'tts': {'pt': 'models/tts/pt_BR-faber-medium.onnx'},
    },
    'translate': {'preferred': 'google'},
    'tts': {'parallel_workers': 4, 'sample_rate': 22050},
    'checkpoint': {'enabled': True},
}


def _deep_merge(base, override):
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_config():
    cfg = _DEFAULTS.copy()
    for path in _CONFIG_SEARCH:
        if path.exists():
            with open(path) as f:
                user = json.load(f)
            cfg = _deep_merge(cfg, user)
            break
    return cfg


_cfg = _load_config()

# ── constantes de diretório ────────────────────────────────
ROOT = _ROOT
DATA = _ROOT / '.vidra' / 'tmp'
OUTPUT = _ROOT / 'output'
CHECKPOINT_DIR = _ROOT / '.vidra' / 'checkpoints'
for d in (DATA, OUTPUT, CHECKPOINT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── constantes de runtime ──────────────────────────────────
TTS_WORKERS = _cfg['tts']['parallel_workers']
TTS_SAMPLE_RATE = _cfg['tts']['sample_rate']
CHECKPOINT_ENABLED = _cfg['checkpoint']['enabled']
TRANSLATE_PREFERRED = _cfg['translate'].get('preferred', 'google')

# ── idioma padrão vindo do config ─────────────────────────
DEFAULT_SOURCE_LANG = _cfg.get('language', {}).get('source', 'en')
DEFAULT_TARGET_LANG = _cfg.get('language', {}).get('target', 'pt')

# ── lookup de modelos por idioma ───────────────────────────
VOSK_MODELS = {k: _ROOT / v for k, v in _cfg['models']['vosk'].items()}
TTS_MODELS = {k: _ROOT / v for k, v in _cfg['models']['tts'].items()}

# ── estado dinâmico de idioma ──────────────────────────────
_source_lang = 'en'
_target_lang = 'pt'


# ── API pública ────────────────────────────────────────────
def set_source_lang(lang='en'):
    global _source_lang
    _source_lang = lang or 'en'
    log = logging.getLogger('vidra')
    model = VOSK_MODELS.get(_source_lang)
    if not model or not model.exists():
        log.warning('Modelo Vosk para "%s" não encontrado em %s', _source_lang, model)
    return _source_lang


def set_target_lang(lang='pt'):
    global _target_lang
    _target_lang = lang or 'pt'
    log = logging.getLogger('vidra')
    model = TTS_MODELS.get(_target_lang)
    if not model or not model.exists():
        log.warning('Modelo TTS para "%s" não encontrado em %s', _target_lang, model)
    return _target_lang


def get_source_lang():
    return _source_lang


def get_target_lang():
    return _target_lang


def get_vosk_model(lang=None):
    return VOSK_MODELS.get(lang or _source_lang)


def get_tts_model(lang=None):
    return TTS_MODELS.get(lang or _target_lang)


def available_source_langs():
    return sorted(VOSK_MODELS.keys())


def available_target_langs():
    return sorted(TTS_MODELS.keys())


# ── __getattr__ mantém compatibilidade com imports legados ──
# Permite que `from src.configs import MODEL` funcione,
# resolvendo o valor dinamicamente no momento do acesso.
def __getattr__(name):
    if name == 'MODEL':
        return VOSK_MODELS.get(_source_lang)
    if name == 'MODEL_TTS':
        return TTS_MODELS.get(_target_lang)
    if name == 'LANG_TRANSLATE':
        return _target_lang
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
