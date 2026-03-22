import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# МойСклад
MS_TOKEN = os.getenv("MS_TOKEN")
MS_BASE_URL = "https://api.moysklad.ru/api/remap/1.2"

# MarketParser
MP_API_KEY = os.getenv("MP_API_KEY")
MP_BASE_URL = "https://cp2.marketparser.ru/api/v2"

# Integration Project
IP_API_URL = os.getenv("IP_API_URL", "http://msmp.pricing.su/api/ur_summary")
IP_API_USER = os.getenv("IP_API_USER", "admin")
IP_API_PASS = os.getenv("IP_API_PASS", "")

# Общие настройки
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
