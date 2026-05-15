#!/data/data/com.termux/files/usr/bin/bash
# Genesis Engine — быстрый запуск
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Файл .env не найден!"
    echo "Скопируй: cp .env.example .env && nano .env"
    exit 1
fi

export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)

cd "$SCRIPT_DIR"
echo "Запускаю Genesis Engine..."
python bot.py
