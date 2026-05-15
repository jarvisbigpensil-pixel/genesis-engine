import os
import subprocess
import tempfile
import asyncio
from pathlib import Path
import requests

DOWNLOAD_DIR = Path(os.environ.get("JARVIS_DOWNLOAD_DIR", str(Path.home() / "jarvis_downloads")))
SCRIPTS_DIR = Path(os.environ.get("JARVIS_SCRIPTS_DIR", str(Path.home() / "jarvis_scripts")))

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Download Manager ──────────────────────────────────────────────────────────

def download_file(url: str, filename: str = None) -> dict:
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        if filename is None:
            filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
        dest = DOWNLOAD_DIR / filename
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
        return {"success": True, "path": str(dest), "size_mb": round(downloaded / 1024 / 1024, 2)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_media(url: str) -> dict:
    try:
        import yt_dlp
        dest = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")
        ydl_opts = {
            "outtmpl": dest,
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return {"success": True, "path": filename, "title": info.get("title", "unknown")}
    except ImportError:
        return {"success": False, "error": "yt-dlp не установлен. Запусти: pip install yt-dlp"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def clone_github(repo_url: str) -> dict:
    try:
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        dest = DOWNLOAD_DIR / repo_name
        result = subprocess.run(
            ["git", "clone", repo_url, str(dest)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return {"success": True, "path": str(dest), "repo": repo_name}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Code Runner ───────────────────────────────────────────────────────────────

def save_and_run_script(code: str, script_name: str = None) -> dict:
    if script_name is None:
        import time
        script_name = f"script_{int(time.time())}.py"
    if not script_name.endswith(".py"):
        script_name += ".py"
    path = SCRIPTS_DIR / script_name
    path.write_text(code, encoding="utf-8")
    try:
        result = subprocess.run(
            ["python", str(path)],
            capture_output=True, text=True, timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
            "path": str(path),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Скрипт выполнялся больше 30 секунд и был остановлен.", "path": str(path)}
    except Exception as e:
        return {"success": False, "error": str(e), "path": str(path)}


def run_shell(command: str) -> dict:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Команда выполнялась больше 30 секунд."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Termux:API — System Access ────────────────────────────────────────────────

def termux_api(command: list) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return {"success": result.returncode == 0, "output": result.stdout.strip(), "error": result.stderr.strip()}
    except FileNotFoundError:
        return {"success": False, "error": "termux-api не установлен. Запусти: pkg install termux-api"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_battery() -> dict:
    import json
    result = termux_api(["termux-battery-status"])
    if result["success"] and result["output"]:
        try:
            data = json.loads(result["output"])
            return {
                "success": True,
                "percentage": data.get("percentage", "?"),
                "status": data.get("status", "?"),
                "temperature": data.get("temperature", "?"),
            }
        except Exception:
            pass
    return result


def torch_flashlight(state: bool) -> dict:
    value = "on" if state else "off"
    return termux_api(["termux-torch", value])


def send_sms(number: str, message: str) -> dict:
    return termux_api(["termux-sms-send", "-n", number, message])


async def speak(text: str, voice: str = "ru-RU-SvetlanaNeural") -> dict:
    try:
        import edge_tts
        out_path = str(DOWNLOAD_DIR / "tts_output.mp3")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)
        subprocess.Popen(["termux-media-player", "play", out_path])
        return {"success": True, "path": out_path}
    except ImportError:
        return {"success": False, "error": "edge-tts не установлен. Запусти: pip install edge-tts"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_device_info() -> dict:
    import platform
    import psutil
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "platform": platform.system(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_total_gb": round(mem.total / 1024 ** 3, 2),
        "ram_available_gb": round(mem.available / 1024 ** 3, 2),
        "disk_total_gb": round(disk.total / 1024 ** 3, 2),
        "disk_free_gb": round(disk.free / 1024 ** 3, 2),
    }
