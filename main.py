#!/usr/bin/env python3
"""VIDRA — Pipeline local de dublagem automática de vídeos.

Uso:
    python main.py -u "https://youtube.com/watch?v=..."
    python main.py -f "/path/to/video.mp4"
    python main.py -u "..." --direction pt2en
    python main.py                           # modo interativo
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── redireciona __pycache__ ───────────────────────────────
_CACHE = Path(__file__).resolve().parent / '.pycache'
_CACHE.mkdir(exist_ok=True)
sys.pycache_prefix = str(_CACHE)

from src import configs as cfg
from src.core.input import download_mp4, download_audio, import_local_video
from src.core.audio_manager import (
    clean_save, dub, merge_video_audio, mp3_to_wav,
    speak_parallel, translate_segments, transcribe,
)
from src.core.session import Session
from src.utils.colors import blue, bold, cyan, green, red, yellow
from src.utils.logger import setup_logging

log = setup_logging()

_DIRECTIONS = {
    'en2pt': ('en', 'pt'),
    'pt2en': ('pt', 'en'),
}


# ── helpers de terminal ───────────────────────────────────

def _clear():
    """Limpa a tela."""
    os.system('clear')


def _separador(titulo=''):
    """Linha horizontal ASCII."""
    linha = '─' * 50
    if titulo:
        print(f'  {cyan(linha)}')
        print(f'  {bold(cyan(titulo))}')
        print(f'  {cyan(linha)}')
    else:
        print(f'  {cyan(linha)}')


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='vidra — pipeline local de dublagem automática',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Exemplos:\n'
            '  %(prog)s -u "https://youtube.com/watch?v=abc123"\n'
            '  %(prog)s -f "/tmp/video.mp4"\n'
            '  %(prog)s -u "..." --direction pt2en\n'
            '  %(prog)s -f "/tmp/video.mp4" -s en -t pt\n'
            '  %(prog)s -u "..." --resume\n'
            '  %(prog)s --list-models\n'
        ),
    )
    inp = parser.add_argument_group('entrada')
    inp.add_argument('-u', '--url', help='URL do YouTube para download')
    inp.add_argument('-f', '--file', help='Caminho de vídeo local')

    lang = parser.add_argument_group('idioma')
    lang.add_argument('-d', '--direction',
                      choices=list(_DIRECTIONS.keys()),
                      help=f'Direção: {", ".join(_DIRECTIONS.keys())}')
    lang.add_argument('-s', '--source',
                      default=cfg.DEFAULT_SOURCE_LANG,
                      help='Idioma original. Padrão: lido de vidra.json')
    lang.add_argument('-t', '--target',
                      default=cfg.DEFAULT_TARGET_LANG,
                      help='Idioma alvo. Padrão: lido de vidra.json')

    parser.add_argument('-r', '--resume', action='store_true',
                        help='Retomar pipeline do último checkpoint')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Log detalhado (DEBUG)')
    parser.add_argument('--list-models', action='store_true',
                        help='Listar modelos de idioma disponíveis')
    parser.add_argument('--reset', action='store_true',
                        help='Ignorar checkpoint e começar do zero')
    return parser.parse_args(argv)


# ═══════════════════════════════════════════════════════════
# Interface interativa
# ═══════════════════════════════════════════════════════════

def _header():
    """Logo ASCII."""
    print()
    print(f'  {bold(cyan("╔══════════════════════════════════════════╗"))}')
    print(f'  {bold(cyan("║           V I D R A                     ║"))}')
    print(f'  {bold(cyan("║   Pipeline de Dublagem Automatica       ║"))}')
    print(f'  {bold(cyan("╚══════════════════════════════════════════╝"))}')
    print(f'  {bold("100% local  ·  open source  ·  Python")}')
    print()


def _interactive_menu():
    """Menu principal interativo."""
    import questionary

    while True:
        _clear()
        _header()

        escolha = questionary.select(
            'O que deseja fazer?',
            qmark='',
            choices=[
                '1. Iniciar Pipeline',
                '2. Configuracoes',
                '3. Ver Configuracao',
                '4. Sair',
            ],
        ).ask()

        if escolha is None or escolha == '4. Sair':
            print(f'\n  {yellow("Ate mais!")}\n')
            break

        if escolha == '1. Iniciar Pipeline':
            _interactive_pipeline()
        elif escolha == '2. Configuracoes':
            _interactive_config()
        elif escolha == '3. Ver Configuracao':
            _show_config()
            input(f'\n  {cyan("Pressione ENTER para voltar...")}')


def _interactive_pipeline():
    import questionary

    _clear()
    _header()

    modo = questionary.select(
        'Origem do video:',
        qmark='',
        choices=['URL do YouTube', 'Arquivo local'],
    ).ask()
    if modo is None:
        return

    if modo == 'URL do YouTube':
        url = questionary.text('URL do YouTube:').ask()
        if not url:
            return
        session_id = url
        input_type = 'url'
    else:
        path = questionary.path('Caminho do arquivo de video:').ask()
        if not path:
            return
        session_id = str(Path(path).resolve())
        input_type = 'file'

    dir_opts = list(_DIRECTIONS.keys())
    default_dir = f'{cfg.DEFAULT_SOURCE_LANG}2{cfg.DEFAULT_TARGET_LANG}'
    if default_dir not in dir_opts:
        default_dir = 'en2pt'

    direcao = questionary.select(
        'Direcao de traducao:',
        qmark='',
        choices=dir_opts + ['Personalizar'],
        default=default_dir,
    ).ask()
    if direcao is None:
        return

    if direcao == 'Personalizar':
        src = questionary.select('Idioma original:', qmark='',
                                 choices=cfg.available_source_langs(),
                                 default=cfg.DEFAULT_SOURCE_LANG).ask()
        tgt = questionary.select('Idioma alvo:', qmark='',
                                 choices=cfg.available_target_langs(),
                                 default=cfg.DEFAULT_TARGET_LANG).ask()
    else:
        src, tgt = _DIRECTIONS[direcao]

    print()
    _separador('RESUMO')
    print(f'  Entrada:  {session_id}')
    print(f'  Direcao:  {green(src)} → {green(tgt)}')
    print()

    if not questionary.confirm('Iniciar pipeline?', default=True, qmark='').ask():
        return

    if not _ensure_models(src, tgt):
        log.error('Modelos necessarios nao disponiveis. Execute: bash install.sh')
        input(f'\n  {cyan("Pressione ENTER...")}')
        return

    print()
    session = _resolve_session(session_id, src, tgt, input_type, False, True)
    pipeline(session)

    input(f'\n  {cyan("Pressione ENTER para voltar...")}')


def _interactive_config():
    import questionary

    config_path = cfg._CONFIG_SEARCH[0]
    try:
        with open(config_path) as f:
            conf = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        conf = {}

    _clear()
    _header()

    lang = conf.get('language', {})
    lang_src = questionary.select(
        'Idioma original padrao:',
        qmark='',
        choices=cfg.available_source_langs(),
        default=lang.get('source', 'en'),
    ).ask()
    if lang_src:
        lang['source'] = lang_src

    lang_tgt = questionary.select(
        'Idioma alvo padrao:',
        qmark='',
        choices=cfg.available_target_langs(),
        default=lang.get('target', 'pt'),
    ).ask()
    if lang_tgt:
        lang['target'] = lang_tgt

    conf['language'] = lang

    tts = conf.get('tts', {})
    workers = questionary.text(
        'Workers paralelos para TTS:',
        qmark='',
        default=str(tts.get('parallel_workers', 4)),
    ).ask()
    if workers and workers.isdigit():
        tts['parallel_workers'] = int(workers)
        tts['sample_rate'] = cfg.TTS_SAMPLE_RATE
    conf['tts'] = tts

    with open(config_path, 'w') as f:
        json.dump(conf, f, indent=2)
    print(f'  {green("OK")}  Configuracao salva em vidra.json')

    import importlib
    importlib.reload(cfg)

    input(f'\n  {cyan("Pressione ENTER para voltar...")}')


def _show_config():
    print()
    _separador('CONFIGURACAO ATUAL')

    items = [
        ('Idioma origem', cfg.get_source_lang()),
        ('Idioma alvo', cfg.get_target_lang()),
        ('Workers TTS', str(cfg.TTS_WORKERS)),
        ('Tradutor', cfg.TRANSLATE_PREFERRED),
        ('Diretorio dados', str(cfg.DATA)),
        ('Diretorio saida', str(cfg.OUTPUT)),
    ]
    for nome, valor in items:
        print(f'  {nome+":":20s} {bold(valor)}')

    print()
    print(f'  {bold("Modelos Vosk")}')
    for lang in cfg.available_source_langs():
        p = cfg.get_vosk_model(lang)
        ok = 'OK' if p and p.exists() else 'FALTA'
        cor = green if ok == 'OK' else red
        print(f'    [{cor(ok)}]  {lang}  {p}')

    print()
    print(f'  {bold("Modelos TTS (Piper)")}')
    for lang in cfg.available_target_langs():
        p = cfg.get_tts_model(lang)
        ok = 'OK' if p and p.exists() else 'FALTA'
        cor = green if ok == 'OK' else red
        print(f'    [{cor(ok)}]  {lang}  {p}')

    print()
    for k, (s, tgt) in _DIRECTIONS.items():
        vosk_ok = cfg.get_vosk_model(s) and cfg.get_vosk_model(s).exists()
        tts_ok = cfg.get_tts_model(tgt) and cfg.get_tts_model(tgt).exists()
        status = green('OK') if vosk_ok and tts_ok else red('FALTA MODELOS')
        print(f'    {bold(k):10s}  {s} → {tgt}  [{status}]')


# ═══════════════════════════════════════════════════════════
# Modelos — validação e download
# ═══════════════════════════════════════════════════════════

def _check_models(source: str, target: str) -> list[str]:
    missing = []
    vosk = cfg.get_vosk_model(source)
    if not vosk or not vosk.exists():
        missing.append(f'Vosk ({source}): {vosk}')
    tts = cfg.get_tts_model(target)
    if not tts or not tts.exists():
        missing.append(f'TTS ({target}): {tts}')
    return missing


def _install_tts_model(lang: str) -> bool:
    url_map = {
        'en': (
            'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx',
            'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json',
        ),
    }
    urls = url_map.get(lang)
    if not urls:
        log.error('Nao sei baixar TTS para "%s". Baixe manualmente.', lang)
        return False
    tts_dir = cfg.ROOT / 'models' / 'tts'
    tts_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        fname = Path(url).name
        dest = tts_dir / fname
        if dest.exists():
            continue
        log.info('Baixando %s ...', fname)
        try:
            subprocess.run(['wget', '-q', '--show-progress', '-O', str(dest), url], check=True)
        except subprocess.CalledProcessError:
            log.error('Falha ao baixar %s', fname)
            dest.unlink(missing_ok=True)
            return False
    return True


def _install_vosk_model(lang: str) -> bool:
    url_map = {
        'en': 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
        'pt': 'https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip',
    }
    url = url_map.get(lang)
    if not url:
        log.error('Nao sei baixar Vosk para "%s".', lang)
        return False
    models_dir = cfg.ROOT / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    zip_path = models_dir / f'vosk-{lang}.zip'
    log.info('Baixando modelo Vosk (%s) ...', lang)
    try:
        subprocess.run(['wget', '-q', '--show-progress', '-O', str(zip_path), url], check=True)
        subprocess.run(['unzip', '-qo', str(zip_path), '-d', str(models_dir)], check=True)
        zip_path.unlink()
    except subprocess.CalledProcessError:
        log.error('Falha ao baixar/extrair Vosk %s', lang)
        zip_path.unlink(missing_ok=True)
        return False
    return True


def _ensure_models(source: str, target: str):
    missing = _check_models(source, target)
    if not missing:
        return True
    print()
    log.warning('Modelos necessarios nao encontrados:')
    for m in missing:
        log.warning('  %s %s', red('X'), m)
    print()

    import questionary
    for m in missing:
        if 'Vosk' in m:
            resp = questionary.confirm(f'Baixar modelo Vosk ({source})?', default=False, qmark='').ask()
            if resp:
                if not _install_vosk_model(source):
                    return False
            else:
                return False
        elif 'TTS' in m:
            resp = questionary.confirm(f'Baixar voz Piper ({target})?', default=False, qmark='').ask()
            if resp:
                if not _install_tts_model(target):
                    return False
            else:
                return False
    return True


# ═══════════════════════════════════════════════════════════
# Listagem de modelos
# ═══════════════════════════════════════════════════════════

def _list_models():
    print()
    _separador('MODELOS DISPONIVEIS')
    print()

    print(f'  {bold("Vosk (transcricao)")}')
    for lang in cfg.available_source_langs():
        p = cfg.get_vosk_model(lang)
        ok = green('OK') if p and p.exists() else red('FALTA')
        print(f'    [{ok}]  {lang:6s}  {p}')

    print()
    print(f'  {bold("Piper TTS (voz sintetica)")}')
    for lang in cfg.available_target_langs():
        p = cfg.get_tts_model(lang)
        ok = green('OK') if p and p.exists() else red('FALTA')
        print(f'    [{ok}]  {lang:6s}  {p}')

    print()
    _separador('DIRECOES SUPORTADAS')
    for k, (s, tgt) in _DIRECTIONS.items():
        vosk_ok = cfg.get_vosk_model(s) and cfg.get_vosk_model(s).exists()
        tts_ok = cfg.get_tts_model(tgt) and cfg.get_tts_model(tgt).exists()
        status = green('OK') if vosk_ok and tts_ok else yellow('FALTA MODELOS')
        print(f'    --direction {k:10s}  {s} → {tgt}  [{status}]')

    print()
    return 0


# ═══════════════════════════════════════════════════════════
# Sessão
# ═══════════════════════════════════════════════════════════

def _resolve_session(session_id: str, source: str, target: str,
                     input_type: str, resume: bool, reset: bool) -> Session:
    if reset:
        old = Session(cfg.CHECKPOINT_DIR, session_id)
        if old.checkpoint_path.exists():
            old.checkpoint_path.unlink()
            log.info('Checkpoint anterior removido (--reset)')
    if resume:
        session = Session.load(cfg.CHECKPOINT_DIR, session_id)
        if session:
            log.info('Retomando sessao %s (%s)', session.session_id, session.progress_str())
            return session
        log.info('Nenhum checkpoint encontrado, iniciando nova sessao')
    return Session(cfg.CHECKPOINT_DIR, session_id, source=source, target=target,
                   input_type=input_type)


def _pipeline_error(step: str, exc: Exception, session: Session):
    log.error('%s [%s] %s', red('ERRO'), step, exc)
    flag = '-f' if session.input_type == 'file' else '-u'
    log.info('Para retomar: python main.py %s "%s" --resume', flag, session.url)
    session.save()


# ── barra de progresso ASCII ──────────────────────────────

def _progress_ascii(iteravel, total, prefix='', largura=25):
    """Itera sobre *iteravel* exibindo barra ASCII."""
    for i, item in enumerate(iteravel, 1):
        yield item
        pct = i / total
        preenchido = int(largura * pct)
        barra = '#' * preenchido + '.' * (largura - preenchido)
        print(f'\r  {prefix} [{green(barra)}] {i}/{total}', end='', flush=True)
    print()


# ═══════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════

def pipeline(session: Session):
    source_lang = session.source
    target_lang = session.target

    cfg.set_source_lang(source_lang)
    cfg.set_target_lang(target_lang)

    source_label = 'Arquivo' if session.input_type == 'file' else 'URL'
    print()
    _separador('VIDRA - Pipeline de Dublagem')
    print(f'  {source_label}:  {bold(session.url)}')
    print(f'  Direcao:  {green(source_lang)} → {green(target_lang)}')
    print(f'  Sessao:   {session.session_id}')
    if session.completed:
        print(f'  Resume:   {session.progress_str()}')
    print()

    t_start = time.time()

    # ── INPUT ─────────────────────────────────────────────────
    if not session.is_complete('download'):
        log.info('%s  Obtendo video...', cyan('>>>'))
        try:
            if session.input_type == 'file':
                movie, audio = import_local_video(session.url)
            else:
                movie = download_mp4(session.url)
                audio = download_audio(session.url)
            log.info('     Video: %s', Path(movie).name)
            log.info('     Audio: %s', Path(audio).name)
            session.mark('download', {'movie': movie, 'audio': audio})
        except Exception as exc:
            _pipeline_error('download', exc, session)
            return False
    else:
        data = session.get('download')
        movie, audio = data['movie'], data['audio']
        log.info('%s  [input] OK (checkpoint)', cyan('>>>'))

    # ── CONVERT ───────────────────────────────────────────────
    if not session.is_complete('convert'):
        log.info('%s  Convertendo audio...', cyan('>>>'))
        try:
            wav = mp3_to_wav(audio)
            if not wav:
                raise RuntimeError('Conversao MP3→WAV retornou None')
            session.mark('convert', wav)
        except Exception as exc:
            _pipeline_error('convert', exc, session)
            return False
    else:
        wav = session.get('convert')
        log.info('%s  [convert] OK (checkpoint)', cyan('>>>'))

    # ── TRANSCRIBE ────────────────────────────────────────────
    if not session.is_complete('transcribe'):
        log.info('%s  Transcrevendo (Vosk %s)...', cyan('>>>'), source_lang)
        try:
            transcription = transcribe(wav, with_timestamps=True, lang=source_lang)
            if not transcription:
                raise RuntimeError('Transcricao vazia — nenhuma fala reconhecida')
            paths = clean_save(transcription)
            log.info('     %d segmentos', len(transcription))
            log.info('     SRT: %s', paths['srt'])
            session.mark('transcribe', paths)
        except Exception as exc:
            _pipeline_error('transcribe', exc, session)
            return False
    else:
        paths = session.get('transcribe')
        try:
            with open(paths['json']) as f:
                transcription = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            _pipeline_error('transcribe', exc, session)
            return False
        log.info('%s  [transcribe] OK (checkpoint)', cyan('>>>'))

    # ── TRANSLATE ─────────────────────────────────────────────
    if not session.is_complete('translate'):
        log.info('%s  Traduzindo %s→%s...', green('>>>'), source_lang, target_lang)
        try:
            translated = translate_segments(transcription,
                                            source=source_lang,
                                            target=target_lang)
            lang_dir = cfg.DATA / f'output_{target_lang}'
            lang_dir.mkdir(parents=True, exist_ok=True)
            t_paths = clean_save(translated, lang_dir / 'output')
            log.info('     SRT: %s', t_paths['srt'])
            session.mark('translate', t_paths)
        except Exception as exc:
            _pipeline_error('translate', exc, session)
            return False
    else:
        t_paths = session.get('translate')
        try:
            with open(t_paths['json']) as f:
                translated = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            _pipeline_error('translate', exc, session)
            return False
        log.info('%s  [translate] OK (checkpoint)', green('>>>'))

    # ── TTS ───────────────────────────────────────────────────
    if not session.is_complete('tts'):
        n = len(translated)
        log.info('%s  Gerando %d audios (Piper %s, %d workers)...',
                 yellow('>>>'), n, target_lang, cfg.TTS_WORKERS)
        try:
            wav_dir = cfg.DATA / 'wav_output'

            # Barra ASCII
            def _cb():
                nonlocal done
                done += 1
                pct = done / n
                w = 25
                bar = '#' * int(w * pct) + '.' * (w - int(w * pct))
                print(f'\r  [{green(bar)}] {done}/{n}', end='', flush=True)
                if done == n:
                    print()
            done = 0

            paths_list = speak_parallel(
                translated, wav_dir, lang=target_lang,
                progress_callback=_cb,
            )

            n_ok = sum(1 for p in paths_list if Path(p).stat().st_size > 100)
            log.info('     %d/%d audios OK', n_ok, n)
            session.mark('tts', {'dir': str(wav_dir), 'count': n, 'ok': n_ok})
        except Exception as exc:
            _pipeline_error('tts', exc, session)
            return False
    else:
        tts_data = session.get('tts')
        log.info('%s  [tts] OK (checkpoint): %d audios', yellow('>>>'), tts_data.get('count', '?'))
        wav_dir = Path(tts_data.get('dir', cfg.DATA / 'wav_output'))

    # ── DUB ───────────────────────────────────────────────────
    if not session.is_complete('dub'):
        log.info('%s  Dublando audio...', blue('>>>'))
        try:
            title = Path(movie).stem
            final_mp3 = cfg.DATA / f'{title}_final.mp3'
            dub(audio, translated, wav_dir, str(final_mp3))
            session.mark('dub', str(final_mp3))
        except Exception as exc:
            _pipeline_error('dub', exc, session)
            return False
    else:
        final_mp3 = session.get('dub')
        log.info('%s  [dub] OK (checkpoint)', blue('>>>'))

    # ── MERGE ─────────────────────────────────────────────────
    if not session.is_complete('merge'):
        log.info('%s  Mesclando video + audio...', bold(cyan('>>>')))
        try:
            title = Path(movie).stem
            final_mp4 = cfg.OUTPUT / f'{title}_final.mp4'
            merge_video_audio(movie, str(final_mp3), str(final_mp4))
            session.mark('merge', str(final_mp4))
        except Exception as exc:
            _pipeline_error('merge', exc, session)
            return False
    else:
        final_mp4 = session.get('merge')
        log.info('%s  [merge] OK (checkpoint)', bold(cyan('>>>')))

    # ── CLEANUP ───────────────────────────────────────────────
    log.info('%s  Limpando temporarios...', red('>>>'))
    try:
        for item in cfg.DATA.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                item.unlink(missing_ok=True)
        session.checkpoint_path.unlink(missing_ok=True)
    except Exception as exc:
        log.warning('Cleanup parcial: %s', exc)

    elapsed = time.time() - t_start
    mins, secs = divmod(int(elapsed), 60)
    print()
    _separador()
    print(f'  {bold(green("Pipeline concluido!"))}')
    print(f'  Tempo:  {mins}min {secs}s')
    print(f'  Saida:  {bold(str(final_mp4))}')
    print()
    return True


# ═══════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════

def main():
    args = _parse_args()

    if args.verbose:
        setup_logging(verbose=True)
        globals()['log'] = logging.getLogger('vidra')

    if args.list_models:
        sys.exit(_list_models())

    # ── modo interativo ──
    if not args.url and not args.file:
        try:
            _interactive_menu()
        except ImportError:
            url = input('URL do YouTube: ').strip()
            if not url:
                log.error('Nenhuma URL fornecida')
                sys.exit(1)
            args.url = url
        except (EOFError, KeyboardInterrupt):
            print()
        return

    # ── entrada direta ──
    if args.file:
        session_id = str(Path(args.file).resolve())
        input_type = 'file'
    elif args.url:
        session_id = args.url
        input_type = 'url'
    else:
        return

    if args.direction:
        src, tgt = _DIRECTIONS[args.direction]
    else:
        src, tgt = args.source, args.target

    log.info('Direcao: %s -> %s', src, tgt)

    if not _ensure_models(src, tgt):
        log.error('Modelos necessarios nao disponiveis. Execute: bash install.sh')
        sys.exit(1)

    session = _resolve_session(session_id, src, tgt, input_type,
                               args.resume, args.reset)

    success = pipeline(session)
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\n  {yellow("Interrompido pelo usuario")}')
        sys.exit(130)
    except Exception as exc:
        log.exception('Erro fatal: %s', exc)
        sys.exit(1)
