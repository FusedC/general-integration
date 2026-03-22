#!/usr/bin/env python3
"""
Импорт данных из CSV файлов в Google Таблицы
Версия: с retry, батчами и обработкой больших файлов
"""
import sys
import gspread
import csv
import time
from pathlib import Path
from google.oauth2 import service_account

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR

SHEETS_CONFIG = {
    "ms_products.csv": {"sheet_name": "МС - Товары", "description": "Данные из МойСклад"},
    "ip_mapping.csv": {"sheet_name": "ПИ - Маппинг", "description": "Данные из Проекта Интеграции"},
    "mp_reports.csv": {"sheet_name": "МП - Отчёты", "description": "Данные из MarketParser"}
}

# Настройки для больших файлов
BATCH_SIZE = 500  # Строк за один запрос
MAX_RETRIES = 3   # Максимум попыток
RETRY_DELAY = 2   # Задержка между попытками (сек)


def get_spreadsheet_id():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("⚠️ GOOGLE_SHEET_ID не задан в .env файле")
        sheet_id = input("Введите ID таблицы: ").strip()
        if sheet_id:
            with open(".env", "a") as f:
                f.write(f"\nGOOGLE_SHEET_ID={sheet_id}\n")
    return sheet_id


def connect_to_sheets(credentials_path: str):
    print("🔐 Подключение к Google Sheets...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(credentials)
        print("✅ Успешная авторизация")
        return client
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return None


def get_column_letter(col_index: int) -> str:
    letters = []
    while col_index > 0:
        col_index -= 1
        letters.append(chr(65 + (col_index % 26)))
        col_index //= 26
    return ''.join(reversed(letters))


def update_with_retry(worksheet, range_name, values, max_retries=MAX_RETRIES):
    """Запись данных с повторами при ошибках"""
    for attempt in range(1, max_retries + 1):
        try:
            worksheet.update(range_name=range_name, values=values)
            return True
        except Exception as e:
            if attempt < max_retries:
                wait_time = RETRY_DELAY * attempt
                print(f"   ⚠️ Ошибка: {e}")
                print(f"   🔄 Повтор {attempt}/{max_retries} через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Ошибка после {max_retries} попыток: {e}")
                return False
    return False


def import_csv_to_sheet(client, csv_path: Path, sheet_name: str, spreadsheet_id: str):
    print(f"\n📤 Импорт: {csv_path.name} → {sheet_name}")
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print(f"   📋 Лист '{sheet_name}' найден")
        except gspread.exceptions.WorksheetNotFound:
            print(f"   📄 Создаём лист '{sheet_name}'...")
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=100)
        
        # Читаем CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        if not data:
            print("   ⚠️ Файл пуст")
            return False
        
        rows_count = len(data)
        cols_count = len(data[0]) if data else 0
        print(f"   📊 Строк: {rows_count}, Колонок: {cols_count}")
        
        # Показываем заголовки
        if data:
            preview = ', '.join(data[0][:10]) + ('...' if len(data[0]) > 10 else '')
            print(f"   🔍 Заголовки: {preview}")
        
        # ПОЛНАЯ ПЕРЕЗАПИСЬ
        print("   🧹 Полная очистка листа...")
        worksheet.clear()
        
        # Записываем данные БАТЧАМИ (для больших файлов)
        print("   📝 Записываем данные...")
        
        if rows_count > BATCH_SIZE:
            # Разбиваем на батчи
            num_batches = (rows_count // BATCH_SIZE) + 1
            print(f"   📦 Разбиваем на {num_batches} пакетов по {BATCH_SIZE} строк")
            
            # Сначала заголовки
            header_range = f'A1:{get_column_letter(cols_count)}1'
            if not update_with_retry(worksheet, header_range, [data[0]]):
                return False
            print(f"   ✅ Заголовок записан")
            
            # Затем данные батчами
            for batch_num in range(num_batches):
                start_row = 1 + (batch_num * BATCH_SIZE)
                end_row = min(rows_count, start_row + BATCH_SIZE - 1)
                
                if start_row >= rows_count:
                    break
                
                batch_data = data[start_row:end_row + 1]
                sheet_start = start_row + 1  # +1 потому что заголовок уже записан
                sheet_end = sheet_start + len(batch_data) - 1
                
                range_name = f'A{sheet_start}:{get_column_letter(cols_count)}{sheet_end}'
                
                print(f"   📦 Пакет {batch_num + 1}/{num_batches}: строки {start_row}-{end_row}")
                
                if not update_with_retry(worksheet, range_name, batch_data):
                    print(f"   ❌ Ошибка записи пакета {batch_num + 1}")
                    return False
                
                # Небольшая задержка между батчами
                if batch_num < num_batches - 1:
                    time.sleep(0.5)
        else:
            # Маленький файл — записываем целиком
            end_row = rows_count
            end_col = get_column_letter(cols_count)
            target_range = f'A1:{end_col}{end_row}'
            
            if not update_with_retry(worksheet, target_range, data):
                return False
        
        # Форматируем заголовок
        if rows_count > 0:
            print("   🎨 Форматируем заголовок...")
            header_range = f'A1:{get_column_letter(cols_count)}1'
            worksheet.format(header_range, {
                'backgroundColor': {'red': 0.26, 'green': 0.52, 'blue': 0.96},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
        
        # Замораживаем первую строку
        print("   ❄️ Замораживаем первую строку...")
        worksheet.freeze(rows=1)
        
        # Настраиваем ширину колонок (первые 30)
        print("   📐 Настраиваем ширину колонок...")
        requests = []
        for i in range(1, min(cols_count + 1, 31)):
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": i - 1,
                        "endIndex": i
                    },
                    "properties": {"pixelSize": 150},
                    "fields": "pixelSize"
                }
            })
        if requests:
            worksheet.spreadsheet.batch_update({"requests": requests})
        
        print(f"   ✅ Успешно загружено {rows_count} строк")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print(" ИМПОРТ ДАННЫХ В GOOGLE ТАБЛИЦЫ")
    print("=" * 60)
    
    credentials_path = Path(__file__).parent / "credentials.json"
    if not credentials_path.exists():
        print("❌ Ошибка: файл credentials.json не найден")
        sys.exit(1)
    
    client = connect_to_sheets(str(credentials_path))
    if not client:
        sys.exit(1)
    
    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        print("❌ ID таблицы не указан")
        sys.exit(1)
    
    print(f"\n📁 Таблица ID: {spreadsheet_id}")
    
    results = []
    for csv_file, config in SHEETS_CONFIG.items():
        csv_path = OUTPUT_DIR / csv_file
        if csv_path.exists():
            success = import_csv_to_sheet(client, csv_path, config["sheet_name"], spreadsheet_id)
            results.append((csv_file, success))
        else:
            print(f"\n⚠️ Файл {csv_file} не найден (пропущено)")
            results.append((csv_file, False))
    
    print(f"\n{'=' * 60}")
    print(" ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'=' * 60}")
    for file_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {file_name}")
    success_count = sum(1 for _, s in results if s)
    print(f"\n📊 Успешно: {success_count} из {len(results)}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
