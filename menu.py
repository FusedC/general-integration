#!/usr/bin/env python3
"""
Интерактивное меню для выбора режима работы
Запуск: python menu.py
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import OUTPUT_DIR


def clear_screen():
    """Очищает экран терминала"""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header():
    """Печатает заголовок меню"""
    print("=" * 60)
    print("  📊 СИСТЕМА ВЫГРУЗКИ ДАННЫХ")
    print("  МС + ПИ + МП → Google Таблицы")
    print("=" * 60)
    print()


def print_status():
    """Показывает статус CSV файлов"""
    print("📁 Статус файлов в output/:")
    print("-" * 60)
    
    files = {
        "ms_products.csv": "МойСклад (МС)",
        "ip_mapping.csv": "Проект Интеграции (ПИ)",
        "mp_reports.csv": "MarketParser (МП)"
    }
    
    for filename, description in files.items():
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            lines = sum(1 for _ in open(filepath, 'r', encoding='utf-8')) - 1
            print(f"  ✅ {description}")
            print(f"     📄 {filename} | {lines:,} строк | {size_kb:.1f} KB")
        else:
            print(f"  ❌ {description}")
            print(f"     📄 {filename} | не выгружен")
        print()


def run_script(script_name: str, description: str) -> bool:
    """Запускает скрипт и возвращает результат"""
    print(f"\n{'=' * 60}")
    print(f"🚀 {description}")
    print(f"{'=' * 60}\n")
    
    result = subprocess.run(
        [sys.executable, script_name],
        cwd=Path(__file__).parent,
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0


def export_ms():
    """Выгрузка из МойСклад"""
    return run_script("fetch_ms.py", "ВЫГРУЗКА ИЗ МОЙ СКЛАД (МС)")


def export_ip():
    """Выгрузка из Проекта Интеграции"""
    return run_script("fetch_ip.py", "ВЫГРУЗКА ИЗ ПРОЕКТА ИНТЕГРАЦИИ (ПИ)")


def export_mp():
    """Выгрузка из MarketParser"""
    return run_script("fetch_mp.py", "ВЫГРУЗКА ИЗ MARKETPARSER (МП)")


def import_to_sheets(source: str = None):
    """Импорт в Google Таблицы (все или конкретный источник)"""
    print(f"\n{'=' * 60}")
    print("📤 ИМПОРТ В GOOGLE ТАБЛИЦЫ")
    print(f"{'=' * 60}\n")
    
    if source:
        # Импорт конкретного источника
        from import_to_sheets import connect_to_sheets, get_spreadsheet_id, import_csv_to_sheet, SHEETS_CONFIG
        
        credentials_path = Path(__file__).parent / "credentials.json"
        if not credentials_path.exists():
            print("❌ Ошибка: credentials.json не найден")
            return False
        
        client = connect_to_sheets(str(credentials_path))
        if not client:
            return False
        
        spreadsheet_id = get_spreadsheet_id()
        if not spreadsheet_id:
            return False
        
        csv_file = f"{source}.csv"
        csv_path = OUTPUT_DIR / csv_file
        
        if not csv_path.exists():
            print(f"❌ Файл {csv_path} не найден")
            return False
        
        sheet_name = SHEETS_CONFIG.get(csv_file, {}).get("sheet_name", source)
        success = import_csv_to_sheet(client, csv_path, sheet_name, spreadsheet_id)
        return success
    else:
        # Импорт всех файлов
        result = subprocess.run(
            [sys.executable, "import_to_sheets.py"],
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True
        )
        return result.returncode == 0


def show_menu():
    """Показывает главное меню"""
    clear_screen()
    print_header()
    print_status()
    
    print("📋 МЕНЮ ВЫБОРА ДЕЙСТВИЙ")
    print("-" * 60)
    print("  🔹 МОЙ СКЛАД (МС)")
    print("  1. Выгрузить МС → CSV")
    print("  2. Записать МС → Google Таблицы")
    print("  3. Выгрузить и записать МС")
    print()
    print("  🔹 MARKETPARSER (МП)")
    print("  4. Выгрузить МП → CSV")
    print("  5. Записать МП → Google Таблицы")
    print("  6. Выгрузить и записать МП")
    print()
    print("  🔹 ПРОЕКТ ИНТЕГРАЦИИ (ПИ)")
    print("  7. Выгрузить ПИ → CSV")
    print("  8. Записать ПИ → Google Таблицы")
    print("  9. Выгрузить и записать ПИ")
    print()
    print("  🔹 ОБЩЕЕ")
    print("  0. Выгрузить ВСЁ → CSV")
    print("  A. Записать ВСЁ → Google Таблицы")
    print("  B. Выгрузить и записать ВСЁ")
    print()
    print("  ❌  Q. Выход")
    print("-" * 60)


def main():
    """Основная функция меню"""
    while True:
        show_menu()
        
        choice = input("👉 Ваш выбор: ").strip().upper()
        
        success = False
        
        if choice == "1":
            success = export_ms()
        elif choice == "2":
            success = import_to_sheets("ms_products")
        elif choice == "3":
            success = export_ms()
            if success:
                success = import_to_sheets("ms_products")
        elif choice == "4":
            success = export_mp()
        elif choice == "5":
            success = import_to_sheets("mp_reports")
        elif choice == "6":
            success = export_mp()
            if success:
                success = import_to_sheets("mp_reports")
        elif choice == "7":
            success = export_ip()
        elif choice == "8":
            success = import_to_sheets("ip_mapping")
        elif choice == "9":
            success = export_ip()
            if success:
                success = import_to_sheets("ip_mapping")
        elif choice == "0":
            print("\n🔄 Запуск всех выгрузок...")
            success = export_ms() and export_ip() and export_mp()
        elif choice == "A":
            success = import_to_sheets()
        elif choice == "B":
            success = export_ms() and export_ip() and export_mp()
            if success:
                success = import_to_sheets()
        elif choice == "Q":
            print("\n👋 До свидания!")
            sys.exit(0)
        else:
            print("\n⚠️ Неверный выбор. Попробуйте снова.")
            input("Нажмите Enter чтобы продолжить...")
            continue
        
        # Показываем результат
        print("\n" + "=" * 60)
        if success:
            print("✅ ОПЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        else:
            print("❌ ОПЕРАЦИЯ ЗАВЕРШЕНА С ОШИБКОЙ")
        print("=" * 60)
        
        input("\nНажмите Enter чтобы продолжить...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")
        sys.exit(0)
