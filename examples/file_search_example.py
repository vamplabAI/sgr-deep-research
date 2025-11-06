"""Example: Using SGRFileAgent for file search and analysis."""

import asyncio

from sgr_deep_research.core.agents.sgr_file_agent import SGRFileAgent


async def example_find_python_files():
    """Find all Python files in the project."""
    
    agent = SGRFileAgent(
        task="Найди все Python файлы в текущей директории и покажи их структуру",
        max_iterations=10,
        working_directory="."
    )
    
    print("=" * 60)
    print("Example 1: Find all Python files")
    print("=" * 60)
    
    async for event in agent.run():
        if event["type"] == "reasoning":
            print(f"\n🤔 Reasoning: {event['data']['reasoning']}")
        
        elif event["type"] == "tool_execution":
            print(f"🔧 Executing: {event['data']['tool_name']}")
        
        elif event["type"] == "final_answer":
            print(f"\n✅ Final Answer:\n{event['data']['answer']}")


async def example_find_large_files():
    """Find large files (>1MB)."""
    
    agent = SGRFileAgent(
        task="Найди все файлы размером больше 1 мегабайта",
        max_iterations=10,
        working_directory="."
    )
    
    print("\n" + "=" * 60)
    print("Example 2: Find large files (>1MB)")
    print("=" * 60)
    
    async for event in agent.run():
        if event["type"] == "final_answer":
            print(f"\n✅ Final Answer:\n{event['data']['answer']}")


async def example_find_recent_files():
    """Find recently modified files."""
    
    agent = SGRFileAgent(
        task="Покажи все файлы, измененные за последние 7 дней",
        max_iterations=10,
        working_directory="."
    )
    
    print("\n" + "=" * 60)
    print("Example 3: Find recently modified files")
    print("=" * 60)
    
    async for event in agent.run():
        if event["type"] == "final_answer":
            print(f"\n✅ Final Answer:\n{event['data']['answer']}")


async def example_search_in_files():
    """Search for specific text in files."""
    
    agent = SGRFileAgent(
        task="Найди все упоминания 'BaseTool' в Python файлах",
        max_iterations=10,
        working_directory="./sgr_deep_research"
    )
    
    print("\n" + "=" * 60)
    print("Example 4: Search text in files")
    print("=" * 60)
    
    async for event in agent.run():
        if event["type"] == "final_answer":
            print(f"\n✅ Final Answer:\n{event['data']['answer']}")


async def main():
    """Run all examples."""
    
    await example_find_python_files()
    await example_find_large_files()
    await example_find_recent_files()
    await example_search_in_files()


if __name__ == "__main__":
    asyncio.run(main())

