#!/usr/bin/env python3
"""
Выгрузка отчётов из MarketParser
Версия: МАКСИМАЛЬНАЯ СКОРОСТЬ (без задержек, максимум параллелизма)
"""
import sys
import asyncio
import aiohttp
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import MP_API_KEY, MP_BASE_URL, OUTPUT_DIR
from utils.storage import save_to_csv


# === НАСТРОЙКИ СКОРОСТИ ===
MAX_WORKERS = 100  # Максимум параллельных запросов
REQUESTS_PER_PAGE = 100  # Продуктов на страницу
MAX_PAGES_PER_CAMP = 50  # Макс страниц на кампанию
REQUEST_TIMEOUT = 60  # Таймаут запроса


def extract_city_from_name(name):
    if not name:
        return ''
    name_lower = name.lower()
    if 'смр' in name_lower or 'самара' in name_lower:
        return 'Самара'
    elif 'мск' in name_lower or 'москва' in name_lower:
        return 'Москва'
    elif 'екб' in name_lower or 'екатеринбург' in name_lower:
        return 'Екатеринбург'
    return ''


async def fetch_with_retry(session, url, headers, max_retries=2):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    await asyncio.sleep(1 * (2 ** attempt))
                    continue
                else:
                    return None
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(0.5 * (2 ** attempt))
    return None


async def get_campaigns(session, api_key):
    campaigns = []
    page = 1
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    
    while page <= 50:
        url = f"{MP_BASE_URL}/campaigns.json?per_page=100&page={page}"
        response = await fetch_with_retry(session, url, headers)
        
        if not response or 'response' not in response:
            break
        
        camp_list = response['response'].get('campaigns', [])
        if not camp_list:
            break
        
        for camp in camp_list:
            campaigns.append({
                'id': camp.get('id', ''),
                'name': camp.get('name', ''),
                'ready': camp.get('readyToCreateReports', False)
            })
        
        total = response['response'].get('total', 0)
        if len(campaigns) >= total:
            break
        
        page += 1
    
    return campaigns


async def get_last_report(session, api_key, campaign_id):
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    
    for page in [1, 2]:
        url = f"{MP_BASE_URL}/campaigns/{campaign_id}/reports.json?per_page=20&page={page}"
        response = await fetch_with_retry(session, url, headers)
        
        if not response or 'response' not in response:
            continue
        
        reports = response['response'].get('reports', [])
        for report in reports:
            if report.get('isSuccessfullyFinished') and report.get('status') == 'OK':
                return report
    
    return None


async def get_report_results(session, api_key, campaign_id, report_id):
    products = []
    page = 1
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    
    while page <= MAX_PAGES_PER_CAMP:
        url = f"{MP_BASE_URL}/campaigns/{campaign_id}/reports/{report_id}/results.json?per_page={REQUESTS_PER_PAGE}&page={page}"
        response = await fetch_with_retry(session, url, headers)
        
        if not response or 'response' not in response:
            break
        
        prod_list = response['response'].get('products', [])
        if not prod_list:
            break
        
        products.extend(prod_list)
        
        total = response['response'].get('total', 0)
        if len(products) >= total:
            break
        
        page += 1
    
    return products


def process_product(product, campaign_info, report_info, update_time):
    city = extract_city_from_name(campaign_info.get('name', ''))
    
    offers = product.get('offers', [])
    valid_offers = []
    for offer in offers:
        if offer and offer.get('price') is not None:
            price = float(offer.get('price', 0))
            if price > 0:
                valid_offers.append({
                    'shop': offer.get('shopName', ''),
                    'price': price,
                    'link': offer.get('linkToOffer', '')
                })
    
    valid_offers.sort(key=lambda x: x['price'])
    
    row = [
        city,
        campaign_info.get('name', ''),
        campaign_info.get('id', ''),
        report_info.get('id', ''),
        report_info.get('startedAt', '')[:10] if report_info.get('startedAt') else '',
        report_info.get('startedAt', '')[11:19] if report_info.get('startedAt') else '',
        '',
        update_time,
        product.get('name', ''),
        product.get('ourId', ''),
        product.get('ourCost', ''),
        product.get('minPrice', ''),
        product.get('averagePrice', ''),
        product.get('yandexRegionName', ''),
    ]
    
    for i in range(12):
        if i < len(valid_offers):
            row.append(valid_offers[i]['shop'])
            row.append(valid_offers[i]['link'])
            row.append(valid_offers[i]['price'])
        else:
            row.extend(['', '', ''])
    
    return row


