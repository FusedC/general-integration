#!/usr/bin/env python3
"""
Быстрое получение подкатегорий из МойСклад
Версия: поиск по pathName + parent
"""
import sys
import csv
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR
from utils.api_client import APIClient


def extract_folder_id_from_url(url):
    if not url:
        return None
    parts = url.strip().split('/')
    return parts[-1] if parts else None


def get_folder_subcategories(client, folder_id, folder_name):
    """Получает все подкатегории двумя способами"""
    if not folder_id:
        return []
    
    print(f"\n   🔍 Поиск подкатегорий для: {folder_name} (ID: {folder_id})")
    
    # Загружаем все папки с пагинацией
    all_folders = []
    offset = 0
    limit = 1000
    
    while True:
        response = client.get(
            "/entity/productfolder",
            params={"limit": limit, "offset": offset}
        )
        
        if not response or 'rows' not in response:
            break
        
        folders = response['rows']
        all_folders.extend(folders)
        
        if len(folders) < limit:
            break
        
        offset += limit
    
    print(f"   📁 Всего папок в системе: {len(all_folders)}")
    
    subcategories = []
    found_by_parent = 0
    found_by_path = 0
    
    for folder in all_folders:
        folder_id_current = folder.get('id', '')
        path_name = folder.get('pathName', '')
        name = folder.get('name', '')
        full_name = f"{path_name}/{name}" if path_name else name
        
        # СПОСОБ 1: Ищем по parent
        parent = folder.get('parent')
        if parent:
            parent_meta = parent.get('meta', {})
            parent_href = parent_meta.get('href', '')
            parent_id = parent_href.split('/')[-1] if parent_href else ''
            
            if parent_id == folder_id:
                subcategories.append(full_name)
                found_by_parent += 1
                print(f"      ✓ Найдена (parent): {full_name}")
        
        # СПОСОБ 2: Ищем по pathName (если папка находится внутри)
        elif path_name and folder_id_current != folder_id:
            # Проверяем, начинается ли pathName с имени нашей папки
            if path_name == folder_name or path_name.endswith(f"/{folder_name}"):
                # Проверяем, что это не сама папка
                if full_name != folder_name:
                    if full_name not in subcategories:
                        subcategories.append(full_name)
                        found_by_path += 1
                        print(f"      ✓ Найдена (path): {full_name}")
    
    print(f"   ✅ Найдено подкатегорий: {len(subcategories)} (parent: {found_by_parent}, path: {found_by_path})")
    return sorted(list(set(subcategories)))


def main():
    print("=" * 60)
    print(" БЫСТРОЕ ПОЛУЧЕНИЕ ПОДКАТЕГОРИЙ ИЗ МОЙ СКЛАД")
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
    
    # Находим все УНИКАЛЬНЫЕ категории
    print("\n🔍 Поиск уникальных категорий...")
    unique_categories = {}
    
    for row in rows:
        folder_url = row.get('categories_[*]_id', '')
        folder_id = extract_folder_id_from_url(folder_url)
        category_name = row.get('categories_[*]_name', '')
        
        if folder_id and folder_id not in unique_categories:
            unique_categories[folder_id] = {
                'url': folder_url,
                'name': category_name,
                'count': 0
            }
        
        if folder_id:
            unique_categories[folder_id]['count'] += 1
    
    print(f"✅ Найдено {len(unique_categories)} уникальных категорий")
    
    # Запрашиваем подкатегории
    print("\n🔄 Запрос подкатегорий из МойСклад...")
    
    client = APIClient(MS_BASE_URL)
    client.session.headers.update({
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    })
    
    subcategories_cache = {}
    
    for i, (folder_id, cat_info) in enumerate(unique_categories.items(), 1):
        print(f"\n[{i}/{len(unique_categories)}] Обработка: {cat_info['name']}")
        subcats = get_folder_subcategories(client, folder_id, cat_info['name'])
        subcategories_cache[folder_id] = subcats
    
    # Применяем подкатегории ко всем кампаниям
    print("\n💾 Применение подкатегорий к кампаниям...")
    
    new_fieldnames = list(fieldnames) + ['categories_subcategories']
    
    for row in rows:
        folder_url = row.get('categories_[*]_id', '')
        folder_id = extract_folder_id_from_url(folder_url)
        
        if folder_id and folder_id in subcategories_cache:
            subcats = subcategories_cache[folder_id]
            row['categories_subcategories'] = '; '.join(subcats) if subcats else ''
        else:
            row['categories_subcategories'] = ''
    
    output_file = OUTPUT_DIR / "ip_mapping_with_subcategories.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ Сохранено в {output_file}")
    
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
        print(f"   Подкатегории: {len(subcats.split('; ')) if subcats else 0}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
