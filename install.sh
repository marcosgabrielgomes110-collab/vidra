#!/bin/bash

# ======================================
# VIDRA SETUP — .venv + modelos
# ======================================
# Uso: bash install.sh
# Requer: python3, wget, unzip
# ======================================

set -euo pipefail

PROJECT_DIR=$(pwd)
MODELS_DIR="$PROJECT_DIR/models"
TTS_DIR="$MODELS_DIR/tts"

# ======================================
# PYTHON VENV + LIBS
# ======================================

echo '🐍 Criando ambiente virtual...'
python3 -m venv .venv
source .venv/bin/activate

echo '📚 Instalando bibliotecas Python...'
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install piper-tts -q

# ======================================
# MODELOS VOSK
# ======================================

echo '🧠 Baixando modelos Vosk...'
mkdir -p "$MODELS_DIR"

dl_vosk() {
  local name=$1 url=$2
  local target="$MODELS_DIR/$name"
  local zip_path="$MODELS_DIR/$name.zip"
  [[ -d "$target" ]] && { echo "  ✔ $name já existe"; return; }
  wget -q --show-progress -O "$zip_path" "$url"
  unzip -qo "$zip_path" -d "$MODELS_DIR"
  rm "$zip_path"
}

dl_vosk 'vosk-model-small-en-us-0.15' \
  'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'

dl_vosk 'vosk-model-small-pt-0.3' \
  'https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip'

# ======================================
# MODELO PIPER TTS (PT-BR)
# ======================================

echo '🎤 Baixando voz Piper PT-BR...'
mkdir -p "$TTS_DIR"

dl_piper() {
  local file=$1 url=$2
  [[ -f "$TTS_DIR/$file" ]] && { echo "  ✔ $file já existe"; return; }
  wget -q --show-progress -O "$TTS_DIR/$file" "$url"
}

dl_piper 'pt_BR-faber-medium.onnx' \
  'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx'

dl_piper 'pt_BR-faber-medium.onnx.json' \
  'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json'

# ======================================
# IMBOX
# ======================================

mkdir -p "$PROJECT_DIR/imbox"

# ======================================
# FINISH
# ======================================

echo ''
echo '✅ VIDRA pronto'
echo ''
echo '📁 models/'
echo '  ├── tts/'
echo '  │   ├── pt_BR-faber-medium.onnx'
echo '  │   └── pt_BR-faber-medium.onnx.json'
echo '  ├── vosk-model-small-en-us-0.15/'
echo '  └── vosk-model-small-pt-0.3/'
echo ''
echo '🚀  source .venv/bin/activate'
echo '    python main.py'
