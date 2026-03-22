#!/usr/bin/env python3
"""
Telegram Bot для управления проектами
GENERAL + 4 ТГ парсера (каждый одной кнопкой)
"""
import os
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== GENERAL (основной проект) ====================
GENERAL_SCRIPTS = [
    ("fetch_ip.py", "📥 Выгрузка из ПИ"),
    ("add_subcategories_to_ip.py", "🏷️ Субкатегории"),
    ("fetch_mp.py", "📊 Выгрузка из МП"),
    ("import_to_sheets.py", "📤 Импорт в Sheets")
]

# ==================== ТГ ПАРСЕРЫ ====================
PARSERS = {
    "amax": {
        "name": "📦 AMAX",
        "path": "/Users/samarasamara/AMAX_to_sheets",
        "script": "telegram_parser.py"
    },
    "bsa": {
        "name": "📦 BSA",
        "path": "/Users/samarasamara/BSA_to_sheets",
        "script": "telegram_parser.py"
    },
    "munstore": {
        "name": "📦 MunStore",
        "path": "/Users/samarasamara/MunStore_to_sheets",
        "script": "telegram_parser.py"
    },
    "supportairlines": {
        "name": "📦 SupportAirlines",
        "path": "/Users/samarasamara/SupportAirlines_to_sheets",
        "script": "telegram_parser.py"
    }
}


