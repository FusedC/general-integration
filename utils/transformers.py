from typing import Dict, List, Any, Optional


def extract_attributes(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Извлекает атрибуты товара в плоский словарь
    """
    attrs = {}
    for attr in product.get('attributes', []):
        if attr.get('value') is not None:
            value = attr['value']
            if isinstance(value, dict) and 'name' in value:
                attrs[attr['name']] = value['name']
            else:
                attrs[attr['name']] = value
    return attrs


def extract_prices(sale_prices: List[Dict]) -> Dict[str, float]:
    """
    Извлекает цены по типам (СМР, МСК, ЕКБ)
    """
    prices = {}
    for sp in sale_prices:
        if not sp.get('priceType'):
            continue
        price_type = sp['priceType'].get('name', '')
        value = sp.get('value', 0) / 100
        if 'Самара' in price_type:
            prices['СМР'] = value
        elif 'Москва' in price_type:
            prices['МСК'] = value
        elif 'Екатеринбург' in price_type:
            prices['ЕКБ'] = value
    return prices


def get_min_price(prices: Dict[str, float]) -> Optional[float]:
    """
    Возвращает минимальную положительную цену
    """
    valid_prices = [p for p in prices.values() if p and p > 0]
    return min(valid_prices) if valid_prices else None


def normalize_city_from_name(name: str) -> str:
    """
    Извлекает город из названия кампании
    """
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
