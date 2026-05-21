import logging
import sys
from pathlib import Path

from src.configs import ROOT


def setup_logging(verbose=False):
    log = logging.getLogger('vidra')
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.handlers.clear()

    # console: mensagem pura (cores já vêm das tags)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    log.addHandler(ch)

    # arquivo: timestamp + mensagem (cores desligam automaticamente)
    log_dir = ROOT / 'output'
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / 'vidra.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S'))
    log.addHandler(fh)

    return log