async def process_campaign_async(session, api_key, camp, update_time, semaphore):
    async with semaphore:
        try:
            report = await get_last_report(session, api_key, camp['id'])
            if not report:
                return []
            
            products = await get_report_results(session, api_key, camp['id'], report['id'])
            if not products:
                return []
            
            rows = []
            for product in products:
                row = process_product(product, camp, report, update_time)
                rows.append(row)
            
            return rows
        except Exception as e:
            print(f"   ❌ {camp['name'][:50]}: {e}")
            return []


async def fetch_all_campaigns_async(api_key, campaigns, update_time):
    connector = aiohttp.TCPConnector(
        limit=MAX_WORKERS,
        limit_per_host=MAX_WORKERS,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(MAX_WORKERS)
        
        tasks = [
            process_campaign_async(session, api_key, camp, update_time, semaphore)
            for camp in campaigns
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_rows = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_rows.extend(result)
            elif isinstance(result, Exception):
                print(f"   ❌ Ошибка кампании {i}: {result}")
        
        return all_rows


def fetch_mp_reports(max_campaigns=None):
    print("📡 Подключение к MarketParser API...")
    
    if not MP_API_KEY:
        print("❌ Ошибка: MP_API_KEY не задан в .env файле")
        return []
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        async def get_campaigns_wrapper():
            connector = aiohttp.TCPConnector(
                limit=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            async with aiohttp.ClientSession(connector=connector) as session:
                return await get_campaigns(session, MP_API_KEY)
        
        campaigns = loop.run_until_complete(get_campaigns_wrapper())
        
        ready_campaigns = [c for c in campaigns if c.get('ready')]
        print(f"✅ Готовых кампаний: {len(ready_campaigns)}")
        
        if max_campaigns and len(ready_campaigns) > max_campaigns:
            ready_campaigns = ready_campaigns[:max_campaigns]
            print(f"⚠️ Ограничено до {max_campaigns} кампаний для теста")
        
        update_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        print(f"\n🔄 Запуск асинхронной выгрузки ({MAX_WORKERS} потоков)...")
        
        all_rows = loop.run_until_complete(
            fetch_all_campaigns_async(MP_API_KEY, ready_campaigns, update_time)
        )
        
    finally:
        loop.close()
    
    print(f"\n📊 Итого строк: {len(all_rows)}")
    return all_rows


def main():
    print("=" * 60)
    print(" ВЫГРУЗКА ИЗ MARKETPARSER (МП)")
    print(" Версия: МАКСИМАЛЬНАЯ СКОРОСТЬ")
    print("=" * 60)
    
    rows = fetch_mp_reports(max_campaigns=None)
    
    if not rows:
        print("⚠️ Не загружено ни одного отчёта")
        sys.exit(0)
    
    headers = [
        'Город', 'Кампания', 'ID', 'REPORT_ID',
        'start_date', 'start_time', 'utc', 'Время обновления',
        'Название товара', 'Ваш код', 'Ваша цена',
        'Мин. цена', 'Сред. цена', 'Регион',
        'Конкурент_1', 'offers[0].linkTo', 'offers[0].price',
        'Конкурент_2', 'offers[1].linkTo', 'offers[1].price',
        'Конкурент_3', 'offers[2].linkTo', 'offers[2].price',
        'Конкурент_4', 'offers[3].linkTo', 'offers[3].price',
        'Конкурент_5', 'offers[4].linkTo', 'offers[4].price',
        'Конкурент_6', 'offers[5].linkTo', 'offers[5].price',
        'Конкурент_7', 'offers[6].linkTo', 'offers[6].price',
        'Конкурент_8', 'offers[7].linkTo', 'offers[7].price',
        'Конкурент_9', 'offers[8].linkTo', 'offers[8].price',
        'Конкурент_10', 'offers[9].linkTo', 'offers[9].price',
        'Конкурент_11', 'offers[10].linkTo', 'offers[10].price',
        'Конкурент_12', 'offers[11].linkTo', 'offers[11].price',
    ]
    
    output_file = OUTPUT_DIR / "mp_reports.csv"
    save_to_csv(rows, headers, output_file)
    
    print("\n" + "=" * 60)
    print("✅ ВЫГРУЗКА ЗАВЕРШЕНА!")
    print(f"📁 Файл: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
