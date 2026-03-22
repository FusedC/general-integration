#!/usr/bin/env python3
"""
Выгрузка товаров из МойСклад
Версия с ПАРАЛЛЕЛЬНЫМИ запросами (как в оригинале)
"""
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

from config import MS_TOKEN, MS_BASE_URL, OUTPUT_DIR
from utils.api_client import APIClient
from utils.storage import save_to_csv


# === ФИЛЬТРЫ ИЗ ОРИГИНАЛЬНОГО СКРИПТА ===
ALLOWED_CATEGORIES = [
    "1 - Техника, Блок: 1, 2, 02А, 3, 4",
    "2 - Бытовая техника Блок: 5, 3A, 10, 6 крупная тех. Xiaomi"
]

PRODUCT_LIMIT = 100
BATCH_SIZE = 5  # Параллельных запросов одновременно


def format_price(value):
    """Форматирует цену: убирает .0 если число целое"""
    if value is None or value == '':
        return ''
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return round(value, 2)
    return value


def load_folders(client):
    """Загружает все папки товаров один раз"""
    print("📁 Загрузка папок товаров...")
    folder_map = {}
    offset = 0
    
    while True:
        response = client.get(
            "/entity/productfolder",
            params={"limit": 1000, "offset": offset}
        )
        
        if not response or 'rows' not in response:
            break
        
        for folder in response['rows']:
            folder_id = folder.get('id', '')
            path_name = folder.get('pathName', '')
            name = folder.get('name', '')
            folder_map[folder_id] = f"{path_name}/{name}" if path_name else name
        
        if len(response['rows']) < 1000:
            break
        
        offset += 1000
    
    print(f"✅ Всего папок: {len(folder_map)}")
    return folder_map


def get_total_count(client):
    """Получает общее количество товаров"""
    response = client.get(
        "/entity/product",
        params={"limit": 1, "filter": "archived=false"}
    )
    
    if response and 'meta' in response:
        return response['meta'].get('size', 0)
    return 0


def fetch_batch(client, offset, limit):
    """Делает один запрос к API (для параллельного выполнения)"""
    response = client.get(
        "/entity/product",
        params={
            "limit": limit,
            "offset": offset,
            "filter": "archived=false",
            "expand": "salePrices"
        }
    )
    return {"offset": offset, "response": response}


