#!/usr/bin/env python3
"""
General Parser Manager — Professional UI
"""
import streamlit as st
import subprocess
from pathlib import Path
from datetime import datetime
import os

# === КОНФИГУРАЦИЯ СТРАНИЦЫ ===
st.set_page_config(
    page_title="General Parser",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === КАСТОМНЫЕ СТИЛИ ===
st.markdown("""
<style>
    /* Скрываем футер Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Карточки */
    .card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #3d3d5c;
    }
    
    /* Кнопки */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    /* Заголовки */
    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Статусы */
    .status-ok { color: #00ff88; }
    .status-error { color: #ff4757; }
    .status-warning { color: #ffa502; }
</style>
""", unsafe_allow_html=True)

# === ПУТИ ===
GENERAL_DIR = Path("/Users/samarasamara/GENERAL")
LOGS_DIR = GENERAL_DIR / "logs"

# === ПРОВЕРКА ПАРОЛЯ ===
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🔐 Авторизация")
        password = st.text_input("", type="password", placeholder="Введите пароль", key="pwd_input")
        if st.button("Войти", use_container_width=True, type="primary"):
            if password == st.secrets.get("PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Неверный пароль")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

# === ФУНКЦИИ ===
def run_script(script_name: str, timeout: int = 600):
    """Запускает скрипт и возвращает результат"""
    try:
        env = os.environ.copy()
        for key, value in st.secrets.items():
            if isinstance(value, str):
                env[key] = value
        
        process = subprocess.run(
            ["python", str(GENERAL_DIR / script_name)],
            cwd=GENERAL_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        return process.returncode == 0, process.stdout, process.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"⏱️ Таймаут >{timeout} сек"
    except Exception as e:
        return False, "", f"❌ Ошибка: {str(e)}"

def get_logs(script_name: str, lines: int = 50):
    """Читает последние строки лога"""
    log_file = LOGS_DIR / f"{script_name.replace('.py', '')}.log"
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            return ''.join(f.readlines()[-lines:])
    return "📭 Логи не найдены"

def check_system_status():
    """Проверяет статус системы"""
    status = {
        "general_dir": GENERAL_DIR.exists(),
        "logs_dir": LOGS_DIR.exists(),
        "logs_count": len(list(LOGS_DIR.glob("*.log"))) if LOGS_DIR.exists() else 0,
        "auth": st.session_state.authenticated
    }
    return status

# === БОКОВАЯ ПАНЕЛЬ ===
with st.sidebar:
    st.markdown("### 📊 General Parser")
    st.markdown("---")
    
    page = st.radio(
        "Навигация",
        ["🔄 General", "📦 Поставщики", "⚙️ Администрирование"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown(f"*Обновлено: {datetime.now().strftime('%d.%m %H:%M')}*")
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# === ГЛАВНАЯ СТРАНИЦА ===
if page == "🔄 General":
    st.title("🔄 General — выгрузки")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📥 Отдельные выгрузки")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        if st.button("🗂️ Выгрузка ПИ", use_container_width=True, key="btn_pi"):
            with st.spinner("Запуск..."):
                success, out, err = run_script("fetch_ip.py")
                if success:
                    st.success("✅ ПИ выгружен!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        if st.button("📊 Выгрузка МС", use_container_width=True, key="btn_ms"):
            with st.spinner("Запуск..."):
                success, out, err = run_script("fetch_ms.py")
                if success:
                    st.success("✅ МС выгружен!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        if st.button("📈 Выгрузка МП", use_container_width=True, key="btn_mp"):
            with st.spinner("Запуск..."):
                success, out, err = run_script("fetch_mp.py")
                if success:
                    st.success("✅ МП выгружен!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🚀 Массовые операции")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        if st.button("🔄 ВСЕ: МС+ПИ+МП", use_container_width=True, type="primary", key="btn_all"):
            with st.spinner("Запуск всех выгрузок..."):
                progress = st.progress(0)
                scripts = [("fetch_ip.py", "🗂️ ПИ"), ("fetch_ms.py", "📊 МС"), ("fetch_mp.py", "📈 МП")]
                for i, (script, label) in enumerate(scripts):
                    st.info(f"{label}: выполняется...")
                    success, out, err = run_script(script)
                    if success:
                        st.success(f"✅ {label} завершён")
                    else:
                        st.error(f"❌ {label}: {err or out}")
                    progress.progress((i + 1) / len(scripts))
            st.success("🎉 Все выгрузки завершены!")
        
        st.markdown("---")
        
        if st.button("📊 Обновить дашборд", use_container_width=True, type="primary", key="btn_dashboard"):
            with st.spinner("Генерация дашборда..."):
                success, out, err = run_script("generate_dashboard.py")
                if success:
                    st.success("✅ Дашборд обновлён!")
                    sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
                    if sheet_id:
                        st.markdown(f"🔗 [Открыть в Google Sheets](https://docs.google.com/spreadsheets/d/{sheet_id})")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        st.markdown("</div>", unsafe_allow_html=True)

# === ПОСТАВЩИКИ ===
elif page == "📦 Поставщики":
    st.title("📦 Поставщики — парсеры из ТГ")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 🔹 Отдельные парсеры")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        if st.button("📦 AMAX", use_container_width=True, key="btn_amax"):
            with st.spinner("Запуск AMAX..."):
                success, out, err = run_script("fetch_amax.py")
                if success:
                    st.success("✅ AMAX завершён!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        if st.button("📦 BSA", use_container_width=True, key="btn_bsa"):
            with st.spinner("Запуск BSA..."):
                success, out, err = run_script("fetch_bsa.py")
                if success:
                    st.success("✅ BSA завершён!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🔹 Ещё парсеры")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        if st.button("📦 MunStore", use_container_width=True, key="btn_mun"):
            with st.spinner("Запуск MunStore..."):
                success, out, err = run_script("fetch_munstore.py")
                if success:
                    st.success("✅ MunStore завершён!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        if st.button("📦 SupportAirlines", use_container_width=True, key="btn_support"):
            with st.spinner("Запуск SupportAirlines..."):
                success, out, err = run_script("fetch_supportairlines.py")
                if success:
                    st.success("✅ SupportAirlines завершён!")
                else:
                    st.error(f"❌ Ошибка: {err or out}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 🚀 Запуск всех парсеров")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    if st.button("🚀 ВСЕ парсеры", use_container_width=True, type="primary", key="btn_all_parsers"):
        with st.spinner("Запуск всех парсеров..."):
            progress = st.progress(0)
            scripts = ["fetch_amax.py", "fetch_bsa.py", "fetch_munstore.py", "fetch_supportairlines.py"]
            results = []
            for i, script in enumerate(scripts):
                label = script.replace("fetch_", "").replace(".py", "")
                st.info(f"📦 {label}: выполняется...")
                success, out, err = run_script(script)
                results.append((label, success))
                progress.progress((i + 1) / len(scripts))
            
            ok = sum(1 for _, s in results if s)
            st.success(f"🎉 Завершено: {ok}/{len(results)}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# === АДМИНИСТРИРОВАНИЕ ===
elif page == "⚙️ Администрирование":
    st.title("⚙️ Администрирование")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📋 Просмотр логов")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        log_files = sorted([f.name for f in LOGS_DIR.glob("*.log")]) if LOGS_DIR.exists() else []
        
        if log_files:
            selected = st.selectbox("Выберите лог:", log_files)
            if st.button("👁️ Показать", key="show_logs_btn"):
                content = get_logs(selected)
                st.code(content, language="log")
        else:
            st.info("📭 Логи не найдены")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 📊 Статус системы")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        status = check_system_status()
        
        # GENERAL DIR
        if status["general_dir"]:
            st.markdown("📁 GENERAL: <span class='status-ok'>✅ OK</span>", unsafe_allow_html=True)
        else:
            st.markdown("📁 GENERAL: <span class='status-error'>❌ Не найден</span>", unsafe_allow_html=True)
        
        # LOGS
        st.markdown(f"📂 Logs: **{status['logs_count']}** файлов")
        
        # AUTH
        if status["auth"]:
            st.markdown("🔐 Auth: <span class='status-ok'>✅ OK</span>", unsafe_allow_html=True)
        else:
            st.markdown("🔐 Auth: <span class='status-error'>❌ Ошибка</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🔗 Быстрые ссылки")
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        if sheet_id:
            st.markdown(f"[📊 Дашборд](https://docs.google.com/spreadsheets/d/{sheet_id})")
        
        if st.button("🗑️ Очистить кэш", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ Кэш очищен")
        
        st.markdown("</div>", unsafe_allow_html=True)

# === ФУТЕР ===
st.markdown("---")
st.markdown("<center><small>General Parser • Управление парсерами и аналитикой</small></center>", unsafe_allow_html=True)
