#!/data/data/com.termux/files/usr/bin/bash
# Genesis Engine v1.1 — Minecraft Server Installer
set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }
fail() { echo -e "${RED}[✗] $1${NC}"; exit 1; }

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Genesis Engine v1.1 — Minecraft 🎮   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Определяем доступную RAM
RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
RAM_MB=$(( RAM_KB / 1024 ))
SERVER_RAM=$(( RAM_MB / 3 ))
[ "$SERVER_RAM" -lt 256 ] && SERVER_RAM=256
[ "$SERVER_RAM" -gt 1024 ] && SERVER_RAM=1024
warn "Доступная RAM: ${RAM_MB} MB, для сервера: ${SERVER_RAM} MB"

# Устанавливаем Java
log "Устанавливаю Java..."
pkg install -y openjdk-21 2>/dev/null || pkg install -y openjdk-17 || fail "Java не установлена"
log "Java: $(java -version 2>&1 | head -1)"

# Создаём папку
MC_DIR="$HOME/jarvis_downloads/minecraft/server"
mkdir -p "$MC_DIR" && cd "$MC_DIR"

# Получаем последнюю версию
log "Получаю последнюю версию Minecraft..."
MANIFEST=$(curl -s https://launchermeta.mojang.com/mc/game/version_manifest.json)
MC_VERSION=$(echo "$MANIFEST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['latest']['release'])")
log "Версия: $MC_VERSION"

VERSION_URL=$(echo "$MANIFEST" | python3 -c "import sys,json; d=json.load(sys.stdin); print([v['url'] for v in d['versions'] if v['id']=='$MC_VERSION'][0])")
SERVER_URL=$(curl -s "$VERSION_URL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['downloads']['server']['url'])")

log "Скачиваю server.jar (~45 MB)..."
curl -L --progress-bar -o "server-${MC_VERSION}.jar" "$SERVER_URL"

# Принимаем EULA
echo "eula=true" > eula.txt

# server.properties
cat > server.properties << 'EOF'
server-port=25565
max-players=5
gamemode=survival
difficulty=normal
level-name=world
motd=§aGenesis Engine §6Minecraft Server
online-mode=false
view-distance=6
simulation-distance=4
max-tick-time=60000
EOF

# Скрипт запуска
cat > start.sh << EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$MC_DIR"
java -Xmx${SERVER_RAM}M -Xms$((SERVER_RAM/2))M -jar server-${MC_VERSION}.jar nogui
EOF
chmod +x start.sh

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Minecraft Server готов! 🎮         ║"
echo "╚════════════════════════════════════════╝"
echo ""
log "Запусти сервер: bash $MC_DIR/start.sh"
warn "Подключение: localhost:25565 (с этого же телефона)"
warn "Для игры извне — установи Tailscale или ngrok"
echo ""
