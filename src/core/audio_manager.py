import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

from src.configs import DATA, MODEL, MODEL_TTS

_ROOT = Path(__file__).resolve().parent.parent.parent  # raiz do projeto
from vosk import KaldiRecognizer, Model


# ── conversão ──────────────────────────────────────────

def get_mp3():
    return next(
        (os.path.join(DATA, f) for f in os.listdir(DATA) if f.endswith('.mp3')),
        None,
    )

def mp3_to_wav(mp3_path=None):
    mp3_file = mp3_path or get_mp3()
    if not mp3_file:
        print('nenhum mp3 encontrado')
        return None

    wav_file = mp3_file.replace('.mp3', '.wav')

    subprocess.run([
        'ffmpeg', '-i', mp3_file,
        '-ar', '16000', '-ac', '1', '-f', 'wav',
        wav_file,
    ], check=True, capture_output=True)

    return wav_file


# ── helpers de agrupamento ──────────────────────────────

_PAUSE_THRESH = 0.3   # segundos de silêncio entre palavras
_MAX_WORDS = 25       # palavras máximas por segmento
_MIN_WORDS = 3        # funde com anterior se abaixo disso

def _group_words(words):
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

    # funde segmentos muito curtos no anterior
    merged = []
    for g in groups:
        if merged and len(g) < _MIN_WORDS:
            merged[-1].extend(g)
        else:
            merged.append(g)

    return [{
        'text': ' '.join(w['word'] for w in g),
        'start': g[0]['start'],
        'end': g[-1]['end'],
        'words': g,
    } for g in merged]


_FMT_SRT_CACHE = {}

def _fmt_srt(sec):
    """Segundos → HH:MM:SS,mmm  (formato SRT)."""
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    ms = int((sec - int(sec)) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


# ── transcrição ────────────────────────────────────────

def transcribe(wav_file, with_timestamps=False):
    wf = wave.open(wav_file, 'rb')
    model = Model(str(MODEL))
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
        return [] if with_timestamps else ''

    segments = _group_words(raw_segments)

    if not with_timestamps:
        return ' '.join(s['text'] for s in segments)

    return segments


# ── tradução ───────────────────────────────────────────

def translate_segments(segments):
    """Traduz o text de cada segmento via GoogleTranslator.

    Retorna nova lista preservando start/end/words e
    adicionando campo 'original' com o texto fonte.
    """
    from src.core.translate import translate

    translated = []
    for seg in segments:
        new = dict(seg)
        new['original'] = seg['text']
        new['text'] = translate(seg['text'])
        translated.append(new)
    return translated


# ── salvamento ─────────────────────────────────────────

def clean_save(data, path=None):
    """Salva transcrição detectando formato automaticamente.

    data → str   ⇒  .txt (texto puro)
    data → list  ⇒  .srt + .json (segmentos c/ tempo)
    """
    path = path or DATA / 'output'

    if isinstance(data, list):
        # SRT
        srt_path = path.with_suffix('.srt') if path.suffix else DATA / f'{path.stem}.srt'
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(data, 1):
                f.write(f'{i}\n{_fmt_srt(seg["start"])} --> {_fmt_srt(seg["end"])}\n{seg["text"]}\n\n')

        # JSON word-level
        json_path = path.with_suffix('.json') if path.suffix else DATA / f'{path.stem}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(srt_path)

    # str → TXT
    txt_path = path.with_suffix('.txt') if path.suffix else DATA / f'{path.stem}.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(str(data))
    return str(txt_path)

# ---------- dub (substituição nos timestamps) ----------

def dub(audio_path, segments, wav_dir, output_path):
    """Substitui as falas no áudio original pelos WAVs TTS nos timestamps exatos.

    Mantém a duração original — TTS mais curto vira silêncio no final,
    TTS mais longo é truncado.
    """
    tmp_orig = Path('/tmp/_dub_orig.wav')
    tmp_dub  = Path('/tmp/_dub_out.wav')

    # 1. Converte original para WAV mono 22050 Hz (formato dos segmentos TTS)
    subprocess.run([
        'ffmpeg', '-y', '-i', audio_path,
        '-ar', '22050', '-ac', '1',
        str(tmp_orig),
    ], check=True, capture_output=True)

    # 2. Lê samples do original
    with wave.open(str(tmp_orig)) as f:
        sr, sw, nc = f.getframerate(), f.getsampwidth(), f.getnchannels()
        frames = bytearray(f.readframes(f.getnframes()))
        total_samples = f.getnframes()
        bps = sw * nc  # bytes per sample (frame)

    # 3. Substitui cada segmento no range correto
    for i, seg in enumerate(segments, 1):
        ss = int(seg['start'] * sr) * bps
        se = int(seg['end']   * sr) * bps
        wav_file = wav_dir / f'{i}.wav'
        if not wav_file.exists():
            continue

        with wave.open(str(wav_file)) as seg_w:
            seg_data = seg_w.readframes(seg_w.getnframes())

        size = se - ss
        if len(seg_data) < size:
            seg_data += b'\x00' * (size - len(seg_data))
        frames[ss:se] = seg_data[:size]

    # 4. Salva WAV temporário
    with wave.open(str(tmp_dub), 'wb') as f:
        f.setnchannels(nc)
        f.setsampwidth(sw)
        f.setframerate(sr)
        f.writeframes(bytes(frames))

    # 5. Converte para MP3 final
    subprocess.run([
        'ffmpeg', '-y', '-i', str(tmp_dub),
        '-codec:a', 'libmp3lame', '-qscale:a', '2',
        str(output_path),
    ], check=True, capture_output=True)

    # Limpeza
    tmp_orig.unlink(missing_ok=True)
    tmp_dub.unlink(missing_ok=True)

    return str(output_path)


# ---------- merge (áudio dublado + vídeo original) ----

def merge_video_audio(video_path, audio_path, output_path):
    """Substitui o áudio do MP4 pelo MP3 dublado sem re-encode do vídeo."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        str(out),
    ], check=True, capture_output=True)
    return str(out)


# ---------- tts --------------------- 
def _find_piper():
    """Localiza o binário piper no PATH ou na .venv do projeto."""
    pip = shutil.which('piper')
    if pip:
        return pip
    # fallback: .venv do projeto
    local = _ROOT / '.venv' / 'bin' / 'piper'
    if local.exists():
        return str(local)
    raise FileNotFoundError(
        'piper não encontrado. Instale com: pip install piper-tts'
    )

def speak(text, name_part):
    model_path = str(MODEL_TTS)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f'Modelo TTS não encontrado: {model_path}\n'
            f'Baixe de: https://huggingface.co/rhasspy/piper-voices/'
        )

    out_path = Path(name_part) if isinstance(name_part, str) else name_part
    out_path = out_path.with_suffix('.wav') if out_path.suffix != '.wav' else out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    piper = _find_piper()
    subprocess.run(
        [piper, '--model', model_path, '--output_file', str(out_path)],
        input=text.encode(),
        check=True,
    )
    return str(out_path)

