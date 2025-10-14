import argparse
import asyncio
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from openai import pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from benchmark.utils import (
    GradeAnswerModel,
    get_f1_score,
    grading_answer,
    save_result,
)
from sgr_deep_research.core import (
    FinalAnswerTool,
    ReasoningTool,
)
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.tools import ExtractPageContentTool, WebSearchTool
from sgr_deep_research.settings import get_config

# Set config path to project root BEFORE importing sgr_deep_research modules
# This ensures get_config() will load config.yaml from the correct location
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, "config.yaml")
os.environ.setdefault("APP_CONFIG", config_path)


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Log which config file is being used
logger.info(f"Using config file: {config_path}")


class TaskFilter(logging.Filter):
    """Filter logs by asyncio task ID."""

    def __init__(self, task_id):
        super().__init__()
        self.task_id = task_id

    def filter(self, record):
        current_task = asyncio.current_task()
        if current_task is None:
            return False
        return id(current_task) == self.task_id


@contextmanager
def question_log_context(question_idx: int, question_text: str = "", enabled: bool = True):
    """Context manager for logging each question to a separate file.

    Args:
        question_idx: Index of the question being processed
        question_text: Text of the question (first 20 chars will be used in filename)
        enabled: Whether to enable per-question logging
    """
    if not enabled:
        yield
        return

    config = get_config()
    logs_dir = Path(config.benchmark.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename from question text (first 20 chars)
    safe_question = question_text[:20] if question_text else "question"
    # Replace invalid filename characters with underscore
    safe_question = "".join(c if c.isalnum() or c in (" ", "-") else "_" for c in safe_question)
    safe_question = safe_question.replace(" ", "_").strip("_")

    log_file = logs_dir / f"{question_idx:04d}_{safe_question}.log"

    # Get current task ID to filter logs
    current_task = asyncio.current_task()
    task_id = id(current_task) if current_task else None

    # Create file handler for this question
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add filter to only log from this task
    task_filter = TaskFilter(task_id)
    file_handler.addFilter(task_filter)

    # Add handler to root logger to capture all logs
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    try:
        yield
    finally:
        # Remove and close the handler
        root_logger.removeHandler(file_handler)
        file_handler.close()


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
            # GeneratePlanTool,
            # AdaptPlanTool,
            ReasoningTool,
            WebSearchTool,
            ExtractPageContentTool,
            FinalAnswerTool,
        ]

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                ReasoningTool,
                FinalAnswerTool,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool,
            }

        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def execute(
        self,
    ):
        await super().execute()


async def benchmark_agent(question, answer, model_config, question_idx: int = 0) -> Dict[str, Any]:
    system_conf = get_config()

    with question_log_context(question_idx, question, system_conf.benchmark.save_logs_per_question):
        try:
            agent = BenchmarkAgent(task=question, max_iterations=system_conf.execution.max_steps)
            await agent.execute()

            predicted_answer = agent._context.execution_result

            grade_answer_report: GradeAnswerModel = grading_answer(predicted_answer, question, answer, model_config)
            grade_answer = grade_answer_report.grade_answer

            is_correct_val = grade_answer == "CORRECT"
            is_incorrect_val = grade_answer == "INCORRECT"
            is_not_attempted_val = grade_answer == "NOT_ATTEMPTED"

        except Exception as ex:
            return {
                "problem": question,
                "answer": answer,
                "predicted_answer": "None",
                "grade_str": "None",
                "is_correct": False,
                "is_incorrect": False,
                "is_not_attempted": False,
                "fail_search": True,
                "grade_answer_report": "None",
                "Error text": str(ex),
                "agent_id": getattr(agent, "id", "N/A"),
            }

        return {
            "question": question,
            "answer": answer,
            "predicted_answer": predicted_answer,
            "grade_str": grade_answer,
            "is_correct": is_correct_val,
            "is_incorrect": is_incorrect_val,
            "is_not_attempted": is_not_attempted_val,
            "fail_search": False,
            "grade_answer_report": grade_answer_report,
            "Error text": "None",
            "agent_id": agent.id,
        }


