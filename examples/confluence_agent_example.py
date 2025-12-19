"""Пример использования Confluence Research Agent.

Этот пример демонстрирует, как использовать агента для поиска
внутренней документации в Confluence.
"""

import asyncio
import logging

from sgr_agent_core.agent_config import GlobalConfig
from sgr_agent_core.agent_factory import AgentFactory

# Настраиваем логирование, чтобы видеть процесс работы агента
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def search_confluence_documentation():
    """
    Ищем документацию в Confluence, чтобы найти информацию о проектах.
    
    Этот пример показывает базовое использование Confluence агента
    для поиска проектной документации.
    """
    try:
        # Загружаем конфигурацию, чтобы инициализировать агента
        logger.info("📋 Loading configuration...")
        config = GlobalConfig.from_yaml("config.yaml")
        
        # Загружаем определение Confluence агента, чтобы добавить его в систему
        logger.info("🤖 Loading Confluence agent definition...")
        config.definitions_from_yaml("confluence_agent.yaml")
        
        # Создаем агента, чтобы начать поиск
        logger.info("🚀 Creating Confluence agent...")
        agent = await AgentFactory.create_agent(
            agent_name="sgr_tool_calling_agent_rmr_confluence",
            task="Найди информацию о проекте ОТП Банк AI Нулевой замер. "
                 "Мне нужны детали о целях проекта, статусе и ключевых встречах.",
        )
        
        # Запускаем агента и обрабатываем события, чтобы получить результаты
        logger.info("▶️  Running agent...")
        async for event in agent.run():
            # Выводим события агента для отладки
            logger.debug(f"Event: {event}")
        
        # Получаем финальный ответ, чтобы показать результат
        logger.info("✅ Agent completed!")
        logger.info(f"\n{'='*80}\n")
        logger.info("📄 Final Answer:")
        logger.info(agent.streaming_generator.get_final_answer())
        logger.info(f"\n{'='*80}\n")
        
    except FileNotFoundError as e:
        logger.error(f"❌ Configuration file not found: {e}")
        logger.error("Please create config.yaml with Confluence settings")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


async def search_multiple_projects():
    """
    Ищем несколько проектов одновременно, чтобы сравнить их.
    
    Этот пример показывает, как агент автоматически разбивает
    запрос на отдельные поиски для каждого проекта.
    """
    try:
        logger.info("📋 Loading configuration...")
        config = GlobalConfig.from_yaml("config.yaml")
        config.definitions_from_yaml("confluence_agent.yaml")
        
        logger.info("🚀 Creating Confluence agent...")
        agent = await AgentFactory.create_agent(
            agent_name="sgr_tool_calling_agent_rmr_confluence",
            task="Сравни проекты Daisy и Smart Platform. "
                 "Какие у них цели, статус и ключевые отличия?",
        )
        
        logger.info("▶️  Running agent...")
        async for event in agent.run():
            logger.debug(f"Event: {event}")
        
        logger.info("✅ Agent completed!")
        logger.info(f"\n{'='*80}\n")
        logger.info("📄 Final Answer:")
        logger.info(agent.streaming_generator.get_final_answer())
        logger.info(f"\n{'='*80}\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


async def search_in_specific_space():
    """
    Ищем в конкретном пространстве Confluence, чтобы получить более точные результаты.
    
    Этот пример показывает, как агент может использовать
    ConfluenceSpaceFullTextSearchTool для поиска в определенном пространстве.
    """
    try:
        logger.info("📋 Loading configuration...")
        config = GlobalConfig.from_yaml("config.yaml")
        config.definitions_from_yaml("confluence_agent.yaml")
        
        logger.info("🚀 Creating Confluence agent...")
        agent = await AgentFactory.create_agent(
            agent_name="sgr_tool_calling_agent_rmr_confluence",
            task="Найди все документы о релизах в пространстве TECH. "
                 "Интересуют последние релизы и их статус.",
        )
        
        logger.info("▶️  Running agent...")
        async for event in agent.run():
            logger.debug(f"Event: {event}")
        
        logger.info("✅ Agent completed!")
        logger.info(f"\n{'='*80}\n")
        logger.info("📄 Final Answer:")
        logger.info(agent.streaming_generator.get_final_answer())
        logger.info(f"\n{'='*80}\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


async def main():
    """
    Главная функция для запуска примеров, чтобы продемонстрировать возможности агента.
    """
    logger.info("🎯 Confluence Agent Examples")
    logger.info("=" * 80)
    
    # Выбираем пример для запуска
    examples = {
        "1": ("Search single project", search_confluence_documentation),
        "2": ("Compare multiple projects", search_multiple_projects),
        "3": ("Search in specific space", search_in_specific_space),
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    choice = input("\nSelect example (1-3) or 'all' to run all: ").strip()
    
    if choice == "all":
        for name, func in examples.values():
            logger.info(f"\n{'='*80}")
            logger.info(f"Running: {name}")
            logger.info(f"{'='*80}\n")
            await func()
    elif choice in examples:
        name, func = examples[choice]
        logger.info(f"\n{'='*80}")
        logger.info(f"Running: {name}")
        logger.info(f"{'='*80}\n")
        await func()
    else:
        logger.error("Invalid choice!")


if __name__ == "__main__":
    asyncio.run(main())
