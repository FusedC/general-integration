import csv
from pathlib import Path
from typing import List, Dict, Any


def save_to_csv(data: List[List[Any]], headers: List[str], filepath: Path):
    """
    Сохраняет данные в CSV файл
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    
    print(f"✅ Сохранено {len(data)} строк в {filepath}")


def load_csv(filepath: Path) -> List[Dict[str, str]]:
    """
    Загружает данные из CSV файла
    """
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)
