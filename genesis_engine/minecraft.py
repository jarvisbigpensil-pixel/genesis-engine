"""
Genesis Engine v1.1 — Minecraft Module
Полная установка и управление Minecraft сервером в Termux.
"""

import os
import subprocess
import json
import requests
from pathlib import Path

MC_DIR = Path(os.environ.get("JARVIS_DOWNLOAD_DIR", str(Path.home() / "jarvis_downloads"))) / "minecraft"
MC_DIR.mkdir(parents=True, exist_ok=True)

VERSIONS_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest.json"


def get_latest_version() -> dict:
    try:
        r = requests.get(VERSIONS_MANIFEST, timeout=10)
        data = r.json()
        latest = data["latest"]["release"]
        return {"success": True, "version": latest}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_server_jar(version: str = None) -> dict:
    try:
        manifest = requests.get(VERSIONS_MANIFEST, timeout=10).json()
        if version is None:
            version = manifest["latest"]["release"]

        version_url = None
        for v in manifest["versions"]:
            if v["id"] == version:
                version_url = v["url"]
                break
        if not version_url:
            return {"success": False, "error": f"Версия {version} не найдена"}

        version_data = requests.get(version_url, timeout=10).json()
        server_url = version_data["downloads"]["server"]["url"]
        server_sha1 = version_data["downloads"]["server"]["sha1"]

        jar_path = MC_DIR / f"server-{version}.jar"
        if jar_path.exists():
            return {"success": True, "path": str(jar_path), "version": version, "cached": True}

        r = requests.get(server_url, stream=True, timeout=60)
        with open(jar_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        return {"success": True, "path": str(jar_path), "version": version, "cached": False}
    except Exception as e:
        return {"success": False, "error": str(e)}


def setup_server(version: str = None, ram_mb: int = 512) -> dict:
    try:
        jar_result = download_server_jar(version)
        if not jar_result["success"]:
            return jar_result

        jar_path = Path(jar_result["path"])
        server_dir = MC_DIR / "server"
        server_dir.mkdir(parents=True, exist_ok=True)

        if not (server_dir / jar_path.name).exists():
            import shutil
            shutil.copy(jar_path, server_dir / jar_path.name)

        (server_dir / "eula.txt").write_text("eula=true\n")

        props = {
            "server-port": "25565",
            "max-players": "5",
            "gamemode": "survival",
            "difficulty": "normal",
            "level-name": "world",
            "motd": "Genesis Engine Minecraft Server",
            "online-mode": "false",
            "view-distance": "6",
            "simulation-distance": "4",
            "max-tick-time": "60000",
        }
        props_content = "\n".join(f"{k}={v}" for k, v in props.items())
        (server_dir / "server.properties").write_text(props_content)

        start_script = (
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            f"cd {server_dir}\n"
            f"java -Xmx{ram_mb}M -Xms{ram_mb // 2}M "
            f"-jar {jar_path.name} nogui\n"
        )
        start_path = server_dir / "start.sh"
        start_path.write_text(start_script)
        start_path.chmod(0o755)

        return {
            "success": True,
            "server_dir": str(server_dir),
            "jar": jar_path.name,
            "version": jar_result["version"],
            "start_cmd": f"bash {start_path}",
            "port": 25565,
            "ram_mb": ram_mb,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_server_status() -> dict:
    result = subprocess.run(
        ["pgrep", "-f", "minecraft"],
        capture_output=True, text=True
    )
    running = result.returncode == 0
    server_dir = MC_DIR / "server"
    jar_exists = any(server_dir.glob("*.jar")) if server_dir.exists() else False
    return {
        "running": running,
        "installed": jar_exists,
        "server_dir": str(server_dir),
    }


def start_server() -> dict:
    start_sh = MC_DIR / "server" / "start.sh"
    if not start_sh.exists():
        return {"success": False, "error": "Сервер не установлен. Запусти /mc_setup"}
    try:
        proc = subprocess.Popen(
            ["bash", str(start_sh)],
            stdout=open(MC_DIR / "server.log", "w"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        return {"success": True, "pid": proc.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_server() -> dict:
    result = subprocess.run(
        ["pkill", "-f", "minecraft"],
        capture_output=True, text=True
    )
    return {"success": result.returncode == 0}


def get_server_log(lines: int = 20) -> str:
    log_path = MC_DIR / "server.log"
    if not log_path.exists():
        return "Лог пуст — сервер ещё не запускался."
    content = log_path.read_text(errors="replace").splitlines()
    return "\n".join(content[-lines:])


def generate_setup_script(version: str = "latest", ram_mb: int = 512) -> str:
    return f"""#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════╗
# ║  Genesis Engine v1.1 — Minecraft Installer  ║
# ╚══════════════════════════════════════════════╝
set -e
GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'; RED='\\033[0;31m'; NC='\\033[0m'
log()  {{ echo -e "${{GREEN}}[✓] $1${{NC}}"; }}
warn() {{ echo -e "${{YELLOW}}[!] $1${{NC}}"; }}
fail() {{ echo -e "${{RED}}[✗] $1${{NC}}"; exit 1; }}

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Genesis Engine — Minecraft Server     ║"
echo "╚════════════════════════════════════════╝"
echo ""

# ── Устанавливаем Java ──────────────────────────────
log "Устанавливаю Java..."
pkg install -y openjdk-21 || pkg install -y openjdk-17 || fail "Не удалось установить Java"

JAVA_VER=$(java -version 2>&1 | head -1)
log "Java: $JAVA_VER"

# ── Создаём папку сервера ───────────────────────────
MC_DIR="$HOME/jarvis_downloads/minecraft"
SERVER_DIR="$MC_DIR/server"
mkdir -p "$SERVER_DIR"
cd "$SERVER_DIR"

# ── Скачиваем сервер ────────────────────────────────
VERSION="{version}"
if [ "$VERSION" = "latest" ]; then
    log "Получаю последнюю версию Minecraft..."
    MANIFEST=$(curl -s https://launchermeta.mojang.com/mc/game/version_manifest.json)
    VERSION=$(echo "$MANIFEST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['latest']['release'])")
fi

log "Версия Minecraft: $VERSION"

VERSION_URL=$(curl -s https://launchermeta.mojang.com/mc/game/version_manifest.json | \\
    python3 -c "import sys,json; d=json.load(sys.stdin); print([v['url'] for v in d['versions'] if v['id']=='$VERSION'][0])")

SERVER_URL=$(curl -s "$VERSION_URL" | \\
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d['downloads']['server']['url'])")

log "Скачиваю server.jar (~40 MB)..."
curl -L --progress-bar -o "server-$VERSION.jar" "$SERVER_URL"

# ── Принимаем EULA ──────────────────────────────────
echo "eula=true" > eula.txt
log "EULA принята"

# ── server.properties ───────────────────────────────
cat > server.properties << 'EOF'
server-port=25565
max-players=5
gamemode=survival
difficulty=normal
level-name=world
motd=Genesis Engine Minecraft Server
online-mode=false
view-distance=6
simulation-distance=4
max-tick-time=60000
EOF
log "server.properties создан"

# ── Скрипт запуска ──────────────────────────────────
cat > start.sh << EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$SERVER_DIR"
java -Xmx{ram_mb}M -Xms{ram_mb // 2}M -jar server-$VERSION.jar nogui
EOF
chmod +x start.sh

# ── Скрипт подключения (mcrcon) ─────────────────────
log "Устанавливаю mcrcon для управления сервером..."
pip install mcrcon 2>/dev/null || warn "mcrcon не установлен (опционально)"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║       УСТАНОВКА ЗАВЕРШЕНА! 🎮          ║"
echo "╚════════════════════════════════════════╝"
echo ""
log "Запусти сервер:"
echo "    bash $SERVER_DIR/start.sh"
echo ""
warn "RAM для сервера: {ram_mb} MB"
warn "Порт: 25565"
warn "Для подключения с телефона: localhost:25565"
warn "Для подключения извне — нужен ngrok или Tailscale"
echo ""
"""
