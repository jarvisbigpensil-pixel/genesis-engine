"""
Genesis Engine — Music Generator
Генерирует музыку через MusicGen (Meta AI) офлайн.
Требует: pip install audiocraft torch torchaudio
Размер модели: ~300 MB (small)
"""
import subprocess
import os
from pathlib import Path

MUSIC_DIR = Path(os.environ.get("JARVIS_DOWNLOAD_DIR", str(Path.home() / "jarvis_downloads")))


def generate_music(prompt: str, duration: int = 15) -> dict:
    """Генерирует музыку по описанию. duration — секунды (макс 30 офлайн)."""
    try:
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write

        model = MusicGen.get_pretrained("facebook/musicgen-small")
        model.set_generation_params(duration=min(duration, 30))
        wav = model.generate([prompt])

        out_path = MUSIC_DIR / "generated_music"
        audio_write(str(out_path), wav[0].cpu(), model.sample_rate, strategy="loudness")
        final_path = str(out_path) + ".wav"
        return {"success": True, "path": final_path}
    except ImportError:
        return {
            "success": False,
            "error": (
                "audiocraft не установлен.\n"
                "Установи: pip install audiocraft torch torchaudio\n"
                "Размер загрузки: ~2 GB"
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_music_simple(prompt: str, bpm: int = 120, duration: int = 10) -> dict:
    """
    Простая генерация MIDI без нейросети (работает офлайн без доп. загрузок).
    Требует: pip install midiutil
    """
    try:
        from midiutil import MIDIFile
        import random

        scales = {
            "happy": [60, 62, 64, 65, 67, 69, 71, 72],
            "sad": [60, 62, 63, 65, 67, 68, 70, 72],
            "epic": [60, 63, 65, 66, 67, 70, 72, 75],
        }
        mood = "happy"
        for word in ["грустн", "sad", "темн", "dark"]:
            if word in prompt.lower():
                mood = "sad"
                break
        for word in ["эпич", "epic", "мощн", "power", "battle"]:
            if word in prompt.lower():
                mood = "epic"
                break

        scale = scales[mood]
        midi = MIDIFile(1)
        track, channel = 0, 0
        midi.addTempo(track, 0, bpm)

        beat_duration = 60.0 / bpm
        total_beats = int(duration / beat_duration)

        for i in range(total_beats):
            pitch = random.choice(scale)
            dur = random.choice([0.5, 1.0, 1.5])
            midi.addNote(track, channel, pitch, i, dur, random.randint(70, 100))

        out_path = MUSIC_DIR / "generated_midi.mid"
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            midi.writeFile(f)
        return {"success": True, "path": str(out_path), "mode": "midi"}
    except ImportError:
        return {"success": False, "error": "midiutil не установлен. pip install midiutil"}
    except Exception as e:
        return {"success": False, "error": str(e)}
