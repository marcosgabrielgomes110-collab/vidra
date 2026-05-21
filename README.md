![VIDRA](assets/vidra.png)

<br/>

<p align="center">
  <strong>Pipeline local de IA</strong> — download, transcrição, tradução,
  <br/>voz sintética e dublagem automática de vídeos.
  <br/><strong>100% offline · open source · Python</strong>
</p>

<br/>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Vosk-Speech--to--Text-FF6F00?style=flat&logoColor=white" alt="Vosk">
  <img src="https://img.shields.io/badge/Piper_TTS-Portugu%C3%AAs-7B3FA0?style=flat&logoColor=white" alt="Piper TTS">
  <img src="https://img.shields.io/badge/yt--dlp-Download-FF0000?style=flat&logo=youtube&logoColor=white" alt="yt-dlp">
  <img src="https://img.shields.io/badge/FFmpeg-%C3%81udio%2F%20V%C3%ADdeo-007808?style=flat&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat" alt="MIT">
</p>

---

## ✨ Features

<table>
  <tr>
    <td align="center" width="160">🎬<br/><b>Download</b><br/><sub>YouTube via yt-dlp</sub></td>
    <td align="center" width="160">🧠<br/><b>Transcrição</b><br/><sub>Vosk word-level</sub></td>
    <td align="center" width="160">🌍<br/><b>Tradução</b><br/><sub>GoogleTranslator EN→PT</sub></td>
  </tr>
  <tr>
    <td align="center">🎤<br/><b>TTS</b><br/><sub>Piper voz Faber PT-BR</sub></td>
    <td align="center">🎯<br/><b>Dublagem</b><br/><sub>Substituição temporal precisa</sub></td>
    <td align="center">📦<br/><b>Export</b><br/><sub>SRT + JSON + MP4 final</sub></td>
  </tr>
  <tr>
    <td align="center">📄<br/><b>SRT sincronizado</b><br/><sub>Legendas com timestamp</sub></td>
    <td align="center">🔊<br/><b>Áudio segmentado</b><br/><sub>WAV por fala</sub></td>
    <td align="center">🐧<br/><b>100% local</b><br/><sub>Zero dependência cloud</sub></td>
  </tr>
</table>

---

## 🧠 Pipeline

```
                     ┌─────────────┐
                     │  YouTube    │
                     │    URL      │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  yt-dlp     │
                     │  MP4 + MP3  │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  ffmpeg      │
                     │  WAV 16kHz  │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Vosk       │
                     │  word-level │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Translator │
                     │   EN → PT   │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Piper TTS  │
                     │   PT-BR     │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Dublagem   │
                     │  timestamps │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Merge      │
                     │  c:v copy   │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  MP4 Final  │
                     │  Dublado    │
                     └─────────────┘
```

---

## 📦 Pré-requisitos

<table>
<tr>
<th>Arch Linux</th>
<th>Debian / Ubuntu</th>
<th>macOS (Homebrew)</th>
</tr>
<tr>
<td>

```bash
sudo pacman -S ffmpeg \
  wget unzip python
```
</td>
<td>

```bash
sudo apt install ffmpeg \
  wget unzip python3 python3-venv
```
</td>
<td>

```bash
brew install ffmpeg \
  wget unzip python
```
</td>
</tr>
</table>

---

## 🚀 Instalação

```bash
# Clone
git clone https://github.com/seu-usuario/vidra.git
cd vidra

# Setup automático (.venv + modelos)
bash install.sh

# Ativar ambiente
source .venv/bin/activate
```

> O `install.sh` baixa os modelos Vosk (EN-US + PT-BR) e Piper TTS (PT-BR)
> para o diretório `models/`. Cerca de ~80 MB no total.

---

## 🎯 Uso

```bash
# Com URL direta
python main.py -u "https://youtube.com/watch?v=dQw4w9WgXcQ"

# Modo interativo
python main.py
# > URL do YouTube: <cole a url aqui>
```

### Exemplo de execução

```
[vidra] iniciando pipeline para: https://youtube.com/watch?v=dQw4w9WgXcQ
[download] baixando video e audio...
[transcricao] transcrevendo...
  42 segmentos
  SRT:  imbox/output.srt
  JSON: imbox/output.json
[traducao] pt:
  SRT:  imbox/output_pt/output.srt
  JSON: imbox/output_pt/output.json
[tts] gerando 42 audios...
  42 audios -> imbox/wav_output/
[dub] audio dublado: imbox/*_final.mp3
[merge] video final: output/*_final.mp4
[cleanup] limpando imbox...
[vidra] concluido!
```

