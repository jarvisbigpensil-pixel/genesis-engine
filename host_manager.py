"""
Genesis Engine — Host Manager
Запускает и управляет ботами/серверами прямо с телефона.
"""
import subprocess
import os
import signal
import json
from pathlib import Path

PROCESSES_FILE = Path.home() / ".genesis_processes.json"
_processes: dict = {}


def _load_processes():
    global _processes
    if PROCESSES_FILE.exists():
        try:
            _processes = json.loads(PROCESSES_FILE.read_text())
        except Exception:
            _processes = {}


def _save_processes():
    PROCESSES_FILE.write_text(json.dumps(_processes, indent=2))


def start_service(name: str, command: str, cwd: str = None) -> dict:
    """Запускает сервис в фоне."""
    try:
        proc = subprocess.Popen(
            command, shell=True, cwd=cwd,
            stdout=open(Path.home() / f".genesis_{name}.log", "w"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        _load_processes()
        _processes[name] = {"pid": proc.pid, "command": command, "cwd": cwd}
        _save_processes()
        return {"success": True, "pid": proc.pid, "name": name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_service(name: str) -> dict:
    """Останавливает сервис по имени."""
    _load_processes()
    info = _processes.get(name)
    if not info:
        return {"success": False, "error": f"Сервис {name} не найден"}
    try:
        os.killpg(os.getpgid(info["pid"]), signal.SIGTERM)
        del _processes[name]
        _save_processes()
        return {"success": True, "stopped": name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_services() -> dict:
    """Список запущенных сервисов."""
    _load_processes()
    result = {}
    for name, info in _processes.items():
        try:
            os.kill(info["pid"], 0)
            result[name] = {"pid": info["pid"], "status": "running", "command": info["command"]}
        except ProcessLookupError:
            result[name] = {"pid": info["pid"], "status": "stopped", "command": info["command"]}
    return result


def get_log(name: str, lines: int = 30) -> str:
    """Последние строки лога сервиса."""
    log_path = Path.home() / f".genesis_{name}.log"
    if not log_path.exists():
        return f"Лог для {name} не найден"
    content = log_path.read_text(errors="replace").splitlines()
    return "\n".join(content[-lines:])
