#!/usr/bin/env python3
"""
CLI скрипт для запуска deep research агента с выводом детальных логов.
Показывает рассуждения агента, выполнение инструментов и результаты в реальном времени.

Использование:
    python run_agent.py <имя_агента> <задача>

Примеры:
    python run_agent.py russian_deep_research_agent "Какие новые модели Tesla выпустили в 2024?"
    python run_agent.py sgr_agent "Research latest AI breakthroughs"
"""

import asyncio
import logging
import sys
from pathlib import Path

from sgr_agent_core import AgentFactory
from sgr_agent_core.agent_config import GlobalConfig


def setup_console_logging():
    """Настройка красивого вывода логов в консоль."""
    # Создаем форматтер с цветами
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Формат логов
    formatter = logging.Formatter(
        '%(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Убираем старые хэндлеры и добавляем наш
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Отключаем verbose логи от библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


async def main():
    """Запуск агента для исследования с детальными логами."""
    # Настраиваем вывод логов в консоль
    setup_console_logging()
    
    # Загружаем конфигурацию
    config = GlobalConfig.from_yaml("config.yaml")
    config.definitions_from_yaml("agents.yaml")
    
    # Получаем имя агента и задачу из аргументов
    if len(sys.argv) < 2:
        print("❌ Использование: python run_agent.py <имя_агента> <задача>")
        print("\nПример: python run_agent.py russian_deep_research_agent \"Исследуй цены на Tesla\"")
        print("\nДоступные агенты:")
        for agent_def in AgentFactory.get_definitions_list():
            print(f"  - {agent_def.name}")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    
    if len(sys.argv) > 2:
        task = " ".join(sys.argv[2:])
    else:
        print("❌ Укажите задачу для исследования")
        sys.exit(1)
    
    print("=" * 100)
    print(f"🔍 DEEP RESEARCH AGENT: {agent_name}")
    print(f"📋 ЗАДАЧА: {task}")
    print("=" * 100)
    print()
    
    # Получаем определение агента
    agent_def = next(
        (ad for ad in AgentFactory.get_definitions_list() if ad.name == agent_name),
        None
    )
    
    if not agent_def:
        available = [ad.name for ad in AgentFactory.get_definitions_list()]
        print(f"❌ Агент '{agent_name}' не найден")
        print(f"\nДоступные агенты: {', '.join(available)}")
        sys.exit(1)
    
    # Создаем и запускаем агента
    try:
        # Создаем агента
        agent = await AgentFactory.create(agent_def, task)
        print(f"✅ Агент создан: {agent.id}\n")
        print("=" * 100)
        print("🚀 НАЧАЛО ИССЛЕДОВАНИЯ")
        print("=" * 100)
        print()
        
        # Запускаем выполнение агента
        # Логи будут выводиться автоматически через logging
        result = await agent.execute()
        
        print()
        print("=" * 100)
        print("✅ ИССЛЕДОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 100)
        
        # Выводим финальный ответ
        if result:
            print()
            print("📊 ФИНАЛЬНЫЙ ОТВЕТ:")
            print("-" * 100)
            print(result)
            print("-" * 100)
        
        # Выводим финальную статистику по токенам и производительности
        if config.execution.track_token_usage and agent.llm_call_count > 0:
            print()
            print("=" * 100)
            print("📈 ФИНАЛЬНАЯ СТАТИСТИКА")
            print("=" * 100)
            print(f"🔢 Общий расход токенов:")
            print(f"   • Prompt токенов: {agent.total_prompt_tokens:,}")
            print(f"   • Completion токенов: {agent.total_completion_tokens:,}")
            print(f"   • Всего токенов: {agent.total_tokens:,}")
            print()
            print(f"🔄 Вызовов LLM: {agent.llm_call_count}")
            print()
            
            # Вычисляем средние метрики по всем вызовам
            avg_prompt = agent.total_prompt_tokens / agent.llm_call_count
            avg_completion = agent.total_completion_tokens / agent.llm_call_count
            avg_total = agent.total_tokens / agent.llm_call_count
            
            print(f"📊 Средние метрики на вызов LLM:")
            print(f"   • Среднее prompt токенов: {avg_prompt:.1f}")
            print(f"   • Среднее completion токенов: {avg_completion:.1f}")
            print(f"   • Среднее всего токенов: {avg_total:.1f}")
            
            # Вычисляем среднюю скорость из логов
            total_duration = 0
            total_tokens_with_speed = 0
            speed_count = 0
            
            for log_entry in agent.log:
                if log_entry.get("step_type") == "llm_call" and "metrics" in log_entry:
                    metrics = log_entry["metrics"]
                    total_duration += metrics.get("duration_ms", 0)
                    if metrics.get("tokens_per_second", 0) > 0:
                        total_tokens_with_speed += metrics.get("completion_tokens", 0)
                        speed_count += 1
            
            if total_duration > 0 and total_tokens_with_speed > 0:
                avg_speed = (total_tokens_with_speed / (total_duration / 1000))
                print()
                print(f"⚡ Средняя скорость генерации: {avg_speed:.1f} токенов/сек")
                print(f"⏱️  Общее время LLM вызовов: {total_duration/1000:.1f} сек")
            
            print("=" * 100)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Исследование прервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Показываем где сохранены логи и отчеты
    logs_dir = Path("logs")
    reports_dir = Path("reports")
    
    print()
    if logs_dir.exists():
        print(f"📁 Детальные логи сохранены в: {logs_dir.absolute()}")
        # Находим последний лог файл
        log_files = sorted(logs_dir.glob(f"*{agent_name}*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if log_files:
            print(f"   Последний файл: {log_files[0].name}")
    
    if reports_dir.exists():
        print(f"📄 Отчеты сохранены в: {reports_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
