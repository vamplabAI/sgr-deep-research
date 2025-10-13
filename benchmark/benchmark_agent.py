import asyncio

from sgr_deep_research.core import AdaptPlanTool, FinalAnswerTool, GeneratePlanTool, ReasoningTool
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.tools import ExtractPageContentTool, WebSearchTool


class BenchmarkAgent(SGRToolCallingResearchAgent):
    """Agent for benchmarking with automatic tool selection."""

    name: str = "benchmark_agent"

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.toolkit = [
            GeneratePlanTool,
            AdaptPlanTool,
            ReasoningTool,
            WebSearchTool,
            ExtractPageContentTool,
            FinalAnswerTool,
        ]

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


async def main(batch_size: int = 3):
    results = []
    for i in range(0, len(questions), batch_size):
        batch_results = await asyncio.gather(*[benchmark_agent(q) for q in questions[i : i + batch_size]])
        results.extend(batch_results)

    for id, result in results:
        print(f"Question: {id}")
        print(f"Result: {result}")
        print("-" * 100)


if __name__ == "__main__":
    asyncio.run(main())
