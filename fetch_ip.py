#!/usr/bin/env python3
"""
Выгрузка данных из Проекта Интеграции (IP API)
Версия: с attributes и оптимизацией
"""
import sys
import json
import base64
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import IP_API_URL, IP_API_USER, IP_API_PASS, OUTPUT_DIR
from utils.api_client import APIClient
from utils.storage import save_to_csv


def get_auth_header(user: str, password: str) -> str:
    credentials = f"{user}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def flatten_json(obj, prefix='', max_depth=3, delimiter='_'):
    items = {}
    
    if obj is None:
        return {prefix: ''} if prefix else {}
    
    if not isinstance(obj, (dict, list)):
        return {prefix: obj} if prefix else {}
    
    if isinstance(obj, list):
        if len(obj) == 0:
            return {prefix: ''} if prefix else {}
        
        if not isinstance(obj[0], (dict, list)):
            return {prefix: ', '.join(map(str, obj))} if prefix else {}
        
        sample = obj[0]
        if isinstance(sample, dict):
            for key, value in sample.items():
                clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
                if prefix:
                    new_key = f"{prefix}{delimiter}[*]{delimiter}{clean_key}"
                else:
                    new_key = f"[*]{delimiter}{clean_key}"
                
                if isinstance(value, (dict, list)):
                    nested = flatten_json(value, new_key, max_depth - 1, delimiter)
                    items.update(nested)
                elif value is None:
                    items[new_key] = ''
                else:
                    items[new_key] = value
        return items
    
    if max_depth <= 0:
        return {prefix: json.dumps(obj, ensure_ascii=False)} if prefix else {}
    
    for key, value in obj.items():
        clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
        new_key = f"{prefix}{delimiter}{clean_key}" if prefix else clean_key
        
        if isinstance(value, (dict, list)):
            items.update(flatten_json(value, new_key, max_depth - 1, delimiter))
        elif value is None:
            items[new_key] = ''
        else:
            items[new_key] = value
    
    return items


def fetch_ip_data() -> list:
    print("📡 Запрос к IP API...")
    
    if not IP_API_USER or not IP_API_PASS:
        print("❌ Ошибка: IP_API_USER или IP_API_PASS не заданы в .env файле")
        return []
    
    client = APIClient(IP_API_URL)
    auth_header = get_auth_header(IP_API_USER, IP_API_PASS)
    client.session.headers.update({
        "Authorization": auth_header,
        "Content-Type": "application/json"
    })
    
    response = client.get("")
    
    if not response:
        print("❌ Не удалось получить данные от IP API")
        return []
    
    data_list = []
    if isinstance(response, list):
        data_list = response
    elif isinstance(response, dict):
        for key in ['data', 'items', 'results', 'summary', 'ur_summary']:
            if key in response and isinstance(response[key], list):
                data_list = response[key]
                break
        if not data_list:
            data_list = [response]
    
    print(f"✅ Получено записей: {len(data_list)}")
    return data_list


def process_ip_data(data_list: list) -> tuple:
    print("🔓 Декодирование полей...")
    
    all_rows = []
    all_headers = []
    
    for idx, item in enumerate(data_list):
        if not isinstance(item, dict):
            continue
        
        # Базовые поля
        base_fields = {
            'id': item.get('id', ''),
            'name': item.get('name', ''),
            'is_enable_push_price_to_ms': item.get('is_enable_push_price_to_ms', ''),
        }
        
        # === ОБРАБОТКА КАТЕГОРИЙ (массив) ===
        categories = item.get('categories', [])
        if isinstance(categories, list) and categories:
            category_ids = []
            category_names = []
            
            for cat in categories:
                if isinstance(cat, dict):
                    cat_id = cat.get('id', '')
                    cat_name = cat.get('name', '')
                    if cat_id:
                        category_ids.append(cat_id)
                        category_names.append(cat_name)
            
            base_fields['categories_[*]_id'] = ', '.join(category_ids) if category_ids else ''
            base_fields['categories_[*]_name'] = ', '.join(category_names) if category_names else ''
        else:
            base_fields['categories_[*]_id'] = ''
            base_fields['categories_[*]_name'] = ''
        
        # === ОБРАБОТКА ATTRIBUTES (массив) ===
        attributes = item.get('attributes', [])
        if isinstance(attributes, list) and attributes:
            # Сохраняем как JSON строку для последующей обработки
            base_fields['attributes'] = json.dumps(attributes, ensure_ascii=False)
        else:
            base_fields['attributes'] = ''
        
        # Декодируем остальные поля
        decoded_fields = {}
        for field in ['ms', 'multipliers', 'schedule', 'prices']:
            value = item.get(field, '')
            
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    flattened = flatten_json(parsed, prefix=field, max_depth=3)
                    decoded_fields.update(flattened)
                except:
                    decoded_fields[field] = value
            elif isinstance(value, (dict, list)):
                flattened = flatten_json(value, prefix=field, max_depth=3)
                decoded_fields.update(flattened)
            else:
                decoded_fields[field] = value
        
        # Объединяем базовые + декодированные поля
        row_dict = {}
        for key in ['id', 'name', 'is_enable_push_price_to_ms', 'categories_[*]_id', 'categories_[*]_name', 'attributes']:
            if key in base_fields:
                row_dict[key] = base_fields[key]
        
        for key in sorted(decoded_fields.keys()):
            if key not in row_dict:
                row_dict[key] = decoded_fields[key]
        
        if idx == 0:
            all_headers = list(row_dict.keys())
            print(f"✅ Всего колонок: {len(all_headers)}")
        
        row = [row_dict.get(h, '') for h in all_headers]
        all_rows.append(row)
    
    # Фильтр по id
    before = len(all_rows)
    all_rows = [r for r in all_rows if r[0] and str(r[0]).strip()]
    print(f"🗑️ Отфильтровано строк: {before} → {len(all_rows)}")
    
    return all_rows, all_headers


def main():
    print("=" * 60)
    print(" ВЫГРУЗКА ИЗ ПРОЕКТА ИНТЕГРАЦИИ (ПИ)")
    print("=" * 60)
    
    data_list = fetch_ip_data()
    
    if not data_list:
        print("⚠️ Нет данных для выгрузки")
        sys.exit(0)
    
    rows, headers = process_ip_data(data_list)
    
    if not rows:
        print("⚠️ Не удалось обработать данные")
        sys.exit(0)
    
    output_file = OUTPUT_DIR / "ip_mapping.csv"
    save_to_csv(rows, headers, output_file)
    
    print("\n" + "=" * 60)
    print("✅ ВЫГРУЗКА ЗАВЕРШЕНА!")
    print(f"📁 Файл: {output_file}")
    print(f"📊 Строк: {len(rows)}, Колонок: {len(headers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
