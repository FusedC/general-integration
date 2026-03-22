#!/usr/bin/env python3
"""
Telegram Bot для управления проектами
С прогресс-баром и кнопкой просмотра логов
"""
import os
import subprocess
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Загружаем переменные из .env
from dotenv import load_dotenv
load_dotenv()

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

# Глобальное хранилище логов (в памяти, очищается после просмотра)
_last_operation_logs = {}

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


def extract_progress(output: str) -> str:
    """Извлекает прогресс из вывода скрипта (например, 'Прогресс: 150/397')"""
    # Паттерны для поиска прогресса
    patterns = [
        r'Прогресс:\s*(\d+)/(\d+)',
        r'Пачка #(\d+):.*✅ Загружено:\s*(\d+)',
        r'Пакет (\d+)/(\d+):',
        r'(\d+)\s*из\s*(\d+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, output)
        if matches:
            last = matches[-1]
            if len(last) == 2:
                current, total = last
                percent = min(100, int(float(current) / float(total) * 100)) if total.isdigit() and int(total) > 0 else 0
                return f"▌" * (percent // 10) + "░" * (10 - percent // 10) + f" {percent}% ({current}/{total})"
    
    # Если нашли просто цифры (например, "✅ Загружено: 283")
    loaded = re.findall(r'✅ Загружено:\s*(\d+)', output)
    if loaded:
        return f"⏳ Обработано: {loaded[-1]} записей"
    
    # Если нашли "Сохранено N строк"
    saved = re.findall(r'✅ Сохранено (\d+) строк', output)
    if saved:
        return f"💾 Сохранено: {saved[-1]} строк"
    
    return ""


def run_script_with_progress(script: str, cwd: str = GENERAL_PATH, timeout: int = 600) -> tuple[bool, str, str]:
    """
    Запускает скрипт, парсит прогресс и возвращает (успех, краткий_вывод, полные_логи)
    """
    full_output = []
    progress_lines = []
    
    try:
        result = subprocess.run(
            ["python", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        
        # Разбиваем вывод на строки
        lines = (result.stdout + result.stderr).split('\n')
        
        # Фильтруем строки с прогрессом
        for line in lines:
            line = line.strip()
            if not line:
                continue
            full_output.append(line)
            # Сохраняем только "важные" строки для прогресс-бара
            if any(kw in line.lower() for kw in ['прогресс', 'пачка', 'пакет', 'загружено', 'сохранено', '✅', '❌', '⏰']):
                progress_lines.append(line)
        
        # Формируем краткий вывод для показа в чате
        brief = []
        for line in progress_lines[-15:]:  # Последние 15 строк прогресса
            if 'Прогресс:' in line or 'Пачка' in line or 'Пакет' in line:
                brief.append(line)
            elif line.startswith('✅') or line.startswith('❌') or line.startswith('⏰'):
                brief.append(line)
        
        brief_output = '\n'.join(brief) if brief else (result.stdout[-500:] if result.stdout else "")
        full_logs = '\n'.join(full_output[-100:])  # Последние 100 строк полных логов
        
        if result.returncode == 0:
            return True, brief_output.strip(), full_logs.strip()
        else:
            error = result.stderr[-500:] if result.stderr else "неизвестная ошибка"
            return False, f"❌ Ошибка: {error.strip()}", full_logs.strip()
            
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


async def run_task(query, task_name: str, task_func, success_msg: str, task_key: str):
    """Универсальная функция запуска задачи с прогресс-баром и логом"""
    await query.edit_message_text(f"🔄 {task_name}...\n\n`Запуск...`", parse_mode='Markdown')
    
    success, brief, full_logs = task_func()
    
    # Сохраняем логи для кнопки просмотра
    _last_operation_logs[task_key] = full_logs
    
    # Формируем сообщение с прогрессом
    progress = extract_progress(brief)
    if progress:
        status_msg = f"{progress}\n\n"
    else:
        status_msg = ""
    
    if success:
        message = f"✅ {success_msg}\n\n{status_msg}"
    else:
        message = f"❌ {task_name}:\n{brief}\n\n{status_msg}"
    
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
    
    # Извлекаем ключ задачи из callback_data
    task_key = query.data.replace("show_logs_", "")
    logs = _last_operation_logs.get(task_key, "❌ Логи не найдены (возможно, уже очищены)")
    
    # Форматируем логи для Telegram (код-блок, макс 4000 символов)
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
        ok1, _, _ = run_script_with_progress("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed", ""
        ok2, out2, logs2 = run_script_with_progress("import_to_sheets.py")
        return ok2, out2, logs2
    
    await run_task(query, "Запись МС", task, "МС успешно записан в Google Sheets", "ms")


async def run_mp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск МП"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _, _ = run_script_with_progress("fetch_mp.py")
        if not ok1: return False, "fetch_mp.py failed", ""
        ok2, out2, logs2 = run_script_with_progress("import_to_sheets.py")
        return ok2, out2, logs2
    
    await run_task(query, "Запись МП", task, "МП успешно записан в Google Sheets", "mp")


async def run_pi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ПИ (включая субкатегории)"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        ok1, _, _ = run_script_with_progress("fetch_ip.py")
        if not ok1: return False, "fetch_ip.py failed", ""
        ok2, _, _ = run_script_with_progress("add_subcategories_to_ip.py")
        if not ok2: return False, "add_subcategories failed", ""
        ok3, out3, logs3 = run_script_with_progress("import_to_sheets.py")
        return ok3, out3, logs3
    
    await run_task(query, "Запись ПИ", task, "ПИ (с субкатегориями) успешно записан в Google Sheets", "pi")


async def run_all_general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ВСЕГО: МС+МП+ПИ"""
    query = update.callback_query
    await query.answer()
    if not check_user_allowed(query.from_user.id): return
    
    def task():
        all_logs = []
        # МС
        ok1, _, logs1 = run_script_with_progress("fetch_ms.py")
        if not ok1: return False, "fetch_ms.py failed", logs1
        all_logs.append(logs1)
        # ПИ
        ok2, _, logs2 = run_script_with_progress("fetch_ip.py")
        if not ok2: return False, "fetch_ip.py failed", logs2
        all_logs.append(logs2)
        ok3, _, logs3 = run_script_with_progress("add_subcategories_to_ip.py")
        if not ok3: return False, "add_subcategories failed", logs3
        all_logs.append(logs3)
        # МП
        ok4, _, logs4 = run_script_with_progress("fetch_mp.py")
        if not ok4: return False, "fetch_mp.py failed", logs4
        all_logs.append(logs4)
        # Импорт всего
        ok5, out5, logs5 = run_script_with_progress("import_to_sheets.py")
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
    
    await query.edit_message_text(f"🔄 Запуск {parser['name']}...\n\n`Запуск...`", parse_mode='Markdown')
    
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
        progress = extract_progress(output)
        brief = '\n'.join([l for l in output.split('\n')[-15:] if any(kw in l.lower() for kw in ['прогресс', 'пачка', '✅', '❌', 'сохранено'])])
        
        # Сохраняем логи
        _last_operation_logs[f"parser_{parser_key}"] = output[-2000:]
        
        if result.returncode == 0:
            message = f"✅ {parser['name']} завершён"
        else:
            message = f"❌ {parser['name']}:\n{brief if brief else output[-500:]}"
        
        if progress:
            message = f"{progress}\n\n{message}"
        
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
    
    await query.edit_message_text("🚀 Запуск ВСЕХ парсеров...")
    
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
            progress = extract_progress(output)
            results.append(f"{status} {parser['name']} {progress}")
        except Exception as e:
            results.append(f"❌ {parser['name']}: {e}")
            all_logs.append(f"=== {parser['name']} ===\nEXCEPTION: {e}")
    
    _last_operation_logs["parsers_all"] = "\n\n".join(all_logs)
    
    message = "📦 Результаты:\n" + "\n".join(results)
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
