#!/usr/bin/env python3
"""
Streamlit интерфейс для General Parser
Структурированное меню: 3 раздела
"""
import streamlit as st
import subprocess
from pathlib import Path
from datetime import datetime
import os

st.set_page_config(
    page_title="General Parser",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Пути
GENERAL_DIR = Path("/Users/samarasamara/GENERAL")
LOGS_DIR = GENERAL_DIR / "logs"

# === ПРОВЕРКА ПАРОЛЯ ===
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    password = st.text_input("🔐 Пароль", type="password", key="pwd_input")
    if password == st.secrets.get("PASSWORD", ""):
        st.session_state.authenticated = True
        st.rerun()
        return True
    elif password:
        st.error("❌ Неверный пароль")
    return False

if not check_password():
    st.warning("Введите пароль для доступа")
    st.stop()

# === ФУНКЦИИ ===
def run_script(script_name: str, timeout: int = 600) -> tuple[bool, str, str]:
    """Запускает скрипт из GENERAL и возвращает результат"""
    try:
        env = os.environ.copy()
        for key, value in st.secrets.items():
            if isinstance(value, str):
                env[key] = value
        result = subprocess.run(
            ["python", str(GENERAL_DIR / script_name)],
            cwd=GENERAL_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"⏱️ Таймаут >{timeout} сек"
    except Exception as e:
        return False, "", f"❌ Ошибка: {str(e)}"

def show_logs(script_name: str, lines: int = 100) -> str:
    """Читает последние строки лога"""
    log_file = LOGS_DIR / f"{script_name.replace('.py', '')}.log"
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            return ''.join(f.readlines()[-lines:])
    return "📭 Логи не найдены"

# === ЗАГОЛОВОК ===
st.title("🤖 General Parser Manager")
st.markdown(f"*Обновлено: {datetime.now().strftime('%d.%m %H:%M')}*")
st.markdown("---")

# === БОКОВАЯ ПАНЕЛЬ ===
with st.sidebar:
    st.header("📋 Разделы")
    page = st.radio(
        "Выберите раздел:",
        ["🔄 General", "📦 Поставщики", "⚙️ Администрирование"],
        index=0,
        label_visibility="collapsed"
    )
    st.markdown("---")
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# === РАЗДЕЛ 1: GENERAL ===
if page == "🔄 General":
    st.header("🔄 General — выгрузки")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Отдельные выгрузки")
        if st.button("🗂️ Выгрузка ПИ", use_container_width=True):
            with st.spinner("Запуск fetch_ip.py..."):
                success, out, err = run_script("fetch_ip.py")
                if success:
                    st.success("✅ ПИ выгружен!")
                else:
                    st.error(f"❌ Ошибка:\n```\n{err or out}\n```")
        if st.button("📊 Выгрузка МС", use_container_width=True):
            with st.spinner("Запуск fetch_ms.py..."):
                success, out, err = run_script("fetch_ms.py")
                if success:
                    st.success("✅ МС выгружен!")
                else:
                    st.error(f"❌ Ошибка:\n```\n{err or out}\n```")
        if st.button("📈 Выгрузка МП", use_container_width=True):
            with st.spinner("Запуск fetch_mp.py..."):
                success, out, err = run_script("fetch_mp.py")
                if success:
                    st.success("✅ МП выгружен!")
                else:
                    st.error(f"❌ Ошибка:\n```\n{err or out}\n```")
    
    with col2:
        st.markdown("### 🚀 Массовые операции")
        if st.button("🔄 ВСЕ: МС+ПИ+МП", use_container_width=True, type="primary"):
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
        if st.button("📊 Обновить дашборд", use_container_width=True, type="primary"):
            with st.spinner("Генерация дашборда..."):
                success, out, err = run_script("generate_dashboard.py")
                if success:
                    st.success("✅ Дашборд обновлён!")
                    sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
                    if sheet_id:
                        st.markdown(f"🔗 [Открыть в Google Sheets](https://docs.google.com/spreadsheets/d/{sheet_id})")
                else:
                    st.error(f"❌ Ошибка:\n```\n{err or out}\n```")

# === РАЗДЕЛ 2: ПОСТАВЩИКИ ===
elif page == "📦 Поставщики":
    st.header("📦 Поставщики — парсеры из ТГ")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔹 Отдельные парсеры")
        parsers = [
            ("fetch_amax.py", "📦 AMAX"),
            ("fetch_bsa.py", "📦 BSA"),
        ]
        for script, label in parsers:
            if st.button(label, use_container_width=True, key=f"btn_{script}"):
                with st.spinner(f"Запуск {label}..."):
                    success, out, err = run_script(script)
                    if success:
                        st.success(f"✅ {label} завершён!")
                    else:
                        st.error(f"❌ Ошибка:\n```\n{err or out}\n```")
    
    with col2:
        st.markdown("### 🔹 Ещё парсеры")
        parsers2 = [
            ("fetch_munstore.py", "📦 MunStore"),
            ("fetch_supportairlines.py", "📦 SupportAirlines"),
        ]
        for script, label in parsers2:
            if st.button(label, use_container_width=True, key=f"btn_{script}"):
                with st.spinner(f"Запуск {label}..."):
                    success, out, err = run_script(script)
                    if success:
                        st.success(f"✅ {label} завершён!")
                    else:
                        st.error(f"❌ Ошибка:\n```\n{err or out}\n```")
    
    st.markdown("---")
    st.markdown("### 🚀 Запуск всех парсеров")
    if st.button("🚀 ВСЕ парсеры", use_container_width=True, type="primary"):
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
            for label, success in results:
                icon = "✅" if success else "❌"
                st.markdown(f"{icon} {label}")

# === РАЗДЕЛ 3: АДМИНИСТРИРОВАНИЕ ===
elif page == "⚙️ Администрирование":
    st.header("⚙️ Администрирование")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Просмотр логов")
        log_files = sorted([f.name for f in LOGS_DIR.glob("*.log")]) if LOGS_DIR.exists() else []
        if log_files:
            selected = st.selectbox("Выберите лог:", log_files)
            if selected and st.button("👁️ Показать", key="show_logs_btn"):
                content = show_logs(selected)
                st.code(content, language="log")
        else:
            st.info("📭 Логи не найдены")
    
    with col2:
        st.markdown("### 📊 Статус системы")
        st.metric("📁 GENERAL", "✅ OK" if GENERAL_DIR.exists() else "❌")
        st.metric("📂 Logs", f"{len(log_files)} файлов" if LOGS_DIR.exists() else "0")
        st.metric("🔐 Auth", "✅" if st.session_state.authenticated else "❌")
        st.markdown("---")
        st.markdown("### 🔗 Быстрые ссылки")
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        if sheet_id:
            st.markdown(f"[📊 Дашборд](https://docs.google.com/spreadsheets/d/{sheet_id})")
        st.markdown("---")
        if st.button("🗑️ Очистить кэш", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ Кэш очищен")

# === ФУТЕР ===
st.markdown("---")
st.caption("General Parser • Управление парсерами и аналитикой")
