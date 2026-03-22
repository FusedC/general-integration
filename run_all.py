#!/usr/bin/env python3
"""
Единый скрипт для запуска всех выгрузок
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_script(script_name: str, description: str) -> bool:
    """Запускает скрипт и возвращает результат"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        [sys.executable, script_name],
        cwd=Path(__file__).parent,
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0


def main():
    """Запускает все три выгрузки последовательно"""
    print("🔗 ЗАПУСК ВСЕХ ВЫГРУЗОК")
    print(f"Папка проекта: {Path(__file__).parent}")
    
    scripts = [
        ("fetch_ms.py", "ВЫГРУЗКА ИЗ МОЙ СКЛАД (МС)"),
        ("fetch_ip.py", "ВЫГРУЗКА ИЗ ПРОЕКТА ИНТЕГРАЦИИ (ПИ)"),
        ("fetch_mp.py", "ВЫГРУЗКА ИЗ MARKETPARSER (МП)"),
    ]
    
    results = []
    for script, desc in scripts:
        success = run_script(script, desc)
        results.append((script, success))
        if not success:
            print(f"\n⚠️ Предупреждение: {script} завершился с ошибкой")
            cont = input("Продолжить со следующим скриптом? (y/n): ").strip().lower()
            if cont != 'y':
                break
    
    # Итоговый отчёт
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'='*60}")
    
    for script, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {script}")
    
    all_success = all(r[1] for r in results)
    if all_success:
        print(f"\n🎉 ВСЕ ВЫГРУЗКИ ЗАВЕРШЕНЫ УСПЕШНО!")
        print(f"📁 Результаты в папке: /Users/samarasamara/GENERAL/output/")
    else:
        print(f"\n⚠️ Некоторые скрипты завершились с ошибками")
        print(f"🔍 Проверьте логи выше для диагностики")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
