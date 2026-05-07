import os
import psutil
from pathlib import Path

MODEL_DIR = Path(os.environ.get("JARVIS_MODEL_DIR", str(Path.home() / "jarvis_models")))

def get_available_ram_gb() -> float:
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)

def select_model() -> dict:
    ram = get_available_ram_gb()
    if ram < 4:
        return {
            "name": "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",
            "hf_repo": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
            "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            "ram_required": 1.5,
        }
    elif ram < 8:
        return {
            "name": "Mistral-7B-Instruct-v0.2.Q4_K_M.gguf",
            "hf_repo": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "ram_required": 5.5,
        }
    else:
        return {
            "name": "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
            "hf_repo": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
            "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
            "ram_required": 6.5,
        }

_llm = None

def load_model() -> bool:
    global _llm
    try:
        from llama_cpp import Llama
    except ImportError:
        return False

    model_info = select_model()
    model_path = MODEL_DIR / model_info["name"]

    if not model_path.exists():
        return False

    ram = get_available_ram_gb()
    n_ctx = 2048 if ram < 4 else 4096

    _llm = Llama(
        model_path=str(model_path),
        n_ctx=n_ctx,
        n_threads=max(2, os.cpu_count() - 1),
        n_gpu_layers=0,
        verbose=False,
    )
    return True

def chat(user_message: str, system_prompt: str = None) -> str:
    global _llm
    if _llm is None:
        if not load_model():
            return "[Мозг не загружен] Модель не найдена. Запусти /setup чтобы скачать модель."

    if system_prompt is None:
        system_prompt = (
            "Ты Jarvis — автономный AI-ассистент на телефоне пользователя. "
            "Отвечай кратко, по делу, на языке пользователя. "
            "Ты можешь запускать команды, скачивать файлы, управлять телефоном."
        )

    prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_message} [/INST]"

    output = _llm(
        prompt,
        max_tokens=1024,
        stop=["</s>", "[INST]"],
        echo=False,
    )
    return output["choices"][0]["text"].strip()

def get_status() -> dict:
    model_info = select_model()
    model_path = MODEL_DIR / model_info["name"]
    return {
        "ram_gb": round(get_available_ram_gb(), 2),
        "model_name": model_info["name"],
        "model_loaded": _llm is not None,
        "model_exists": model_path.exists(),
        "model_path": str(model_path),
    }