---

## 📁 Estrutura de saída

```
📂 imbox/                          ← diretório de trabalho
├── 🎬 titulo_do_video.mp4         ← vídeo original
├── 🎵 titulo_do_video.mp3         ← áudio extraído
├── 🔊 titulo_do_video.wav         ← convertido 16 kHz mono
├── 📄 output.srt                  ← transcrição original (SRT)
├── 📄 output.json                 ← transcrição word-level
└── 📂 output_pt/                  ← conteúdo traduzido
    ├── 📄 output.srt              ← legendas traduzidas
    └── 📄 output.json             ← segmentos traduzidos

📂 output/                         ← resultado final
└── 🎬 titulo_do_video_final.mp4   ← vídeo dublado
```

---

## ⚙️ Configuração

`src/configs.py` expõe todas as variáveis ajustáveis:

| Variável | Tipo | Padrão | Descrição |
|---|---|---|---|
| `MODEL` | `Path` | `models/vosk-model-small-en-us-0.15` | Modelo de transcrição Vosk |
| `MODEL_TTS` | `Path` | `models/tts/pt_BR-faber-medium.onnx` | Voz Piper TTS |
| `LANG_TRANSLATE` | `str` | `pt` | Idioma alvo da tradução (código ISO) |
| `DATA` | `Path` | `imbox/` | Diretório de trabalho temporário |

---

## 🧰 Stack

| Tecnologia | Função | Licença |
|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Download de vídeo/áudio do YouTube | Unlicense |
| [Vosk](https://alphacephei.com/vosk/) | Speech-to-Text offline | Apache 2.0 |
| [Piper TTS](https://github.com/rhasspy/piper) | Text-to-Speech neural | MIT |
| [deep-translator](https://github.com/nidhaloff/deep-translator) | Tradução automática | MIT |
| [FFmpeg](https://ffmpeg.org/) | Processamento e mixagem de áudio/vídeo | LGPL/GPL |

---

## 🏗️ Estrutura do projeto

```
vidra/
├── main.py                 # Entry point da pipeline
├── install.sh              # Setup do .venv + download dos modelos
├── requirements.txt        # Dependências Python
├── assets/                 # Logos e recursos visuais
│   └── vidra.png
├── src/
│   ├── configs.py          # Paths e constantes
│   ├── core/
│   │   ├── input.py        # Download via yt-dlp
│   │   ├── audio_manager.py# Transcrição, dublagem, TTS
│   │   └── translate.py    # Interface com GoogleTranslator
│   └── utils/
│       ├── colors.py       # Output colorido no terminal
│       └── logger.py       # Logging (console + arquivo)
└── models/                 # (baixado pelo install.sh)
    ├── tts/
    │   ├── pt_BR-faber-medium.onnx
    │   └── pt_BR-faber-medium.onnx.json
    ├── vosk-model-small-en-us-0.15/
    └── vosk-model-small-pt-0.3/
```

---

## 🧪 Fluxo técnico

1. **Download** — `yt-dlp` baixa o vídeo em MP4 e o áudio em MP3 (192 kbps)
2. **Conversão** — `ffmpeg` converte o MP3 para WAV mono 16 kHz (formato exigido pelo Vosk)
3. **Transcrição** — Vosk reconhece a fala com timestamps word-level; o algoritmo de agrupamento une palavras em segmentos por pausa (>0.3s) ou tamanho máximo (25 palavras)
4. **Tradução** — `deep-translator` (GoogleTranslator) traduz cada segmento para PT-BR preservando os timestamps originais
5. **TTS** — Piper gera um arquivo WAV para cada segmento traduzido usando a voz *Faber* PT-BR
6. **Dublagem** — Os WAVs gerados substituem as falas originais no áudio nos timestamps exatos; TTS mais curto vira silêncio, TTS mais longo é truncado
7. **Merge** — O áudio dublado é mesclado ao vídeo original sem re-encode (`-c:v copy`)

---

## 📄 Licença

MIT © 2026 — sinta-se livre para usar, modificar e distribuir.

---

<div align="center">
  <sub>Feito com ☕ e Python</sub>
</div>
