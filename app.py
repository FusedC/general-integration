#!/usr/bin/env python3
"""
Простой интерфейс для запуска выгрузок
Запуск: streamlit run app.py
"""
import streamlit as st
import subprocess
import sys
from pathlib import Path

# Настройки страницы
st.set_page_config(
    page_title="Выгрузка данных",
    page_icon="📊",
    layout="wide"
)

# Заголовок
st.title("📊 Панель выгрузки данных")
st.markdown("---")

# Пути
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# Функция запуска скрипта
def run_script(script_path: str, label: str) -> str:
    """Запускает скрипт и возвращает логи"""
    logs = []
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            logs.append(line)
            st.code(line.strip(), language="bash")
        
        process.wait()
        
        if process.returncode == 0:
            return f"✅ {label} завершён успешно"
        else:
            return f"❌ {label} завершился с ошибкой (код {process.returncode})"
            
    except Exception as e:
        return f"❌ Ошибка запуска {label}: {str(e)}"


# Кнопки управления
st.subheader("🚀 Запуск выгрузок")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📦 МойСклад", type="primary", use_container_width=True):
        with st.spinner("Выгружаю данные из МойСклад..."):
            result = run_script("fetch_ms.py", "МойСклад")
            st.success(result)

with col2:
    if st.button("🔗 Проект Интеграции", type="primary", use_container_width=True):
        with st.spinner("Выгружаю данные из ПИ..."):
            result = run_script("fetch_ip.py", "Проект Интеграции")
            st.success(result)

with col3:
    if st.button("📈 MarketParser", type="primary", use_container_width=True):
        with st.spinner("Выгружаю данные из MP..."):
            result = run_script("fetch_mp.py", "MarketParser")
            st.success(result)

with col4:
    if st.button("🔄 ВСЕ ВМЕСТЕ", type="secondary", use_container_width=True):
        with st.spinner("Запускаю все выгрузки последовательно..."):
            scripts = [
                ("fetch_ms.py", "МойСклад"),
                ("fetch_ip.py", "Проект Интеграции"),
                ("fetch_mp.py", "MarketParser")
            ]
            for script, label in scripts:
                st.markdown(f"### 📋 {label}")
                result = run_script(script, label)
                st.markdown(f"**{result}**")
                st.markdown("---")

# Статус файлов
st.markdown("---")
st.subheader("📁 Результаты выгрузки")

if OUTPUT_DIR.exists():
    files = list(OUTPUT_DIR.glob("*.csv"))
    if files:
        for f in sorted(files):
            size_kb = f.stat().st_size / 1024
            st.markdown(f"✅ `{f.name}` — {size_kb:.1f} KB")
    else:
        st.info("Папка output пуста. Запустите выгрузку.")
else:
    st.warning("Папка output не найдена")

# Справка
with st.expander("ℹ️ Справка"):
    st.markdown("""
    ### Как пользоваться:
    1. Убедитесь, что в файле `.env` указаны API-ключи
    2. Нажмите кнопку нужного источника данных
    3. Следите за прогрессом в логах ниже
    4. Результаты сохранятся в папке `output/`
    
    ### Запуск локально:
    ```bash
    cd /Users/samarasamara/GENERAL
    source venv/bin/activate
    streamlit run app.py
    ```
    
    ### На сервере:
    - Установите те же зависимости
    - Настройте cron для периодического запуска
    - Или используйте `streamlit run --server.port 8501 app.py`
    """)
