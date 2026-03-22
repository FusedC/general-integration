#!/usr/bin/env python3
"""
Telegram Bot для управления проектами
Без прогресс-бара + со справкой
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

# Глобальное хранилище логов
_last_operation_logs = {}

# ==================== ПРОЕКТЫ ====================
PARSERS = {
    "amax": {"name": "📦 AMAX", "path": "/Users/samarasamara/AMAX_to_sheets", "script": "telegram_parser.py"},
    "bsa": {"name": "📦 BSA", "path": "/Users/samarasamara/BSA_to_sheets", "script": "telegram_parser.py"},
    "munstore": {"name": "📦 MunStore", "path": "/Users/samarasamara/MunStore_to_sheets", "script": "telegram_parser.py"},
    "supportairlines": {"name": "📦 SupportAirlines", "path": "/Users/samarasamara/SupportAirlines_to_sheets", "script": "telegram_parser.py"}
}

GENERAL_PATH = "/Users/samarasamara/GENERAL"

# ==================== СПРАВКА ====================
HELP_TEXT = """
📖 *СПРАВОЧНИК ПО БОТУ*

*🔄 GENERAL (основной проект):*
• 📊 Запуск и запись МС — Выгружает товары и цены из МойСклад, записывает в Google Sheets (лист "МС - Товары")
• 📈 Запуск и запись МП — Выгружает отчёты по конкурентам из MarketParser, записывает в Google Sheets (лист "МП - Отчёты")
• 🗂️ Запуск и запись ПИ — Выгружает настройки кампаний из Проекта Интеграции + субкатегории, записывает в Google Sheets (лист "ПИ - Маппинг")
• 🔄 Запуск и запись МС+МП+ПИ — Полная выгрузка всех трёх источников подряд

*📦 Парсеры Telegram-каналов:*
• 📦 AMAX — Парсинг прайса поставщика AMAX из ТГ-канала
• 📦 BSA — Парсинг прайса поставщика BSA из ТГ-канала
• 📦 MunStore — Парсинг прайса поставщика MunStore из ТГ-канала
• 📦 SupportAirlines — Парсинг прайса поставщика SupportAirlines из ТГ-канала
• 🚀 ВСЕ парсеры — Запускает все 4 парсера последовательно

*ℹ️ Прочее:*
• 📊 Статус — Показывает статус файлов выгрузки (когда обновлялись)
• 📖 Справка — Эта справка

*⏰ Автоматическая выгрузка:*
Каждый день в 12:00 MSK GitHub Actions автоматически запускает выгрузку GENERAL (МС+МП+ПИ)
"""


def check_user_allowed(user_id: int) -> bool:
    return str(user_id) in ALLOWED_USERS


def run_script(script: str, cwd: str = GENERAL_PATH, timeout: int = 600) -> tuple[bool, str, str]:
    """Запускает скрипт и возвращает (успех, краткий_вывод, полные_логи)"""
    try:
        result = subprocess.run(
            ["python", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        
        output = (result.stdout + result.stderr).strip()
        full_logs = output[-2000:] if len(output) > 2000 else output
        
        # Извлекаем только итоговые строки для краткого вывода
        brief_lines = []
        for line in output.split('\n'):
            line = line.strip()
            if any(kw in line for kw in ['✅', '❌', '⏰', 'Сохранено', 'Загружено', 'Итого', 'Успешно']):
                brief_lines.append(line)
        
        brief = '\n'.join(brief_lines[-10:]) if brief_lines else (output[-500:] if output else "")
        
        if result.returncode == 0:
            return True, brief, full_logs
        else:
            error = result.stderr[-500:] if result.stderr else "неизвестная ошибка"
            return False, f"❌ Ошибка: {error.strip()}", full_logs
            
    except subprocess.TimeoutExpired:
        return False, "⏰ Превышено время выполнения (10 мин)", "⏰ TIMEOUT"
    except Exception as e:
        return False, f"❌ Исключение: {str(e)}", f"EXCEPTION: {str(e)}"


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
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("📖 Справка", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🤖 *Bot управления*\nВыберите проект:", reply_markup=reply_markup, parse_mode='Markdown')


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(HELP_TEXT, reply_markup=reply_markup, parse_mode='Markdown')


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус файлов"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    output_dir = os.path.join(GENERAL_PATH, "output")
    files_info = []
    
    for filename in ["ip_mapping.csv", "mp_reports.csv", "ms_products.csv"]:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size_kb = os.path.getsize(filepath) / 1024
            from datetime import datetime
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%d.%m %H:%M")
            files_info.append(f"• `{filename}`: {size_kb:.1f} KB ({mtime})")
        else:
            files_info.append(f"• `{filename}`: ❌ не найден")
    
    message = "📁 *Статус файлов GENERAL:*\n\n" + "\n".join(files_info)
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def general_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню GENERAL - 5 кнопок + справка"""
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


