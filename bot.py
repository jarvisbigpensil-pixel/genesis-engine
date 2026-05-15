import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.utils.markdown import hcode, hbold

import brain
import tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("jarvis")

BOT_TOKEN = os.environ.get("JARVIS_BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("JARVIS_OWNER_ID", "0"))

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()


def is_owner(message: Message) -> bool:
    return OWNER_ID == 0 or message.from_user.id == OWNER_ID


# ── /start ────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not is_owner(message):
        return
    status = brain.get_status()
    model_status = "✅ загружена" if status["model_exists"] else "❌ не скачана (запусти /setup)"
    await message.answer(
        f"⚡ <b>Jarvis Online</b>\n\n"
        f"🧠 Модель: {status['model_name']}\n"
        f"💾 RAM доступно: {status['ram_gb']} GB\n"
        f"📦 Модель: {model_status}\n\n"
        f"<b>Команды:</b>\n"
        f"/help — список всех команд\n"
        f"/status — состояние системы\n"
        f"/setup — установить и скачать модель\n"
        f"Просто напиши мне что угодно — я отвечу 🤖"
    )


# ── /help ─────────────────────────────────────────────────────────────────────

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_owner(message):
        return
    await message.answer(
        f"⚡ <b>Команды Jarvis</b>\n\n"
        f"🧠 <b>AI</b>\n"
        f"Просто напиши — AI ответит\n\n"
        f"💻 <b>Код</b>\n"
        f"/run <code>код</code> — выполнить Python\n"
        f"/shell <code>команда</code> — выполнить bash\n\n"
        f"⬇️ <b>Загрузки</b>\n"
        f"/download <code>URL</code> — скачать файл\n"
        f"/media <code>URL</code> — скачать видео/аудио\n"
        f"/github <code>URL</code> — клонировать репо\n\n"
        f"📱 <b>Телефон</b>\n"
        f"/battery — уровень заряда\n"
        f"/torch on|off — фонарик\n"
        f"/sms <code>номер текст</code> — отправить SMS\n"
        f"/speak <code>текст</code> — озвучить текст\n"
        f"/device — информация об устройстве\n\n"
        f"⚙️ <b>Система</b>\n"
        f"/status — состояние Jarvis\n"
        f"/setup — инструкция по установке"
    )


# ── /status ───────────────────────────────────────────────────────────────────

@dp.message(Command("status"))
async def cmd_status(message: Message):
    if not is_owner(message):
        return
    s = brain.get_status()
    d = tools.get_device_info()
    b = tools.get_battery()
    battery_str = f"{b.get('percentage', '?')}% ({b.get('status', '?')})" if b.get("success") else "недоступно"
    await message.answer(
        f"📊 <b>Статус Jarvis</b>\n\n"
        f"🧠 Модель: {s['model_name']}\n"
        f"⚡ Загружена: {'да' if s['model_loaded'] else 'нет'}\n"
        f"📦 Файл есть: {'да' if s['model_exists'] else 'нет'}\n\n"
        f"💾 RAM: {s['ram_gb']} GB свободно / {d['ram_total_gb']} GB всего\n"
        f"💽 Диск: {d['disk_free_gb']} GB свободно / {d['disk_total_gb']} GB всего\n"
        f"🔋 Батарея: {battery_str}\n"
        f"🖥 CPU ядер: {d['cpu_count']}\n"
        f"⚙️ Архитектура: {d['machine']}"
    )


# ── /setup ────────────────────────────────────────────────────────────────────

@dp.message(Command("setup"))
async def cmd_setup(message: Message):
    if not is_owner(message):
        return
    model = brain.select_model()
    await message.answer(
        f"⚙️ <b>Установка Jarvis</b>\n\n"
        f"Выбранная модель для твоего устройства:\n"
        f"📦 {hcode(model['name'])}\n\n"
        f"Запусти в Termux:\n"
        f"{hcode('bash setup.sh')}\n\n"
        f"Скрипт автоматически:\n"
        f"✅ Установит все зависимости\n"
        f"✅ Скомпилирует llama-cpp-python\n"
        f"✅ Скачает модель ({model['ram_required']} GB RAM нужно)\n"
        f"✅ Настроит автозапуск\n\n"
        f"URL модели:\n{hcode(model['url'])}"
    )


# ── /run — запустить Python-код ───────────────────────────────────────────────

@dp.message(Command("run"))
async def cmd_run(message: Message):
    if not is_owner(message):
        return
    code = message.text.removeprefix("/run").strip()
    if not code:
        await message.answer("Использование: /run <code>print('hello')</code>")
        return
    await message.answer("⚙️ Выполняю...")
    result = tools.save_and_run_script(code)
    parts = []
    if result.get("stdout"):
        parts.append(f"📤 <b>Вывод:</b>\n{hcode(result['stdout'])}")
    if result.get("stderr"):
        parts.append(f"⚠️ <b>Ошибки:</b>\n{hcode(result['stderr'])}")
    if not parts:
        parts.append("✅ Выполнено без вывода")
    parts.append(f"💾 Сохранён: {hcode(result['path'])}")
    await message.answer("\n\n".join(parts))


# ── /shell — bash команда ─────────────────────────────────────────────────────

@dp.message(Command("shell"))
async def cmd_shell(message: Message):
    if not is_owner(message):
        return
    command = message.text.removeprefix("/shell").strip()
    if not command:
        await message.answer("Использование: /shell <code>ls -la</code>")
        return
    await message.answer(f"⚙️ Выполняю: {hcode(command)}")
    result = tools.run_shell(command)
    output = result.get("stdout") or result.get("error") or "нет вывода"
    await message.answer(f"{'✅' if result['success'] else '❌'} {hcode(output)}")


# ── /download ─────────────────────────────────────────────────────────────────

@dp.message(Command("download"))
async def cmd_download(message: Message):
    if not is_owner(message):
        return
    url = message.text.removeprefix("/download").strip()
    if not url:
        await message.answer("Использование: /download <code>https://example.com/file.zip</code>")
        return
    msg = await message.answer("⬇️ Скачиваю...")
    result = tools.download_file(url)
    if result["success"]:
        await msg.edit_text(f"✅ Скачано!\n📁 {hcode(result['path'])}\n📦 {result['size_mb']} MB")
    else:
        await msg.edit_text(f"❌ Ошибка: {result['error']}")


# ── /media ────────────────────────────────────────────────────────────────────

@dp.message(Command("media"))
async def cmd_media(message: Message):
    if not is_owner(message):
        return
    url = message.text.removeprefix("/media").strip()
    if not url:
        await message.answer("Использование: /media <code>https://youtube.com/watch?v=...</code>")
        return
    msg = await message.answer("⬇️ Скачиваю медиа...")
    result = tools.download_media(url)
    if result["success"]:
        await msg.edit_text(f"✅ Скачано!\n🎵 {result['title']}\n📁 {hcode(result['path'])}")
    else:
        await msg.edit_text(f"❌ Ошибка: {result['error']}")


# ── /github ───────────────────────────────────────────────────────────────────

@dp.message(Command("github"))
async def cmd_github(message: Message):
    if not is_owner(message):
        return
    url = message.text.removeprefix("/github").strip()
    if not url:
        await message.answer("Использование: /github <code>https://github.com/user/repo</code>")
        return
    msg = await message.answer("📦 Клонирую репозиторий...")
    result = tools.clone_github(url)
    if result["success"]:
        await msg.edit_text(f"✅ Склонировано!\n📁 {hcode(result['path'])}")
    else:
        await msg.edit_text(f"❌ Ошибка: {result['error']}")


# ── /battery ──────────────────────────────────────────────────────────────────

@dp.message(Command("battery"))
async def cmd_battery(message: Message):
    if not is_owner(message):
        return
    result = tools.get_battery()
    if result.get("success"):
        pct = result.get("percentage", "?")
        status = result.get("status", "?")
        temp = result.get("temperature", "?")
        emoji = "🔋" if int(pct) > 20 else "🪫"
        await message.answer(f"{emoji} <b>Батарея</b>\nЗаряд: {pct}%\nСтатус: {status}\nТемпература: {temp}°C")
    else:
        await message.answer(f"❌ {result.get('error', 'Ошибка получения данных')}")


# ── /torch ────────────────────────────────────────────────────────────────────

@dp.message(Command("torch"))
async def cmd_torch(message: Message):
    if not is_owner(message):
        return
    arg = message.text.removeprefix("/torch").strip().lower()
    if arg not in ("on", "off"):
        await message.answer("Использование: /torch on или /torch off")
        return
    result = tools.torch_flashlight(arg == "on")
    emoji = "🔦" if arg == "on" else "⬛"
    status = "включён" if arg == "on" else "выключен"
    if result.get("success"):
        await message.answer(f"{emoji} Фонарик {status}")
    else:
        await message.answer(f"❌ {result.get('error')}")


# ── /sms ──────────────────────────────────────────────────────────────────────

@dp.message(Command("sms"))
async def cmd_sms(message: Message):
    if not is_owner(message):
        return
    parts = message.text.removeprefix("/sms").strip().split(" ", 1)
    if len(parts) < 2:
        await message.answer("Использование: /sms <code>+79001234567 Привет!</code>")
        return
    number, text = parts[0], parts[1]
    result = tools.send_sms(number, text)
    if result.get("success"):
        await message.answer(f"✅ SMS отправлено на {number}")
    else:
        await message.answer(f"❌ {result.get('error')}")


# ── /speak ────────────────────────────────────────────────────────────────────

@dp.message(Command("speak"))
async def cmd_speak(message: Message):
    if not is_owner(message):
        return
    text = message.text.removeprefix("/speak").strip()
    if not text:
        await message.answer("Использование: /speak <code>Привет, это Jarvis</code>")
        return
    await message.answer("🔊 Озвучиваю...")
    result = await tools.speak(text)
    if result.get("success"):
        await message.answer("✅ Воспроизвожу")
    else:
        await message.answer(f"❌ {result.get('error')}")


# ── /device ───────────────────────────────────────────────────────────────────

@dp.message(Command("device"))
async def cmd_device(message: Message):
    if not is_owner(message):
        return
    d = tools.get_device_info()
    await message.answer(
        f"📱 <b>Устройство</b>\n\n"
        f"ОС: {d['platform']}\n"
        f"Архитектура: {d['machine']}\n"
        f"CPU ядер: {d['cpu_count']}\n"
        f"RAM: {d['ram_available_gb']} / {d['ram_total_gb']} GB\n"
        f"Диск: {d['disk_free_gb']} / {d['disk_total_gb']} GB"
    )


# ── AI чат (всё остальное) ────────────────────────────────────────────────────

@dp.message(F.text)
async def handle_chat(message: Message):
    if not is_owner(message):
        return
    thinking = await message.answer("🧠 Думаю...")
    response = brain.chat(message.text)
    await thinking.delete()
    await message.answer(response)


# ── Запуск ────────────────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        log.error("JARVIS_BOT_TOKEN не задан! Добавь его в .env или переменные окружения.")
        return
    log.info("Jarvis запускается...")
    log.info(f"Модель выбрана: {brain.select_model()['name']}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
