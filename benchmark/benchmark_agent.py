import asyncio

from sgr_deep_research.core.agents.sgr_auto_tools_agent import SGRAutoToolCallingResearchAgent
from sgr_deep_research.core.tools import ExtractPageContentTool, WebSearchTool, system_agent_tools


class BenchmarkAgent(SGRAutoToolCallingResearchAgent):
    """Agent for benchmarking with automatic tool selection."""

    name: str = "benchmark_agent"

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.toolkit = [*system_agent_tools, WebSearchTool, ExtractPageContentTool]

    async def execute(
        self,
    ):
        await super().execute()


questions = [
    "What is the capital of France?",
    "What is the capital of Germany?",
    "What is the capital of Italy?",
    "What is the capital of Spain?",
    "What is the capital of Portugal?",
    "What is the capital of Greece?",
    "What is the capital of Turkey?",
]


async def benchmark_agent(question) -> tuple[str, str]:
    agent = BenchmarkAgent(task=question)
    await agent.execute()
    return agent.id, agent._context.execution_result


async def main():
    results = await asyncio.gather(*[benchmark_agent(question) for question in questions])
    for id, result in results:
        print(f"Question: {id}")
        print(f"Result: {result}")
        print("-" * 100)


if __name__ == "__main__":
    asyncio.run(main())
