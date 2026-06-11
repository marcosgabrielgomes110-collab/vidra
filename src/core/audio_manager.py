"""Núcleo do VIDRA — transcrição, TTS, dublagem e merge."""

import json
import logging
import os
import shutil
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from vosk import KaldiRecognizer, Model

from src import configs as cfg

log = logging.getLogger('vidra')
_ROOT = Path(__file__).resolve().parent.parent.parent

# ── helpers ────────────────────────────────────────────────

def _fmt_srt(sec: float) -> str:
    """Segundos → HH:MM:SS,mmm (formato SRT)."""
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    ms = int((sec - int(sec)) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def _run_ffmpeg(args: list[str], desc: str = 'ffmpeg', live: bool = False):
    """Executa ffmpeg com logging e tratamento de erro.

    Args:
        live: se True, mostra progresso em tempo real no terminal.
    """
    try:
        if live:
            # banner oculto + só erros + stats ao vivo
            quiet = ['-hide_banner', '-loglevel', 'error', '-stats']
            subprocess.run(quiet + args, check=True)
        else:
            subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()[-300:] if exc.stderr else '(sem saída)'
        log.error('%s falhou (código %d): …%s', desc, exc.returncode, stderr)
        raise RuntimeError(f'{desc} falhou') from exc


# ── conversão MP3 → WAV ───────────────────────────────────

def _find_mp3() -> str | None:
    for f in os.listdir(cfg.DATA):
        if f.endswith('.mp3'):
            return os.path.join(cfg.DATA, f)
    return None


def mp3_to_wav(mp3_path: str | None = None) -> str | None:
    """Converte MP3 para WAV mono 16 kHz (formato exigido pelo Vosk)."""
    mp3_file = mp3_path or _find_mp3()
    if not mp3_file:
        log.error('Nenhum arquivo MP3 encontrado em %s', cfg.DATA)
        return None

    wav_file = mp3_file.replace('.mp3', '.wav')
    _run_ffmpeg([
        'ffmpeg', '-y', '-i', mp3_file,
        '-ar', '16000', '-ac', '1', '-f', 'wav', wav_file,
    ], desc='Conversão MP3→WAV')
    return str(wav_file)


# ── agrupamento de palavras ───────────────────────────────

_PAUSE_THRESH = 0.3
_MAX_WORDS = 25
_MIN_WORDS = 3


def _group_words(words: list[dict]) -> list[dict]:
    """Agrupa palavras do Vosk em segmentos por pausa e tamanho."""
    groups = []
    cur = []
    for w in words:
        if not cur:
            cur.append(w)
        elif w['start'] - cur[-1]['end'] > _PAUSE_THRESH:
            groups.append(cur)
            cur = [w]
        elif len(cur) >= _MAX_WORDS:
            groups.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        groups.append(cur)

    # Funde segmentos muito curtos no anterior
    merged = []
    for g in groups:
        if merged and len(g) < _MIN_WORDS:
            merged[-1].extend(g)
        else:
            merged.append(g)

    return [{
        'text':  ' '.join(w['word'] for w in g),
        'start': g[0]['start'],
        'end':   g[-1]['end'],
        'words': g,
    } for g in merged]


# ── transcrição ───────────────────────────────────────────

def transcribe(wav_file: str, with_timestamps: bool = False,
               lang: str | None = None) -> list[dict] | str:
    """Transcreve WAV usando modelo Vosk para o idioma informado.

    Returns:
        - with_timestamps=True → list[dict] (segmentos)
        - with_timestamps=False → str (texto puro)
    """
    model_path = cfg.get_vosk_model(lang)
    if not model_path or not model_path.exists():
        raise FileNotFoundError(
            f'Modelo Vosk para "{lang or cfg.get_source_lang()}" '
            f'não encontrado em {model_path}. '
            f'Disponíveis: {cfg.available_source_langs()}'
        )

    # Silencia logs verbosos do Vosk (C++)
    import vosk as _vosk
    _vosk.SetLogLevel(-1)

    wf = wave.open(wav_file, 'rb')
    model = Model(str(model_path))
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    raw_segments = []
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            words = res.get('result', [])
            if words:
                raw_segments.extend(words)

    final = json.loads(rec.FinalResult())
    final_words = final.get('result', [])
    if final_words:
        raw_segments.extend(final_words)

    if not raw_segments:
        log.warning('Nenhuma palavra reconhecida no áudio')
        return [] if with_timestamps else ''

    segments = _group_words(raw_segments)
    if not with_timestamps:
        return ' '.join(s['text'] for s in segments)

    log.info('  %d segmentos, %d palavras', len(segments), len(raw_segments))
    return segments


# ── salvamento ────────────────────────────────────────────

def clean_save(data, path=None) -> dict:
    """Salva transcrição/tradução em SRT + JSON.

    Args:
        data: str (texto puro) ou list[dict] (segmentos c/ tempo)
        path: diretório ou arquivo base (opcional)

    Returns:
        dict com chaves 'srt' e 'json' (ou 'txt') contendo os caminhos.
    """
    if path is None:
        path = cfg.DATA / 'output'
    path = Path(path)

    result = {}

    if isinstance(data, list):
        # path = '.vidra/tmp/output'           → dir=.vidra/tmp,      stem=output
        # path = '.vidra/tmp/output_pt/output' → dir=.vidra/tmp/output_pt, stem=output
        out_dir, stem = path.parent, path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        srt = out_dir / f'{stem}.srt'
        with open(srt, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(data, 1):
                f.write(f'{i}\n{_fmt_srt(seg["start"])} --> '
                        f'{_fmt_srt(seg["end"])}\n{seg["text"]}\n\n')
        result['srt'] = str(srt)

        jsn = out_dir / f'{stem}.json'
        with open(jsn, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        result['json'] = str(jsn)

        return result

    # str → TXT
    txt = path.with_suffix('.txt') if path.suffix else cfg.DATA / f'{path.stem}.txt'
    with open(txt, 'w', encoding='utf-8') as f:
        f.write(str(data))
    result['txt'] = str(txt)
    return result


# ── tradução ──────────────────────────────────────────────

def translate_segments(segments: list[dict], source: str = 'auto',
                       target: str | None = None) -> list[dict]:
    """Traduz o text de cada segmento. Preserva start/end/words."""
    from src.core.translate import translate

    tgt = target or cfg.get_target_lang()
    translated = []
    for seg in segments:
        new = dict(seg)
        new['original'] = seg['text']
        try:
            new['text'] = translate(seg['text'], source=source, target=tgt)
        except Exception as exc:
            log.warning('Falha na tradução do segmento, mantendo original: %s', exc)
            # mantém texto original como fallback
        translated.append(new)
    return translated


# ── TTS (Piper) ────────────────────────────────────────────

def _find_piper() -> str:
    """Localiza o binário piper no PATH ou na .venv do projeto."""
    pip = shutil.which('piper')
    if pip:
        return pip
    local = _ROOT / '.venv' / 'bin' / 'piper'
    if local.exists():
        return str(local)
    raise FileNotFoundError(
        'piper não encontrado. Instale com: pip install piper-tts'
    )


def speak(text: str, name_part, lang: str | None = None) -> str:
    """Gera áudio TTS para um único segmento via Piper."""
    model_path = cfg.get_tts_model(lang)
    if not model_path or not model_path.exists():
        raise FileNotFoundError(
            f'Modelo TTS para "{lang or cfg.get_target_lang()}" '
            f'não encontrado em {model_path}'
        )

    out_path = Path(name_part)
    out_path = out_path.with_suffix('.wav') if out_path.suffix != '.wav' else out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    piper = _find_piper()
    try:
        subprocess.run(
            [piper, '--model', str(model_path), '--output_file', str(out_path)],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()[-200:] if exc.stderr else ''
        raise RuntimeError(f'Piper TTS falhou para "{text[:50]}…": {stderr}') from exc

    return str(out_path)


def speak_parallel(segments: list[dict], output_dir: Path | str,
                   max_workers: int | None = None,
                   lang: str | None = None,
                   progress_callback=None) -> list[str]:
    """Gera todos os áudios TTS em paralelo.

    Args:
        progress_callback: chamado a cada segmento concluído (para rich bar).

    Returns:
        Lista de caminhos dos WAVs gerados, na ordem dos segmentos.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workers = max_workers or cfg.TTS_WORKERS
    total = len(segments)

    results: list[tuple[int, str | None]] = [None] * total

    def _gen(i: int, seg: dict) -> tuple[int, str]:
        wav_path = output_dir / f'{i}.wav'
        try:
            speak(seg['text'], wav_path, lang=lang)
        except Exception as exc:
            log.error('TTS falhou para segmento %d: %s', i, exc)
            _write_silent_wav(wav_path, duration=0.5)
        return i, str(wav_path)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_gen, i, seg): i for i, seg in enumerate(segments, 1)}
        done = 0
        for future in as_completed(futures):
            i, _ = future.result()
            done += 1
            if progress_callback:
                progress_callback()
            elif done % max(1, total // 10) == 0 or done == total:
                log.info('  TTS: %d/%d', done, total)

    # Reconstroi lista ordenada
    ordered = []
    for i in range(1, total + 1):
        w = output_dir / f'{i}.wav'
        ordered.append(str(w))
    return ordered


def _write_silent_wav(path: Path, duration: float = 0.5,
                      rate: int = 22050):
    """Cria um WAV silencioso (fallback quando TTS falha)."""
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b'\x00' * int(rate * duration * 2))


# ── dublagem (substituição nos timestamps) ────────────────

def dub(audio_path: str, segments: list[dict], wav_dir: Path | str,
        output_path: str) -> str:
    """Substitui as falas originais pelos WAVs TTS nos timestamps exatos.

    TTS mais curto que a fala original → preenche com silêncio.
    TTS mais longo → truncado.
    """
    sample_rate = cfg.TTS_SAMPLE_RATE
    wav_dir = Path(wav_dir)
    tmp_orig = Path('/tmp/_dub_orig.wav')
    tmp_dub = Path('/tmp/_dub_out.wav')

    # 1. Converte original para WAV mono (sample rate do TTS)
    _run_ffmpeg([
        'ffmpeg', '-y', '-i', audio_path,
        '-ar', str(sample_rate), '-ac', '1', str(tmp_orig),
    ], desc='Conversão para dublagem', live=True)

    # 2. Lê samples do original
    with wave.open(str(tmp_orig)) as f:
        sr, sw, nc = f.getframerate(), f.getsampwidth(), f.getnchannels()
        frames = bytearray(f.readframes(f.getnframes()))
        total_samples = f.getnframes()
        bps = sw * nc  # bytes per sample (frame)

    # 3. Substitui cada segmento no range correto
    for i, seg in enumerate(segments, 1):
        ss = int(seg['start'] * sr) * bps
        se = int(seg['end'] * sr) * bps
        wav_file = wav_dir / f'{i}.wav'
        if not wav_file.exists():
            log.warning('  WAV %d não encontrado, pulando', i)
            continue

        try:
            with wave.open(str(wav_file)) as seg_w:
                seg_data = seg_w.readframes(seg_w.getnframes())
        except Exception as exc:
            log.warning('  Erro lendo WAV %d: %s', i, exc)
            continue

        size = se - ss
        if len(seg_data) < size:
            seg_data += b'\x00' * (size - len(seg_data))
        if ss < len(frames):
            frames[ss:se] = seg_data[:min(size, len(frames) - ss)]

    # 4. Salva WAV temporário
    with wave.open(str(tmp_dub), 'wb') as f:
        f.setnchannels(nc)
        f.setsampwidth(sw)
        f.setframerate(sr)
        f.writeframes(bytes(frames))

    # 5. Converte para MP3 final
    _run_ffmpeg([
        'ffmpeg', '-y', '-i', str(tmp_dub),
        '-codec:a', 'libmp3lame', '-qscale:a', '2', str(output_path),
    ], desc='Codificação MP3 dublado', live=True)

    tmp_orig.unlink(missing_ok=True)
    tmp_dub.unlink(missing_ok=True)
    log.info('  Áudio dublado: %s', output_path)
    return str(output_path)


# ── merge (áudio dublado + vídeo) ──────────────────────────

def merge_video_audio(video_path: str, audio_path: str,
                       output_path: str) -> str:
    """Substitui o áudio do MP4 pelo MP3 dublado sem re-encode do vídeo."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    _run_ffmpeg([
        'ffmpeg', '-y', '-stats',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        str(out),
    ], desc='Merge vídeo+áudio', live=True)

    log.info('  Vídeo final: %s', out)
    return str(out)
