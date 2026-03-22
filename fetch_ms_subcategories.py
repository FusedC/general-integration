#!/usr/bin/env python3
"""
Получение всех подкатегорий из МойСклад для кампаний из Проекта Интеграции
Исправленная версия
"""
import sys
import csv
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR
from utils.api_client import APIClient


def extract_folder_id_from_url(url):
    """Извлекает ID папки из URL МойСклад"""
    if not url:
        return None
    parts = url.strip().split('/')
    return parts[-1] if parts else None


def get_folder_subcategories(client, folder_id):
    """Получает все подкатегории (дочерние папки) для указанной папки"""
    if not folder_id:
        return []
    
    response = client.get(
        "/entity/productfolder",
        params={"limit": 1000, "offset": 0}
    )
    
    if not response or 'rows' not in response:
        return []
    
    subcategories = []
    for folder in response['rows']:
        if folder.get('parent'):
            parent_meta = folder['parent'].get('meta', {})
            parent_href = parent_meta.get('href', '')
            
            if folder_id in parent_href:
                path_name = folder.get('pathName', '')
                name = folder.get('name', '')
                full_name = f"{path_name}/{name}" if path_name else name
                subcategories.append(full_name)
    
    return sorted(list(set(subcategories)))


def main():
    print("=" * 60)
    print(" ПОЛУЧЕНИЕ ПОДКАТЕГОРИЙ ИЗ МОЙ СКЛАД")
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
    
    if 'categories_[*]_id' not in fieldnames:
        print("❌ Колонка 'categories_[*]_id' не найдена в файле")
        sys.exit(1)
    
    client = APIClient(MS_BASE_URL)
    client.session.headers.update({
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    })
    
    new_fieldnames = list(fieldnames) + ['categories_subcategories']
    
    print("\n🔍 Получение подкатегорий...")
    processed = 0
    
    for i, row in enumerate(rows, 1):
        folder_url = row.get('categories_[*]_id', '')
        folder_id = extract_folder_id_from_url(folder_url)
        
        if folder_id:
            subcategories = get_folder_subcategories(client, folder_id)
            row['categories_subcategories'] = '; '.join(subcategories) if subcategories else ''
            processed += 1
            
            if i % 50 == 0:
                print(f"   Прогресс: {i}/{len(rows)}")
        else:
            row['categories_subcategories'] = ''
    
    print(f"\n✅ Обработано {processed} кампаний")
    
    output_file = OUTPUT_DIR / "ip_mapping_with_subcategories.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n💾 Сохранено в {output_file}")
    
    print("\n" + "=" * 60)
    print(" ПРИМЕРЫ ПОДКАТЕГОРИЙ:")
    print("=" * 60)
    
    examples = [row for row in rows if row.get('categories_subcategories')][:5]
    for row in examples:
        campaign_name = row.get('name', 'N/A')[:50]
        category_name = row.get('categories_[*]_name', 'N/A')
        subcats = row.get('categories_subcategories', '')
        
        print(f"\n📁 Кампания: {campaign_name}")
        print(f"   Категория: {category_name}")
        print(f"   Подкатегории:")
        for subcat in subcats.split('; '):
            if subcat:
                print(f"      • {subcat}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
