import time
import requests
from typing import Optional, Dict, Any
from config import MAX_RETRIES, RETRY_DELAY, REQUEST_TIMEOUT


class APIClient:
    """Универсальный клиент для API запросов с повторами"""
    
    def __init__(self, base_url: str, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def get(self, endpoint: str, params: Optional[Dict] = None, 
            headers: Optional[Dict] = None, max_retries: int = MAX_RETRIES) -> Optional[Dict[str, Any]]:
        """
        GET запрос с автоматическими повторами при ошибках
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 429:  # Rate limit
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ Rate limit. Ждём {wait_time}с...")
                    time.sleep(wait_time)
                    continue
                
                elif 400 <= response.status_code < 500:
                    print(f"❌ Клиентская ошибка {response.status_code}: {response.text[:200]}")
                    return None
                
                else:  # 5xx
                    if attempt < max_retries:
                        wait_time = RETRY_DELAY * attempt
                        print(f"⚠️ Ошибка сервера {response.status_code}. Повтор через {wait_time}с...")
                        time.sleep(wait_time)
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"⏱️ Таймаут на попытке {attempt}/{max_retries}")
                if attempt < max_retries:
                    time.sleep(RETRY_DELAY * attempt)
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка запроса: {e}")
                if attempt < max_retries:
                    time.sleep(RETRY_DELAY * attempt)
        
        print(f"❌ Не удалось выполнить запрос после {max_retries} попыток")
        return None
