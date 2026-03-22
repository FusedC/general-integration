#!/usr/bin/env python3
"""
Получение подкатегорий из МойСклад для кампаний из Проекта Интеграции
Версия: поиск по pathName (быстро и надёжно)
"""
import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR
from utils.api_client import APIClient


def get_all_folders(client):
    """Получает ВСЕ папки товаров из МойСклад"""
    print("📁 Загрузка всех папок из МойСклад...")
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
        print(f"   Загружено: {len(all_folders)} папок")
        
        if len(folders) < limit:
            break
        
        offset += limit
    
    print(f"✅ Всего папок: {len(all_folders)}")
    return all_folders


def find_subcategories_by_path(all_folders, category_name):
    """Находит все папки где pathName == category_name"""
    subcategories = []
    
    for folder in all_folders:
        path_name = folder.get('pathName', '')
        name = folder.get('name', '')
        full_name = f"{path_name}/{name}" if path_name else name
        
        # Ищем папки где pathName совпадает с именем категории
        # И исключаем саму категорию
        if path_name == category_name and name != category_name:
            if full_name not in subcategories:
                subcategories.append(full_name)
    
    return sorted(list(set(subcategories)))


def main():
    print("=" * 60)
    print(" ПОЛУЧЕНИЕ ПОДКАТЕГОРИЙ ДЛЯ ПРОЕКТА ИНТЕГРАЦИИ")
    print(" Версия: поиск по pathName")
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
    
    # Находим все УНИКАЛЬНЫЕ категории по имени
    print("\n🔍 Поиск уникальных категорий по имени...")
    unique_category_names = {}
    
    for row in rows:
        category_name = row.get('categories_[*]_name', '').strip()
        if category_name and category_name not in unique_category_names:
            unique_category_names[category_name] = 0
        if category_name:
            unique_category_names[category_name] += 1
    
    print(f"✅ Найдено {len(unique_category_names)} уникальных категорий")
    
    # Инициализация клиента МойСклад
    client = APIClient(MS_BASE_URL)
    client.session.headers.update({
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    })
    
    # Загружаем ВСЕ папки один раз
    all_folders = get_all_folders(client)
    
    # Получаем подкатегории для каждой уникальной категории
    print("\n🔍 Поиск подкатегорий по pathName...")
    subcategories_cache = {}
    
    for i, (category_name, count) in enumerate(unique_category_names.items(), 1):
        print(f"\n[{i}/{len(unique_category_names)}] {category_name} (используется в {count} кампаниях)")
        subcats = find_subcategories_by_path(all_folders, category_name)
        subcategories_cache[category_name] = subcats
        print(f"   ✅ Найдено подкатегорий: {len(subcats)}")
        if subcats:
            for subcat in subcats[:5]:  # Показываем первые 5
                print(f"      • {subcat}")
            if len(subcats) > 5:
                print(f"      ... и ещё {len(subcats) - 5}")
    
    # Применяем подкатегории ко всем кампаниям
    print("\n💾 Применение подкатегорий к кампаниям...")
    
    new_fieldnames = list(fieldnames) + ['categories_subcategories']
    
    for row in rows:
        category_name = row.get('categories_[*]_name', '').strip()
        
        if category_name and category_name in subcategories_cache:
            subcats = subcategories_cache[category_name]
            row['categories_subcategories'] = '; '.join(subcats) if subcats else ''
        else:
            row['categories_subcategories'] = ''
    
    # Сохраняем результат
    output_file = OUTPUT_DIR / "ip_mapping_with_subcategories.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ Сохранено в {output_file}")
    
    # Показываем статистику
    total_with_subcats = sum(1 for row in rows if row.get('categories_subcategories'))
    print(f"\n📊 Статистика:")
    print(f"   Всего кампаний: {len(rows)}")
    print(f"   С подкатегориями: {total_with_subcats}")
    print(f"   Без подкатегорий: {len(rows) - total_with_subcats}")
    
    # Показываем примеры
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
        for subcat in subcats.split('; ')[:5]:
            if subcat:
                print(f"      • {subcat}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
