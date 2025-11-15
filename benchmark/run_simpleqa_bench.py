import argparse
import asyncio
import logging
import os
from typing import Any, Dict, List

import pandas as pd
from benchmark_agent import BenchmarkAgent
from dotenv import load_dotenv

from benchmark.utils import (
    GradeAnswerModel,
    get_f1_score,
    grading_answer,
    save_result,
)
from sgr_deep_research.core.agent_config import GlobalConfig

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, "config.yaml")
os.environ.setdefault("APP_CONFIG", config_path)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logger.info(f"Using config file: {config_path}")


async def benchmark_agent(question, answer, model_config) -> Dict[str, Any]:
    system_conf = GlobalConfig()
    agent = BenchmarkAgent(task=question, max_iterations=system_conf.execution.max_iterations)

    try:
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

        logger.info(
            f"Started batch {batch_idx}/{total_batches} (questions {i + 1}-{min(i + batch_size, len(problems))})"
        )
        logger.debug(f"Batch tasks: {batch_tasks}")

        batch_results = await asyncio.gather(
            *[benchmark_agent(question, answer, judge_model_config) for question, answer in zip(*batch_tasks)]
        )

        results.extend(batch_results)

        save_result(results, output_path)

        logger.info(
            f"Completed batch {batch_idx}/{total_batches}."
            f"Processed questions: {len(results)}/{len(problems) + len(results_task if results_task else [])}"
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
        f.write(f"Number of correct: {num_correct}\n")
        f.write(f"Number of incorrect: {num_incorrect}\n")
        f.write(f"Number of incomplete: {num_not_attempted}\n")
        f.write(f"Number of failed_search: {num_failed_search}\n")

    logger.info("Calculating F1...")
    logger.info(f"F1 score: {metric_f1}")
    logger.info(f"Accuracy: {accuracy}")
    logger.info(f"Number of correct: {num_correct}")
    logger.info(f"Number of incorrect: {num_incorrect}")
    logger.info(f"Number of incomplete: {num_not_attempted}")
    logger.info(f"Number of failed_search: {num_failed_search}")


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

    # Select only a subset of questions if needed
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