def check_user_allowed(user_id: int) -> bool:
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    if not check_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 GENERAL (основной)", callback_data="general_menu")],
        [InlineKeyboardButton("📦 AMAX (ТГ парсер)", callback_data="run_parser_amax")],
        [InlineKeyboardButton("📦 BSA (ТГ парсер)", callback_data="run_parser_bsa")],
        [InlineKeyboardButton("📦 MunStore (ТГ парсер)", callback_data="run_parser_munstore")],
        [InlineKeyboardButton("📦 SupportAirlines (ТГ парсер)", callback_data="run_parser_supportairlines")],
        [InlineKeyboardButton("🚀 Запустить ВСЕ парсеры", callback_data="run_all_parsers")],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Bot управления проектами*\n\n"
        "Выберите проект:\n\n"
        "🔄 *GENERAL* — выгрузка из МС, МП, ПИ\n"
        "📦 *Парсеры* — обновление прайсов из ТГ",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if not check_user_allowed(query.from_user.id):
        await query.edit_message_text("❌ Доступ запрещён")
        return
    
    data = query.data
    
    # Меню GENERAL
    if data == "general_menu":
        keyboard = []
        for script_file, script_name in GENERAL_SCRIPTS:
            keyboard.append([InlineKeyboardButton(
                script_name,
                callback_data=f"run_general_{script_file}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start")])
        keyboard.append([InlineKeyboardButton("🚀 Запустить всё", callback_data="run_general_all")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "*🔄 GENERAL (основной проект)*\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Запуск скрипта GENERAL
    elif data.startswith("run_general_"):
        if data == "run_general_all":
            await run_all_general_scripts(query)
        else:
            script_file = data.replace("run_general_", "")
            await run_general_script(query, script_file)
    
    # Запуск парсера
    elif data.startswith("run_parser_"):
        if data == "run_all_parsers":
            await run_all_parsers(query)
        else:
            parser_key = data.replace("run_parser_", "")
            parser = PARSERS.get(parser_key)
            if parser:
                await run_parser(query, parser)
    
    # Статус
    elif data == "status":
        await show_status(query)
    
    # Назад
    elif data == "start":
        await start(update, context)


async def run_general_script(query, script_file: str):
    """Запускает скрипт GENERAL"""
    await query.edit_message_text(f"🔄 Запуск *{script_file}*...", parse_mode='Markdown')
    
    try:
        result = subprocess.run(
            ["python", script_file],
            capture_output=True,
            text=True,
            timeout=600,
            cwd="/Users/samarasamara/GENERAL"
        )
        
        output = result.stdout[-2000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""
        
        if result.returncode == 0:
            message = f"✅ *{script_file}* завершён!\n\n"
            if output:
                message += f"📋 *Вывод:*\n```\n{output.strip()}\n```"
        else:
            message = f"❌ *{script_file}* завершился с ошибкой\n\n"
            if error:
                message += f"🔍 *Ошибка:*\n```\n{error.strip()}\n```"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="general_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await query.edit_message_text(f"⏰ *{script_file}* превысил время (10 мин)")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: `{str(e)}`")


async def run_all_general_scripts(query):
    """Запускает все скрипты GENERAL"""
    await query.edit_message_text(
        "🚀 Запуск *всех скриптов GENERAL*...\nЭто займёт несколько минут.",
        parse_mode='Markdown'
    )
    
    for script_file, script_name in GENERAL_SCRIPTS:
        await query.message.reply_text(f"🔄 {script_name}...")
        try:
            result = subprocess.run(
                ["python", script_file],
                capture_output=True,
                text=True,
                timeout=600,
                cwd="/Users/samarasamara/GENERAL"
            )
            status = "✅" if result.returncode == 0 else "❌"
            await query.message.reply_text(f"{status} {script_name}")
        except Exception as e:
            await query.message.reply_text(f"❌ {script_name}: {e}")
    
    await query.message.reply_text("🎉 *GENERAL завершён!*\nПроверьте Google Sheets.", parse_mode='Markdown')


async def run_parser(query, parser: dict):
    """Запускает парсер"""
    parser_name = parser["name"]
    await query.edit_message_text(f"🚀 Запуск *{parser_name}*...", parse_mode='Markdown')
    
    project_path = parser["path"]
    script_file = parser["script"]
    python_path = os.path.join(project_path, ".venv", "bin", "python")
    script_path = os.path.join(project_path, script_file)
    
    try:
        result = subprocess.run(
            [python_path, script_path],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=project_path
        )
        
        output = result.stdout[-2000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""
        
        if result.returncode == 0:
            message = f"✅ *{parser_name}* завершён!\n\n"
            if output:
                message += f"📋 *Вывод:*\n```\n{output.strip()}\n```"
        else:
            message = f"❌ *{parser_name}* завершился с ошибкой\n\n"
            if error:
                message += f"🔍 *Ошибка:*\n```\n{error.strip()}\n```"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await query.edit_message_text(f"⏰ *{parser_name}* превысил время (10 мин)")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: `{str(e)}`")


async def run_all_parsers(query):
    """Запускает все парсеры"""
    await query.edit_message_text(
        "🚀 Запуск *ВСЕХ парсеров*...\nЭто займёт время.",
        parse_mode='Markdown'
    )
    
    for parser_key, parser in PARSERS.items():
        parser_name = parser["name"]
        await query.message.reply_text(f"\n🔄 {parser_name}...")
        
        project_path = parser["path"]
        script_file = parser["script"]
        python_path = os.path.join(project_path, ".venv", "bin", "python")
        script_path = os.path.join(project_path, script_file)
        
        try:
            result = subprocess.run(
                [python_path, script_path],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=project_path
            )
            status = "✅" if result.returncode == 0 else "❌"
            await query.message.reply_text(f"{status} {parser_name}")
        except Exception as e:
            await query.message.reply_text(f"❌ {parser_name}: {e}")
    
    await query.message.reply_text("🎉 *ВСЕ парсеры завершены!*", parse_mode='Markdown')


async def show_status(query):
    """Показывает статус файлов"""
    await query.edit_message_text("📊 Проверка статуса...")
    
    output_dir = "/Users/samarasamara/GENERAL/output"
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
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан")
        return
    
    print("🤖 Запуск Telegram бота...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Бот запущен! Ожидаю команды...")
    print(f"📋 GENERAL скриптов: {len(GENERAL_SCRIPTS)}")
    print(f"📦 Парсеров: {len(PARSERS)}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
