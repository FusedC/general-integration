#!/usr/bin/env python3
"""
Telegram Bot для управления проектами
Упрощённое меню: 5 кнопок для GENERAL + 4 парсера
"""
import os
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Загружаем переменные из .env
from dotenv import load_dotenv
load_dotenv()

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/Users/samarasamara/GENERAL/bot.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== ПРОЕКТЫ ====================
PARSERS = {
    "amax": {"name": "📦 AMAX", "path": "/Users/samarasamara/AMAX_to_sheets", "script": "telegram_parser.py"},
    "bsa": {"name": "📦 BSA", "path": "/Users/samarasamara/BSA_to_sheets", "script": "telegram_parser.py"},
    "munstore": {"name": "📦 MunStore", "path": "/Users/samarasamara/MunStore_to_sheets", "script": "telegram_parser.py"},
    "supportairlines": {"name": "📦 SupportAirlines", "path": "/Users/samarasamara/SupportAirlines_to_sheets", "script": "telegram_parser.py"}
}

GENERAL_PATH = "/Users/samarasamara/GENERAL"


def check_user_allowed(user_id: int) -> bool:
    return str(user_id) in ALLOWED_USERS


def run_script(script: str, cwd: str = GENERAL_PATH, timeout: int = 600) -> tuple[bool, str]:
    """Запускает скрипт и возвращает (успех, вывод)"""
    try:
        result = subprocess.run(
            ["python", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        output = result.stdout[-1000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""
        if result.returncode == 0:
            return True, output.strip() if output else "✅ Успешно"
        else:
            return False, f"❌ Ошибка: {error.strip() if error else 'неизвестная'}"
    except subprocess.TimeoutExpired:
        return False, "⏰ Превышено время выполнения (10 мин)"
    except Exception as e:
        return False, f"❌ Исключение: {str(e)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    if not check_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 GENERAL", callback_data="general")],
        [InlineKeyboardButton("📦 AMAX", callback_data="parser_amax")],
        [InlineKeyboardButton("📦 BSA", callback_data="parser_bsa")],
        [InlineKeyboardButton("📦 MunStore", callback_data="parser_munstore")],
        [InlineKeyboardButton("📦 SupportAirlines", callback_data="parser_supportairlines")],
        [InlineKeyboardButton("🚀 ВСЕ парсеры", callback_data="parsers_all")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🤖 *Bot управления*\nВыберите проект:", reply_markup=reply_markup, parse_mode='Markdown')


async def general_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню GENERAL - ровно 5 кнопок"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Запуск и запись МС", callback_data="run_ms")],
        [InlineKeyboardButton("📈 Запуск и запись МП", callback_data="run_mp")],
        [InlineKeyboardButton("🗂️ Запуск и запись ПИ", callback_data="run_pi")],
        [InlineKeyboardButton("🔄 Запуск и запись МС+МП+ПИ", callback_data="run_all_general")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("*🔄 GENERAL*\nВыберите действие:", reply_markup=reply_markup, parse_mode='Markdown')


async def run_task(query, task_name: str, task_func, success_msg: str):
    """Универсальная функция запуска задачи"""
    await query.edit_message_text(f"🔄 {task_name}...")
    
    success, output = task_func()
    
    if success:
        message = f"✅ {success_msg}"
    else:
        message = f"❌ {task_name}:\n{output}"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_general")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def run_ms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск МС"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        # fetch_ms.py + import_to_sheets.py (только МС)
        ok1, _ = run_script("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed"
        ok2, out2 = run_script("import_to_sheets.py")
        return ok2, out2
    
    await run_task(query, "Запись МС", task, "МС успешно записан в Google Sheets")


async def run_mp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск МП"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _ = run_script("fetch_mp.py")
        if not ok1: return False, "fetch_mp.py failed"
        ok2, out2 = run_script("import_to_sheets.py")
        return ok2, out2
    
    await run_task(query, "Запись МП", task, "МП успешно записан в Google Sheets")


async def run_pi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ПИ (включая субкатегории)"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _ = run_script("fetch_ip.py")
        if not ok1: return False, "fetch_ip.py failed"
        ok2, _ = run_script("add_subcategories_to_ip.py")
        if not ok2: return False, "add_subcategories failed"
        ok3, out3 = run_script("import_to_sheets.py")
        return ok3, out3
    
    await run_task(query, "Запись ПИ", task, "ПИ (с субкатегориями) успешно записан в Google Sheets")


async def run_all_general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ВСЕГО: МС+МП+ПИ"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        # МС
        ok1, _ = run_script("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed"
        # ПИ
        ok2, _ = run_script("fetch_ip.py")
        if not ok2: return False, "fetch_ip.py failed"
        ok3, _ = run_script("add_subcategories_to_ip.py")
        if not ok3: return False, "add_subcategories failed"
        # МП
        ok4, _ = run_script("fetch_mp.py")
        if not ok4: return False, "fetch_mp.py failed"
        # Импорт всего
        ok5, out5 = run_script("import_to_sheets.py")
        return ok5, out5
    
    await run_task(query, "Запись МС+МП+ПИ", task, "Все данные успешно записаны в Google Sheets")


async def run_parser_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск парсера ТГ"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    data = query.data  # parser_amax, parser_bsa, etc.
    parser_key = data.replace("parser_", "")
    parser = PARSERS.get(parser_key)
    
    if not parser:
        await query.edit_message_text("❌ Парсер не найден")
        return
    
    await query.edit_message_text(f"🔄 Запуск {parser['name']}...")
    
    python_path = os.path.join(parser["path"], ".venv", "bin", "python")
    script_path = os.path.join(parser["path"], parser["script"])
    
    try:
        result = subprocess.run(
            [python_path, script_path],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=parser["path"]
        )
        if result.returncode == 0:
            message = f"✅ {parser['name']} завершён"
        else:
            message = f"❌ {parser['name']}:\n{result.stderr[-500:] if result.stderr else result.stdout[-500:]}"
    except Exception as e:
        message = f"❌ Ошибка: {str(e)}"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def run_all_parsers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск всех парсеров"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    await query.edit_message_text("🚀 Запуск ВСЕХ парсеров...")
    
    results = []
    for key, parser in PARSERS.items():
        python_path = os.path.join(parser["path"], ".venv", "bin", "python")
        script_path = os.path.join(parser["path"], parser["script"])
        try:
            result = subprocess.run([python_path, script_path], capture_output=True, text=True, timeout=600, cwd=parser["path"])
            status = "✅" if result.returncode == 0 else "❌"
            results.append(f"{status} {parser['name']}")
        except Exception as e:
            results.append(f"❌ {parser['name']}: {e}")
    
    message = "📦 Результаты:\n" + "\n".join(results)
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    data = query.data
    
    # === GENERAL меню ===
    if data == "general":
        await general_menu(update, context)
    
    # === Кнопки GENERAL ===
    elif data == "run_ms":
        await run_ms_callback(update, context)
    elif data == "run_mp":
        await run_mp_callback(update, context)
    elif data == "run_pi":
        await run_pi_callback(update, context)
    elif data == "run_all_general":
        await run_all_general_callback(update, context)
    
    # === Парсеры ===
    elif data.startswith("parser_"):
        await run_parser_callback(update, context)
    elif data == "parsers_all":
        await run_all_parsers_callback(update, context)
    
    # === Кнопки "Назад" ===
    elif data == "back_to_main":
        # Возврат в главное меню
        keyboard = [
            [InlineKeyboardButton("🔄 GENERAL", callback_data="general")],
            [InlineKeyboardButton("📦 AMAX", callback_data="parser_amax")],
            [InlineKeyboardButton("📦 BSA", callback_data="parser_bsa")],
            [InlineKeyboardButton("📦 MunStore", callback_data="parser_munstore")],
            [InlineKeyboardButton("📦 SupportAirlines", callback_data="parser_supportairlines")],
            [InlineKeyboardButton("🚀 ВСЕ парсеры", callback_data="parsers_all")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🤖 *Bot управления*\nВыберите проект:", reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "back_to_general":
        # Возврат в меню GENERAL
        await general_menu(update, context)


def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан")
        return
    
    print("🤖 Запуск Telegram бота...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