def fetch_products(client, folder_map, limit=PRODUCT_LIMIT):
    """Выгружает товары с ПАРАЛЛЕЛЬНЫМИ запросами"""
    total_count = get_total_count(client)
    print(f"📦 Всего товаров в базе (archived=false): {total_count}")
    
    all_products = []
    seen_ids = set()
    total_skipped = 0
    
    start_time = time.time()
    offset = 0
    batch_num = 0
    
    while offset < total_count:
        batch_num += 1
        batch_start = time.time()
        
        # Формируем пачку оффсетов для параллельной загрузки
        batch_offsets = []
        for i in range(BATCH_SIZE):
            batch_offset = offset + i * limit
            if batch_offset >= total_count:
                break
            batch_offsets.append(batch_offset)
        
        if not batch_offsets:
            break
        
        print(f"\n🔄 Пачка #{batch_num}: offsets {batch_offsets[0]} - {batch_offsets[-1] + limit}")
        
        # === ПАРАЛЛЕЛЬНОЕ ВЫПОЛНЕНИЕ ЗАПРОСОВ ===
        results = []
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {
                executor.submit(fetch_batch, client, off, limit): off 
                for off in batch_offsets
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"   ❌ Ошибка запроса: {e}")
        
        # Обрабатываем результаты
        batch_products = []
        for result in sorted(results, key=lambda x: x['offset']):
            response = result['response']
            current_offset = result['offset']
            
            if not response or 'rows' not in response:
                print(f"   ⚠️ Пустой ответ на offset={current_offset}")
                continue
            
            for product in response['rows']:
                # Извлечение атрибутов
                attr = {}
                for a in product.get('attributes', []):
                    if a.get('value') is not None:
                        value = a['value']
                        if isinstance(value, dict) and 'name' in value:
                            attr[a['name']] = value['name']
                        else:
                            attr[a['name']] = value
                
                # ФИЛЬТР 1: Снят с производства
                if attr.get("Снят с производства") is True:
                    total_skipped += 1
                    continue
                
                # ФИЛЬТР 2: Категория закупки
                category = attr.get("Категория закупки", "")
                if category not in ALLOWED_CATEGORIES:
                    total_skipped += 1
                    continue
                
                # ФИЛЬТР 3: Защита от дублей
                product_id = product.get('id', '')
                if product_id in seen_ids:
                    total_skipped += 1
                    continue
                seen_ids.add(product_id)
                
                # Извлечение данных
                code = product.get('code', '')
                name = product.get('name', '')
                
                group = ''
                if product.get('productFolder') and product['productFolder'].get('meta'):
                    folder_id = product['productFolder']['meta']['href'].split('/')[-1]
                    group = folder_map.get(folder_id, '')
                
                buy_price = product.get('buyPrice', {}).get('value', 0) / 100 if product.get('buyPrice') else 0
                
                prices = {'СМР': '', 'МСК': '', 'ЕКБ': ''}
                for p in product.get('salePrices', []):
                    if not p.get('priceType'):
                        continue
                    val = p.get('value', 0) / 100
                    price_name = p['priceType'].get('name', '')
                    if price_name == "Цена (Самара)":
                        prices['СМР'] = val
                    elif price_name == "Цена (Москва)":
                        prices['МСК'] = val
                    elif price_name == "Цена (Екатеринбург)":
                        prices['ЕКБ'] = val
                
                valid_prices = [v for v in prices.values() if v and v > 0]
                min_price = min(valid_prices) if valid_prices else ''
                
                row = [
                    code,
                    name,
                    group,
                    format_price(buy_price),
                    format_price(min_price),
                    format_price(prices['СМР']),
                    format_price(prices['МСК']),
                    format_price(prices['ЕКБ']),
                    attr.get("ABC-анализ (СМР)", ''),
                    attr.get("ABC-анализ (МСК)", ''),
                    attr.get("ABC-анализ (ЕКБ)", ''),
                    attr.get("Товар дня (СМР)", ''),
                    attr.get("Товар дня (МСК)", ''),
                    attr.get("Товар дня (ЕКБ)", ''),
                    attr.get("Парсинг работает (СМР)", ''),
                    attr.get("Парсинг работает (МСК)", ''),
                    attr.get("Парсинг работает (ЕКБ)", ''),
                    attr.get("Договор о цене", ''),
                    attr.get("Ручное РЦ", ''),
                    attr.get("Бывший D сегмент", ''),
                    attr.get("Новинка", ''),
                    attr.get("Новинка: дата поставки неснижаемого остатка", ''),
                    category
                ]
                
                batch_products.append(row)
        
        all_products.extend(batch_products)
        
        # Статистика пачки
        batch_time = time.time() - batch_start
        print(f"   ✅ Загружено: {len(batch_products)} | Время: {batch_time:.1f}с | Скорость: {len(batch_offsets)/batch_time:.1f} запросов/с")
        
        # Двигаем оффсет
        offset += len(batch_offsets) * limit
        
        # Небольшая пауза между пачками (чтобы не превысить rate limit)
        if offset < total_count:
            time.sleep(0.5)
    
    elapsed = time.time() - start_time
    print(f"\n📊 Итого: загружено {len(all_products)}, пропущено {total_skipped}")
    print(f"⏱️ Общее время: {elapsed:.0f}с ({elapsed/60:.1f} мин)")
    return all_products


def main():
    """Основная функция выгрузки"""
    print("=" * 60)
    print(" ВЫГРУЗКА ИЗ МОЙ СКЛАД (ПАРАЛЛЕЛЬНЫЕ ЗАПРОСЫ)")
    print("=" * 60)
    
    if not MS_TOKEN:
        print("❌ Ошибка: MS_TOKEN не задан в .env файле")
        sys.exit(1)
    
    # Инициализация клиента
    client = APIClient(MS_BASE_URL)
    client.session.headers.update({
        "Authorization": f"Bearer {MS_TOKEN}",
        "Accept-Encoding": "gzip"
    })
    
    # Загружаем папки
    folder_map = load_folders(client)
    
    # Выгружаем товары с параллельными запросами
    products = fetch_products(client, folder_map)
    
    if not products:
        print("⚠️ Не загружено ни одного товара")
        sys.exit(0)
    
    # Заголовки
    headers = [
        "Код", "Наименование", "Группа", "Закуп", "Мин цена",
        "Цена СМР", "Цена МСК", "Цена ЕКБ",
        "СМР АВС", "МСК АВС", "ЕКБ АВС",
        "ТД СМР", "ТД МСК", "ТД ЕКБ",
        "Парсинг работает СМР", "Парсинг работает МСК", "Парсинг работает ЕКБ",
        "Договор о цене", "Ручное РЦ", "Бывший D",
        "Новинка", "Новинка: дата поставки неснижаемого остатка",
        "Категория закупки"
    ]
    
    # Сохраняем в CSV
    output_file = OUTPUT_DIR / "ms_products.csv"
    save_to_csv(products, headers, output_file)
    
    print("\n" + "=" * 60)
    print("✅ ВЫГРУЗКА ЗАВЕРШЕНА!")
    print(f"📁 Файл: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
