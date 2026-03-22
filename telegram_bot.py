#!/usr/bin/env python3
"""
Telegram Bot для управления ВСЕМИ проектами
5 проектов: GENERAL + 4 ТГ парсера
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

# ==================== СПИСОК ВСЕХ ПРОЕКТОВ ====================
PROJECTS = {
    "general": {
        "name": "🔄 GENERAL (основной)",
        "path": "/Users/samarasamara/GENERAL",
        "scripts": [
            ("fetch_ip.py", "📥 Выгрузка из ПИ"),
            ("add_subcategories_to_ip.py", "🏷️ Субкатегории"),
            ("fetch_mp.py", "📊 Выгрузка из МП"),
            ("import_to_sheets.py", "📤 Импорт в Sheets")
        ],
        "use_venv": True
    },
    "amax": {
        "name": "📦 AMAX (ТГ парсер)",
        "path": "/Users/samarasamara/AMAX_to_sheets",
        "scripts": [
            ("telegram_parser.py", "🚀 Запустить парсер")
        ],
        "use_venv": True
    },
    "bsa": {
        "name": "📦 BSA (ТГ парсер)",
        "path": "/Users/samarasamara/BSA_to_sheets",
        "scripts": [
            ("telegram_parser.py", "🚀 Запустить парсер")
        ],
        "use_venv": True
    },
    "munstore": {
        "name": "📦 MunStore (ТГ парсер)",
        "path": "/Users/samarasamara/MunStore_to_sheets",
        "scripts": [
            ("telegram_parser.py", "🚀 Запустить парсер")
        ],
        "use_venv": True
    },
    "supportairlines": {
        "name": "📦 SupportAirlines (ТГ парсер)",
        "path": "/Users/samarasamara/SupportAirlines_to_sheets",
        "scripts": [
            ("telegram_parser.py", "🚀 Запустить парсер")
        ],
        "use_venv": True
    }
}


def check_user_allowed(user_id: int) -> bool:
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню с кнопками проектов"""
    if not check_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    keyboard = []
    for project_key, project_info in PROJECTS.items():
        keyboard.append([InlineKeyboardButton(
            project_info["name"], 
            callback_data=f"project_{project_key}"
        )])
    
    keyboard.append([InlineKeyboardButton("📊 Статус", callback_data="status")])
    keyboard.append([InlineKeyboardButton("🔄 Запустить ВСЕ проекты", callback_data="full_all")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Bot управления ВСЕМИ проектами*\n\n"
        "Выберите проект для управления:",
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
    
    # Меню проекта
    if data.startswith("project_"):
        project_key = data.replace("project_", "")
        project = PROJECTS.get(project_key)
        
        if project:
            keyboard = []
            for script_file, script_name in project["scripts"]:
                keyboard.append([InlineKeyboardButton(
                    script_name,
                    callback_data=f"run_{project_key}_{script_file}"
                )])
            
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="start")])
            keyboard.append([InlineKeyboardButton("🚀 Запустить всё", callback_data=f"full_{project_key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"*{project['name']}*\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    # Запуск скрипта
    elif data.startswith("run_"):
        parts = data.replace("run_", "").split("_", 1)
        if len(parts) >= 2:
            project_key = parts[0]
            script_file = "_".join(parts[1:])
            project = PROJECTS.get(project_key)
            if project:
                await run_script_inline(query, project, script_file)
    
    # Полная выгрузка одного проекта
    elif data.startswith("full_"):
        project_key = data.replace("full_", "")
        if project_key == "all":
            await full_all_projects(query)
        else:
            project = PROJECTS.get(project_key)
            if project:
                await full_project(query, project)
    
    # Статус
    elif data == "status":
        await show_status(query)
    
    # Назад в главное меню
    elif data == "start":
        await start(update, context)


async def run_script_inline(query, project: dict, script_file: str):
    """Запускает скрипт и отправляет результат"""
    await query.edit_message_text(f"🔄 Запуск *{script_file}*...", parse_mode='Markdown')
    
    project_path = project["path"]
    use_venv = project.get("use_venv", True)
    
    # Формируем команду
    if use_venv:
        python_path = os.path.join(project_path, ".venv", "bin", "python")
        script_path = os.path.join(project_path, script_file)
        cmd = [python_path, script_path]
    else:
        cmd = ["python", script_file]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=project_path
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
            elif output:
                message += f"📋 *Вывод:*\n```\n{output.strip()}\n```"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await query.edit_message_text(f"⏰ *{script_file}* превысил время (10 мин)")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: `{str(e)}`")


async def full_project(query, project: dict):
    """Запускает все скрипты проекта"""
    await query.edit_message_text(
        f"🚀 Запуск *всех скриптов {project['name']}*...\nЭто займёт несколько минут.",
        parse_mode='Markdown'
    )
    
    project_path = project["path"]
    use_venv = project.get("use_venv", True)
    
    for script_file, script_name in project["scripts"]:
        await query.message.reply_text(f"🔄 {script_name}...")
        
        if use_venv:
            python_path = os.path.join(project_path, ".venv", "bin", "python")
            script_path = os.path.join(project_path, script_file)
            cmd = [python_path, script_path]
        else:
            cmd = ["python", script_file]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=project_path
            )
            status = "✅" if result.returncode == 0 else "❌"
            await query.message.reply_text(f"{status} {script_name}")
        except Exception as e:
            await query.message.reply_text(f"❌ {script_name}: {e}")
    
    await query.message.reply_text(
        f"🎉 *{project['name']} завершён!*",
        parse_mode='Markdown'
    )


async def full_all_projects(query):
    """Запускает все проекты"""
    await query.edit_message_text(
        "🚀 Запуск *ВСЕХ проектов*...\nЭто займёт время.",
        parse_mode='Markdown'
    )
    
    for project_key, project in PROJECTS.items():
        await query.message.reply_text(f"\n📦 *{project['name']}*")
        
        project_path = project["path"]
        use_venv = project.get("use_venv", True)
        
        for script_file, script_name in project["scripts"]:
            if use_venv:
                python_path = os.path.join(project_path, ".venv", "bin", "python")
                script_path = os.path.join(project_path, script_file)
                cmd = [python_path, script_path]
            else:
                cmd = ["python", script_file]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    cwd=project_path
                )
                status = "✅" if result.returncode == 0 else "❌"
                await query.message.reply_text(f"{status} {script_name}")
            except Exception as e:
                await query.message.reply_text(f"❌ {script_name}: {e}")
    
    await query.message.reply_text("🎉 *ВСЕ проекты завершены!*", parse_mode='Markdown')


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
    print(f"📋 Доступно проектов: {len(PROJECTS)}")
    for key, proj in PROJECTS.items():
        print(f"   • {proj['name']}")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
