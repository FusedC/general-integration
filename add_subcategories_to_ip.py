#!/usr/bin/env python3
"""
Добавляет столбец с субкатегориями в ip_mapping.csv
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: кэширование + параллельные запросы
"""
import sys
import csv
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR


def extract_folder_id_from_url(url):
    """Извлекает UUID из URL МойСклад"""
    if not url:
        return None
    parts = url.strip().split('/')
    return parts[-1] if parts else None


def get_folder_data(folder_id):
    """Получает данные папки из МойСклад API"""
    if not folder_id:
        return None
    
    url = f"{MS_BASE_URL}/entity/productfolder/{folder_id}"
    headers = {
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            path_name = data.get('pathName', '')
            name = data.get('name', '')
            full_path = f"{path_name}/{name}" if path_name else name
            return full_path
        else:
            return None
    except Exception:
        return None


def main():
    print("=" * 60)
    print(" ДОБАВЛЕНИЕ СУБКАТЕГОРИЙ В IP_MAPPING.CSV")
    print(" Оптимизированная версия")
    print("=" * 60)
    
    if not MS_TOKEN:
        print("❌ Ошибка: MS_TOKEN не задан в .env файле")
        sys.exit(1)
    
    input_file = OUTPUT_DIR / "ip_mapping.csv"
    if not input_file.exists():
        print(f"❌ Файл {input_file} не найден")
        sys.exit(1)
    
    print(f"📖 Чтение {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    if not rows:
        print("⚠️ Файл пуст")
        sys.exit(0)
    
    print(f"✅ Загружено {len(rows)} кампаний")
    
    # Находим все УНИКАЛЬНЫЕ ID категорий
    print("\n🔍 Поиск уникальных категорий...")
    unique_folder_ids = set()
    
    for row in rows:
        folder_urls = row.get('categories_[*]_id', '')
        if ',' in folder_urls:
            for url in folder_urls.split(','):
                folder_id = extract_folder_id_from_url(url.strip())
                if folder_id:
                    unique_folder_ids.add(folder_id)
        else:
            folder_id = extract_folder_id_from_url(folder_urls)
            if folder_id:
                unique_folder_ids.add(folder_id)
    
    print(f"✅ Найдено {len(unique_folder_ids)} уникальных категорий")
    
    # Получаем названия папок из МойСклад (ПАРАЛЛЕЛЬНО)
    print("\n🔄 Запрос субкатегорий из МойСклад (параллельно)...")
    folder_paths_cache = {}
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_id = {
            executor.submit(get_folder_data, folder_id): folder_id 
            for folder_id in unique_folder_ids
        }
        
        for i, future in enumerate(as_completed(future_to_id), 1):
            folder_id = future_to_id[future]
            if i % 50 == 0:
                print(f"   Прогресс: {i}/{len(unique_folder_ids)}")
            
            try:
                folder_path = future.result()
                folder_paths_cache[folder_id] = folder_path if folder_path else ''
            except Exception:
                folder_paths_cache[folder_id] = ''
    
    # Добавляем субкатегории ко всем кампаниям
    print("\n💾 Применение субкатегорий к кампаниям...")
    
    new_fieldnames = list(fieldnames) + ['subcategory']
    
    for row in rows:
        folder_urls = row.get('categories_[*]_id', '')
        
        all_subcats = []
        
        if ',' in folder_urls:
            urls_list = [u.strip() for u in folder_urls.split(',')]
        else:
            urls_list = [folder_urls]
        
        for url in urls_list:
            folder_id = extract_folder_id_from_url(url)
            if folder_id and folder_id in folder_paths_cache:
                subcat = folder_paths_cache[folder_id]
                if subcat and subcat not in all_subcats:
                    all_subcats.append(subcat)
        
        row['subcategory'] = '; '.join(all_subcats) if all_subcats else ''
    
    # Перезаписываем ip_mapping.csv с новой колонкой
    print(f"\n💾 Сохранение в {input_file}...")
    with open(input_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Файл {input_file} обновлён")
    
    # Показываем статистику
    with_subcats = sum(1 for r in rows if r.get('subcategory'))
    print(f"\n📊 Статистика:")
    print(f"   Всего кампаний: {len(rows)}")
    print(f"   С субкатегориями: {with_subcats}")
    print(f"   Без субкатегорий: {len(rows) - with_subcats}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