async def run_task(query, task_name: str, task_func, success_msg: str, task_key: str):
    """Универсальная функция запуска задачи"""
    await query.edit_message_text(f"⏳ {task_name}...\n\n_Подождите, выполняется..._", parse_mode='Markdown')
    
    success, brief, full_logs = task_func()
    
    # Сохраняем логи для кнопки просмотра
    _last_operation_logs[task_key] = full_logs
    
    if success:
        message = f"✅ {success_msg}"
        if brief:
            message += f"\n\n📋 *Итог:*\n```\n{brief}\n```"
    else:
        message = f"❌ {task_name}:\n```\n{brief}\n```"
    
    # Кнопки: Назад + Показать логи
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_general")],
        [InlineKeyboardButton("📋 Показать логи", callback_data=f"show_logs_{task_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def show_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает полные логи операции"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    task_key = query.data.replace("show_logs_", "")
    logs = _last_operation_logs.get(task_key, "❌ Логи не найдены (возможно, уже очищены)")
    
    logs_preview = logs[-3500:] if len(logs) > 3500 else logs
    
    message = f"📋 *Логи операции:*\n```\n{logs_preview}\n```"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_general")],
        [InlineKeyboardButton("🗑️ Очистить логи", callback_data=f"clear_logs_{task_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def clear_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает логи из памяти"""
    query = update.callback_query
    await query.answer()
    
    task_key = query.data.replace("clear_logs_", "")
    if task_key in _last_operation_logs:
        del _last_operation_logs[task_key]
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_general")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("🗑️ Логи очищены", reply_markup=reply_markup, parse_mode='Markdown')


async def run_ms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск МС"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _, _ = run_script("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed", ""
        ok2, out2, logs2 = run_script("import_to_sheets.py")
        return ok2, out2, logs2
    
    await run_task(query, "Запись МС", task, "МС успешно записан в Google Sheets", "ms")


async def run_mp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск МП"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _, _ = run_script("fetch_mp.py")
        if not ok1: return False, "fetch_mp.py failed", ""
        ok2, out2, logs2 = run_script("import_to_sheets.py")
        return ok2, out2, logs2
    
    await run_task(query, "Запись МП", task, "МП успешно записан в Google Sheets", "mp")


async def run_pi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ПИ (включая субкатегории)"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _, _ = run_script("fetch_ip.py")
        if not ok1: return False, "fetch_ip.py failed", ""
        ok2, _, _ = run_script("add_subcategories_to_ip.py")
        if not ok2: return False, "add_subcategories failed", ""
        ok3, out3, logs3 = run_script("import_to_sheets.py")
        return ok3, out3, logs3
    
    await run_task(query, "Запись ПИ", task, "ПИ (с субкатегориями) успешно записан в Google Sheets", "pi")


async def run_all_general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ВСЕГО: МС+МП+ПИ"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        all_logs = []
        ok1, _, logs1 = run_script("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed", logs1
        all_logs.append(logs1)
        ok2, _, logs2 = run_script("fetch_ip.py")
        if not ok2: return False, "fetch_ip.py failed", logs2
        all_logs.append(logs2)
        ok3, _, logs3 = run_script("add_subcategories_to_ip.py")
        if not ok3: return False, "add_subcategories failed", logs3
        all_logs.append(logs3)
        ok4, _, logs4 = run_script("fetch_mp.py")
        if not ok4: return False, "fetch_mp.py failed", logs4
        all_logs.append(logs4)
        ok5, out5, logs5 = run_script("import_to_sheets.py")
        all_logs.append(logs5)
        return ok5, out5, "\n\n=== LOGS ===\n\n".join(all_logs)
    
    await run_task(query, "Запись МС+МП+ПИ", task, "Все данные успешно записаны в Google Sheets", "all_general")


async def run_parser_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск парсера ТГ"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    data = query.data
    parser_key = data.replace("parser_", "")
    parser = PARSERS.get(parser_key)
    
    if not parser:
        await query.edit_message_text("❌ Парсер не найден")
        return
    
    await query.edit_message_text(f"⏳ Запуск {parser['name']}...\n\n_Подождите, выполняется..._", parse_mode='Markdown')
    
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
        
        output = (result.stdout + result.stderr).strip()
        _last_operation_logs[f"parser_{parser_key}"] = output[-2000:]
        
        brief_lines = [l for l in output.split('\n') if any(kw in l for kw in ['✅', '❌', 'Сохранено', 'Загружено', 'Итого'])]
        brief = '\n'.join(brief_lines[-10:]) if brief_lines else output[-500:]
        
        if result.returncode == 0:
            message = f"✅ {parser['name']} завершён"
        else:
            message = f"❌ {parser['name']}:\n```\n{brief if brief else output[-500:]}\n```"
        
    except Exception as e:
        message = f"❌ Ошибка: {str(e)}"
        _last_operation_logs[f"parser_{parser_key}"] = f"EXCEPTION: {str(e)}"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        [InlineKeyboardButton("📋 Показать логи", callback_data=f"show_logs_parser_{parser_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def run_all_parsers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск всех парсеров"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    await query.edit_message_text("🚀 Запуск ВСЕХ парсеров...\n\n_Подождите, выполняется..._", parse_mode='Markdown')
    
    all_logs = []
    results = []
    for key, parser in PARSERS.items():
        python_path = os.path.join(parser["path"], ".venv", "bin", "python")
        script_path = os.path.join(parser["path"], parser["script"])
        try:
            result = subprocess.run([python_path, script_path], capture_output=True, text=True, timeout=600, cwd=parser["path"])
            output = (result.stdout + result.stderr).strip()
            all_logs.append(f"=== {parser['name']} ===\n{output[-500:]}")
            status = "✅" if result.returncode == 0 else "❌"
            results.append(f"{status} {parser['name']}")
        except Exception as e:
            results.append(f"❌ {parser['name']}: {e}")
            all_logs.append(f"=== {parser['name']} ===\nEXCEPTION: {e}")
    
    _last_operation_logs["parsers_all"] = "\n\n".join(all_logs)
    
    message = "📦 *Результаты:*\n" + "\n".join(results)
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        [InlineKeyboardButton("📋 Показать логи", callback_data="show_logs_parsers_all")]
    ]
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
    
    # === Показать логи ===
    if data.startswith("show_logs_"):
        await show_logs_callback(update, context)
        return
    
    # === Очистить логи ===
    if data.startswith("clear_logs_"):
        await clear_logs_callback(update, context)
        return
    
    # === Справка ===
    if data == "help":
        await help_callback(update, context)
        return
    
    # === Статус ===
    if data == "status":
        await status_callback(update, context)
        return
    
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
        keyboard = [
            [InlineKeyboardButton("🔄 GENERAL", callback_data="general")],
            [InlineKeyboardButton("📦 AMAX", callback_data="parser_amax")],
            [InlineKeyboardButton("📦 BSA", callback_data="parser_bsa")],
            [InlineKeyboardButton("📦 MunStore", callback_data="parser_munstore")],
            [InlineKeyboardButton("📦 SupportAirlines", callback_data="parser_supportairlines")],
            [InlineKeyboardButton("🚀 ВСЕ парсеры", callback_data="parsers_all")],
            [InlineKeyboardButton("📊 Статус", callback_data="status")],
            [InlineKeyboardButton("📖 Справка", callback_data="help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🤖 *Bot управления*\nВыберите проект:", reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == "back_to_general":
        await general_menu(update, context)


def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан")
        return
    
    print("🤖 Запуск Telegram бота...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
