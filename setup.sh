#!/data/data/com.termux/files/usr/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }
fail() { echo -e "${RED}[✗] $1${NC}"; exit 1; }
info() { echo -e "${BLUE}[→] $1${NC}"; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     GENESIS ENGINE — SETUP v1.1     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── ПРОВЕРКА 1: Termux не должен быть на SD карте ────────────────────────────
info "Проверяю расположение Termux..."
if [[ "$HOME" == *"/storage/"* ]] || [[ "$HOME" == *"/sdcard/"* ]]; then
    fail "Termux установлен на SD карту! Перенеси его во внутреннюю память и переустанови."
fi
log "Termux в правильном месте: $HOME"

# ── ПРОВЕРКА 2: Свободное место ───────────────────────────────────────────────
info "Проверяю свободное место..."
FREE_MB=$(df "$HOME" | awk 'NR==2 {print int($4/1024)}')
log "Свободно: ${FREE_MB} MB"
if [ "$FREE_MB" -lt 2000 ]; then
    warn "Мало места: ${FREE_MB} MB. Нужно минимум 2000 MB."
    warn "Удали ненужные файлы и запусти снова."
    warn "Продолжаю, но могут быть ошибки..."
fi

# ── ПРОВЕРКА 3: Интернет ──────────────────────────────────────────────────────
info "Проверяю интернет..."
if ! curl -s --max-time 5 https://google.com > /dev/null; then
    fail "Нет интернета! Подключись к Wi-Fi и запусти снова."
fi
log "Интернет работает"

# ── RAM ───────────────────────────────────────────────────────────────────────
RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
RAM_MB=$(( RAM_KB / 1024 ))
RAM_GB=$(echo "scale=1; $RAM_KB / 1024 / 1024" | bc)
ARCH=$(uname -m)
log "RAM доступно: ${RAM_GB} GB | Архитектура: $ARCH"

# ── ВЫБОР МОДЕЛИ ──────────────────────────────────────────────────────────────
if (( $(echo "$RAM_GB < 3" | bc -l) )); then
    MODEL_NAME="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    MODEL_SIZE="~700 MB"
elif (( $(echo "$RAM_GB < 8" | bc -l) )); then
    MODEL_NAME="mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    MODEL_URL="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    MODEL_SIZE="~4.4 GB"
else
    MODEL_NAME="Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
    MODEL_URL="https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
    MODEL_SIZE="~4.9 GB"
fi
log "Выбрана модель: $MODEL_NAME ($MODEL_SIZE)"

# ── ШАГ 1: Базовые пакеты (по одному, с retry) ───────────────────────────────
echo ""
info "ШАГ 1/5: Установка базовых пакетов..."
pkg update -y 2>/dev/null || warn "pkg update завершился с ошибкой, продолжаю..."

install_pkg() {
    local PKG=$1
    for attempt in 1 2 3; do
        if pkg install -y "$PKG" 2>/dev/null; then
            log "  $PKG — OK"
            return 0
        else
            warn "  $PKG — попытка $attempt/3 не удалась, повторяю..."
            sleep 2
        fi
    done
    warn "  $PKG — пропущен (не критично)"
}

install_pkg python
install_pkg python-pip
install_pkg git
install_pkg curl
install_pkg wget
install_pkg ffmpeg
install_pkg termux-api
install_pkg libopenblas
install_pkg make

# clang/cmake/ninja — нужны только для компиляции, ставим опционально
install_pkg clang
install_pkg cmake
install_pkg ninja

# ── ШАГ 2: Python пакеты ──────────────────────────────────────────────────────
echo ""
info "ШАГ 2/5: Установка Python пакетов..."
pip install --upgrade pip --quiet

install_py() {
    local PKG=$1
    if pip install "$PKG" --quiet 2>/dev/null; then
        log "  $PKG — OK"
    else
        warn "  $PKG — ошибка установки, пропускаю"
    fi
}

install_py aiogram
install_py psutil
install_py requests
install_py yt-dlp
install_py edge-tts
install_py python-dotenv
install_py midiutil
install_py g4f

# ── ШАГ 3: llama-cpp-python (умная установка) ────────────────────────────────
echo ""
info "ШАГ 3/5: Установка llama-cpp-python..."
warn "Сначала пробую готовый wheel (быстро, без компиляции LLVM)..."

LLAMA_OK=false

# Метод 1: готовый wheel для CPU (не требует LLVM)
if pip install llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    --quiet 2>/dev/null; then
    log "llama-cpp-python установлен (pre-built wheel) ✓"
    LLAMA_OK=true
fi

# Метод 2: pip install без компиляции через FORCE_CMAKE=0
if [ "$LLAMA_OK" = false ]; then
    warn "Pre-built wheel не подошёл, пробую метод 2..."
    if FORCE_CMAKE=0 pip install llama-cpp-python --quiet 2>/dev/null; then
        log "llama-cpp-python установлен (метод 2) ✓"
        LLAMA_OK=true
    fi
fi

# Метод 3: полная компиляция (долго, ~20 минут, нужен LLVM)
if [ "$LLAMA_OK" = false ]; then
    warn "Пробую полную компиляцию (нужен LLVM ~30 MB, займёт 10-20 мин)..."
    warn "Не закрывай Termux!"
    export CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
    export FORCE_CMAKE=1
    if pip install llama-cpp-python --no-cache-dir 2>/dev/null; then
        log "llama-cpp-python скомпилирован ✓"
        LLAMA_OK=true
    else
        warn "llama-cpp-python не установлен — AI офлайн недоступен."
        warn "Бот будет работать через g4f (интернет)."
    fi
fi

# ── ШАГ 4: Скачиваем AI модель ───────────────────────────────────────────────
echo ""
info "ШАГ 4/5: Скачивание AI модели..."
MODEL_DIR="$HOME/jarvis_models"
mkdir -p "$MODEL_DIR"
MODEL_PATH="$MODEL_DIR/$MODEL_NAME"

if [ -f "$MODEL_PATH" ]; then
    ACTUAL_SIZE=$(du -m "$MODEL_PATH" | cut -f1)
    log "Модель уже есть: $MODEL_NAME (${ACTUAL_SIZE} MB) — пропускаю"
else
    log "Скачиваю: $MODEL_NAME ($MODEL_SIZE)"
    warn "Используй Wi-Fi! Не закрывай Termux!"
    warn "Если прервётся — запусти setup.sh снова, скачивание продолжится с места остановки"
    echo ""
    # curl -C - = возобновить скачивание если прервалось
    if curl -L -C - --progress-bar \
        --retry 5 --retry-delay 3 \
        --connect-timeout 30 \
        -o "$MODEL_PATH" "$MODEL_URL"; then
        log "Модель скачана: $MODEL_PATH"
    else
        warn "Ошибка скачивания модели."
        warn "Попробуй запустить setup.sh снова — скачивание продолжится."
        rm -f "$MODEL_PATH"
    fi
fi

# ── ШАГ 5: Конфиг и автозапуск ───────────────────────────────────────────────
echo ""
info "ШАГ 5/5: Настройка..."
JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$JARVIS_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << ENVEOF
# Genesis Engine — конфигурация
JARVIS_BOT_TOKEN=вставь_токен_от_BotFather
JARVIS_OWNER_ID=вставь_свой_telegram_id
JARVIS_MODEL_DIR=$MODEL_DIR
JARVIS_DOWNLOAD_DIR=$HOME/jarvis_downloads
JARVIS_SCRIPTS_DIR=$HOME/jarvis_scripts
ENVEOF
    warn ".env создан — нужно заполнить токен и ID"
else
    log ".env уже существует"
fi

# Папки
mkdir -p "$HOME/jarvis_downloads" "$HOME/jarvis_scripts" "$HOME/jarvis_downloads/minecraft"

# Автозапуск
BOOT_DIR="$HOME/.termux/boot"
mkdir -p "$BOOT_DIR"
cat > "$BOOT_DIR/jarvis.sh" << BOOTEOF
#!/data/data/com.termux/files/usr/bin/bash
source $JARVIS_DIR/.env
export \$(grep -v '^#' $JARVIS_DIR/.env | xargs)
cd $JARVIS_DIR
python bot.py >> $HOME/jarvis.log 2>&1 &
BOOTEOF
chmod +x "$BOOT_DIR/jarvis.sh"
log "Автозапуск настроен"

# ── ИТОГ ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║            УСТАНОВКА ЗАВЕРШЕНА! ✓                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Следующие шаги:"
echo ""
log "1. Заполни токен бота:"
echo "      nano $ENV_FILE"
echo ""
log "2. Создай бота → @BotFather в Telegram"
log "   Узнай свой ID → @userinfobot"
echo ""
log "3. Запусти Jarvis:"
echo "      bash $JARVIS_DIR/start.sh"
echo ""
if [ "$LLAMA_OK" = false ]; then
    warn "ВНИМАНИЕ: llama-cpp-python не установлен."
    warn "AI будет работать через интернет (g4f)."
    warn "Для офлайн AI запусти: pip install llama-cpp-python"
    echo ""
fi
warn "Для автозапуска при включении телефона:"
warn "Установи 'Termux:Boot' из F-Droid"
echo ""
