#!/usr/bin/env python3
"""
Получение названий подкатегорий из МойСклад для кампаний из Проекта Интеграции
"""
import sys
import csv
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR


def extract_folder_id_from_url(url):
    """Извлекает UUID из URL МойСклад"""
    if not url:
        return None
    parts = url.strip().split('/')
    return parts[-1] if parts else None


def get_folder_name(folder_id):
    """Получает название папки из МойСклад API"""
    if not folder_id:
        return ''
    
    url = f"{MS_BASE_URL}/entity/productfolder/{folder_id}"
    headers = {
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('name', '')
        else:
            print(f"   ⚠️ Ошибка {response.status_code} для {folder_id}")
            return ''
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return ''


def main():
    print("=" * 60)
    print(" ПОЛУЧЕНИЕ ПОДКАТЕГОРИЙ ИЗ МОЙ СКЛАД")
    print("=" * 60)
    
    if not MS_TOKEN:
        print("❌ Ошибка: MS_TOKEN не задан в .env файле")
        sys.exit(1)
    
    # Читаем ip_mapping.csv
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
        folder_url = row.get('categories_[*]_id', '')
        folder_id = extract_folder_id_from_url(folder_url)
        if folder_id:
            unique_folder_ids.add(folder_id)
    
    print(f"✅ Найдено {len(unique_folder_ids)} уникальных категорий")
    
    # Получаем названия папок из МойСклад
    print("\n🔄 Запрос названий подкатегорий из МойСклад...")
    folder_names_cache = {}
    
    for i, folder_id in enumerate(sorted(unique_folder_ids), 1):
        if i % 50 == 0:
            print(f"   Прогресс: {i}/{len(unique_folder_ids)}")
        
        folder_name = get_folder_name(folder_id)
        folder_names_cache[folder_id] = folder_name
        print(f"   [{i}] {folder_id[:8]}... → {folder_name}")
    
    # Добавляем подкатегории ко всем кампаниям
    print("\n💾 Применение подкатегорий к кампаниям...")
    
    new_fieldnames = list(fieldnames) + ['subcategory_name']
    
    for row in rows:
        folder_url = row.get('categories_[*]_id', '')
        folder_id = extract_folder_id_from_url(folder_url)
        
        if folder_id and folder_id in folder_names_cache:
            row['subcategory_name'] = folder_names_cache[folder_id]
        else:
            row['subcategory_name'] = ''
    
    # Сохраняем результат
    output_file = OUTPUT_DIR / "ip_mapping_with_subcategories.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ Сохранено в {output_file}")
    
    # Показываем статистику
    with_subcats = sum(1 for r in rows if r['subcategory_name'])
    print(f"\n📊 Статистика:")
    print(f"   Всего кампаний: {len(rows)}")
    print(f"   С подкатегориями: {with_subcats}")
    print(f"   Без подкатегорий: {len(rows) - with_subcats}")
    
    # Показываем примеры
    print("\n" + "=" * 60)
    print(" ПРИМЕРЫ:")
    print("=" * 60)
    
    examples = [row for row in rows if row.get('subcategory_name')][:10]
    for row in examples:
        campaign = row.get('name', 'N/A')[:50]
        parent_cat = row.get('categories_[*]_name', 'N/A')
        subcat = row.get('subcategory_name', 'N/A')
        
        print(f"\n📁 Кампания: {campaign}")
        print(f"   Родительская категория: {parent_cat}")
        print(f"   Подкатегория: {subcat}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
