#!/usr/bin/env python3
"""
Telegram Bot для удалённого управления проектом
Команды:
  /start - Приветствие и меню
  /status - Статус файлов
  /fetch_ip - Выгрузка из Проекта Интеграции
  /fetch_mp - Выгрузка из MarketParser
  /import - Импорт в Google Sheets
  /full - Полная выгрузка (всё подряд)
  /help - Помощь
"""
import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def check_user_allowed(user_id: int) -> bool:
    """Проверяет, разрешён ли пользователь"""
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    
    if not check_user_allowed(user_id):
        await update.message.reply_text("❌ Доступ запрещён")
        logger.warning(f"Запрещённый доступ: user_id={user_id}")
        return
    
    await update.message.reply_text(
        "🤖 *Bot для управления интеграцией*\n\n"
        "Доступные команды:\n"
        "/status - Статус файлов вывода\n"
        "/fetch_ip - Выгрузка из Проекта Интеграции (ПИ)\n"
        "/fetch_mp - Выгрузка из MarketParser (МП)\n"
        "/import - Импорт данных в Google Sheets\n"
        "/full - Полная выгрузка (все скрипты подряд)\n"
        "/help - Подробная помощь",
        parse_mode='Markdown'
    )
    logger.info(f"User {user_id} started bot")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - показывает статус файлов"""
    if not check_user_allowed(update.effective_user.id):
        return
    
    await update.message.reply_text("📊 Проверка статуса файлов...")
    
    output_dir = "output"
    files_info = []
    
    for filename in ["ip_mapping.csv", "mp_reports.csv", "ms_products.csv"]:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size_kb = os.path.getsize(filepath) / 1024
            mtime = os.path.getmtime(filepath)
            from datetime import datetime
            updated = datetime.fromtimestamp(mtime).strftime("%d.%m %H:%M")
            files_info.append(f"• `{filename}`: {size_kb:.1f} KB (обновлено: {updated})")
        else:
            files_info.append(f"• `{filename}`: ❌ не найден")
    
    message = "📁 *Статус файлов:*\n\n" + "\n".join(files_info)
    await update.message.reply_text(message, parse_mode='Markdown')


async def run_script(update: Update, context: ContextTypes.DEFAULT_TYPE, script_name: str, display_name: str):
    """Запускает скрипт и отправляет результат в Telegram"""
    if not check_user_allowed(update.effective_user.id):
        return
    
    await update.message.reply_text(f"🔄 Запуск *{display_name}*...", parse_mode='Markdown')
    
    try:
        # Запускаем скрипт
        result = subprocess.run(
            ["python", script_name],
            capture_output=True,
            text=True,
            timeout=600,  # 10 минут максимум
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # Формируем ответ
        output = result.stdout[-2000:] if result.stdout else ""
        error = result.stderr[-500:] if result.stderr else ""
        
        if result.returncode == 0:
            message = f"✅ *{display_name}* завершён успешно!\n\n"
            if output:
                message += f"📋 *Вывод:*\n```\n{output.strip()}\n```"
        else:
            message = f"❌ *{display_name}* завершился с ошибкой (код {result.returncode})\n\n"
            if error:
                message += f"🔍 *Ошибка:*\n```\n{error.strip()}\n```"
            elif output:
                message += f"📋 *Вывод:*\n```\n{output.strip()}\n```"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text(f"⏰ *{display_name}* превысил время выполнения (10 мин)")
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Файл `{script_name}` не найден")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: `{str(e)}`")


async def fetch_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /fetch_ip"""
    await run_script(update, context, "fetch_ip.py", "Выгрузка из ПИ")


async def fetch_mp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /fetch_mp"""
    await run_script(update, context, "fetch_mp.py", "Выгрузка из МП")


async def import_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /import"""
    await run_script(update, context, "import_to_sheets.py", "Импорт в Google Sheets")


async def full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /full - полная выгрузка"""
    if not check_user_allowed(update.effective_user.id):
        return
    
    await update.message.reply_text("🚀 Запуск *полной выгрузки*...\nЭто займёт несколько минут.", parse_mode='Markdown')
    
    scripts = [
        ("fetch_ip.py", "1/4: ПИ"),
        ("add_subcategories_to_ip.py", "2/4: Субкатегории"),
        ("fetch_mp.py", "3/4: МП"),
        ("import_to_sheets.py", "4/4: Google Sheets")
    ]
    
    for script_name, display_name in scripts:
        await update.message.reply_text(f"🔄 {display_name}...")
        try:
            result = subprocess.run(
                ["python", script_name],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            status = "✅" if result.returncode == 0 else "❌"
            await update.message.reply_text(f"{status} {display_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ {display_name}: {e}")
    
    await update.message.reply_text("🎉 *Полная выгрузка завершена!*\nПроверьте Google Sheets.", parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 *Справка по боту*\n\n"
        "Этот бот управляет автоматической выгрузкой данных из:\n"
        "• *МойСклад (МС)* - товары и цены\n"
        "• *MarketParser (МП)* - отчёты конкурентов\n"
        "• *Проект Интеграции (ПИ)* - настройки кампаний\n\n"
        "Результаты загружаются в *Google Sheets*.\n\n"
        "*Команды:*\n"
        "/start - Приветствие и меню\n"
        "/status - Показать статус файлов вывода\n"
        "/fetch_ip - Запустить выгрузку из ПИ\n"
        "/fetch_mp - Запустить выгрузку из МП\n"
        "/import - Запустить импорт в Google Sheets\n"
        "/full - Запустить полную выгрузку (все скрипты)\n"
        "/help - Эта справка",
        parse_mode='Markdown'
    )


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан в переменных окружения")
        print("💡 Добавьте секрет TELEGRAM_BOT_TOKEN в GitHub Actions")
        return
    
    print("🤖 Запуск Telegram бота...")
    
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("fetch_ip", fetch_ip))
    app.add_handler(CommandHandler("fetch_mp", fetch_mp))
    app.add_handler(CommandHandler("import", import_sheets))
    app.add_handler(CommandHandler("full", full))
    app.add_handler(CommandHandler("help", help_command))
    
    # Запускаем polling
    print("✅ Бот запущен! Ожидаю команды...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