async def main(
    problems: List[str],
    answers: List[str],
    output_path: str,
    judge_model_config: Dict[str, str],
    results_task: List[Dict[str, Any]] = None,
    batch_size: int = 3,
    start_idx: int = 0,
):
    results = results_task if results_task else []

    if len(problems) != len(answers):
        raise "Problems list and Answer list don't compare"

    total_batches = (len(problems) + batch_size - 1) // batch_size

    for batch_idx, i in enumerate(range(0, len(problems), batch_size), start=1):
        batch_tasks = problems[i : i + batch_size], answers[i : i + batch_size]

        # Calculate global question indices for this batch
        question_indices = list(range(start_idx + i, start_idx + i + len(batch_tasks[0])))

        logger.info(f"Начался батч {batch_idx}/{total_batches} (вопросы {i+1}-{min(i+batch_size, len(problems))})")
        logger.debug(f"Batch tasks: {batch_tasks}")

        batch_results = await asyncio.gather(
            *[
                benchmark_agent(question, answer, judge_model_config, question_idx)
                for question, answer, question_idx in zip(*batch_tasks, question_indices)
            ]
        )

        results.extend(batch_results)

        save_result(results, output_path)

        logger.info(
            f"Завершен батч {batch_idx}/{total_batches}."
            f"Обработано вопросов: {len(results)}/{len(problems) + len(results_task if results_task else [])}"
        )

    logger.info("Benchmark completed!")

    results_df = pd.DataFrame(results)
    num_correct = results_df["is_correct"].sum()
    num_incorrect = results_df["is_incorrect"].sum()
    num_not_attempted = results_df["is_not_attempted"].sum()
    num_failed_search = results_df["fail_search"].sum()

    metric_f1 = get_f1_score(results_df)
    accuracy = num_correct / len(results_df)
    metrics_path = output_path.replace(".xlsx", "_metrics.txt")

    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write(f"F1 score: {metric_f1}\n")
        f.write(f"Accuracy: {accuracy}\n")
        f.write(f"Количество правильных: {num_correct}\n")
        f.write(f"Количество неправильных: {num_incorrect}\n")
        f.write(f"Количество неполных: {num_not_attempted}\n")
        f.write(f"Количество failed_search: {num_failed_search}\n")

    logger.info("Calculating F1...")
    logger.info(f"F1 score: {metric_f1}")
    logger.info(f"Accuracy: {accuracy}")
    logger.info(f"Количество правильных: {num_correct}")
    logger.info(f"Количество неправильных: {num_incorrect}")
    logger.info(f"Количество неполных: {num_not_attempted}")
    logger.info(f"Количество failed_search: {num_failed_search}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SimpleQA Benchmark")

    parser.add_argument(
        "--path_to_simpleqa",
        type=str,
        required=True,
        help="Path to simpleqa_verified on csv",
    )

    parser.add_argument(
        "--output_path",
        type=str,
        required=False,
        default="simpleqa_bench_results.xlsx",
        help="Path to output Excel file",
    )

    parser.add_argument(
        "--n_samples",
        type=int,
        required=False,
        default=None,
        help="Number of samples to process from simpleqa",
    )

    parser.add_argument(
        "--batch_size",
        type=int,
        required=False,
        default=10,
        help="Number of samples to process from simpleqa",
    )

    args = parser.parse_args()

    judge_model_config = {
        "base_url": os.getenv("JUDGE_BASE_URL"),
        "api_key": os.getenv("JUDGE_API_KEY"),
        "model": os.getenv("JUDGE_MODEL_NAME"),
    }

    simpleqa_path = args.path_to_simpleqa
    output_path = args.output_path

    batch_size = args.batch_size

    n_samples = args.n_samples

    df = pd.read_csv(simpleqa_path)

    # По необходимости выбираем не все вопросы
    if n_samples:
        df = df.head(n_samples)

    problems = df["problem"].to_list()
    answers = df["answer"].to_list()

    results_tasks = []
    start_idx = 0

    if os.path.exists(output_path):
        results_df = pd.read_excel(output_path)
        number_ready_task = len(results_df)
        start_idx = number_ready_task
        problems = problems[number_ready_task:]
        answers = answers[number_ready_task:]
        results_tasks = results_df.to_dict(orient="records")

    asyncio.run(
        main(
            problems=problems,
            answers=answers,
            output_path=output_path,
            judge_model_config=judge_model_config,
            results_task=results_tasks,
            batch_size=batch_size,
            start_idx=start_idx,
        )
    )
