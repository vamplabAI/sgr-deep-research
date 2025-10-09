# Скрипт для запуска оценки системы на SimpleQA Verified
# URL: https://www.kaggle.com/datasets/deepmind/simpleqa-verified/data


from utils import grading_answer, call_sgr_agent, get_f1_score

from openai import OpenAI
import pandas as pd
import argparse
import logging


import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def simpleqa_run_task(row, judge_model_config, sgr_reports_path, sgr_agent_name):

    curr_reports = os.listdir(sgr_reports_path)

    problem = row["problem"]
    answer = row["answer"]

    logger.info("Starting deep research...")
    agent = OpenAI(base_url="http://localhost:8010/v1", api_key="dummy")
    response_success, err = call_sgr_agent(agent, problem, sgr_agent_name)

    if not response_success:
        logger.error(f"Deep research failed: {err}")
        return {
            "problem": problem,
            "answer": answer,
            "predicted_answer": "None",
            "grade_str": "None",
            "is_correct": False,
            "is_incorrect": False,
            "is_not_attempted": False,
            "fail_search": True,
            "grade_answer_report": "None",
        }

    logger.info("Deep research completed successfully")

    after_reports = os.listdir(sgr_reports_path)

    # Получение нового отчета происходит после выполнения поиска (ищем новый появившийся отчет)
    new_report = list(set(after_reports) - set(curr_reports))

    if len(new_report) == 0:
        logger.error("Failed to create report")
        return {
            "problem": problem,
            "answer": answer,
            "predicted_answer": "None",
            "grade_str": "None",
            "is_correct": False,
            "is_incorrect": False,
            "is_not_attempted": False,
            "fail_search": True,
            "grade_answer_report": "None",
        }

    curr_report_path = os.path.join(sgr_reports_path, new_report[0])
    logger.info(f"Report created: {curr_report_path}")

    # Оценка происходит методом LLM-as-a-judge
    logger.info("Starting answer grading...")
    grade_answer_report, report_content = grading_answer(
        curr_report_path, problem, answer, judge_model_config
    )
    grade_answer = grade_answer_report.grade_answer

    logger.info(f"Answer grading completed: {grade_answer}")

    is_correct_val = grade_answer == "CORRECT"
    is_incorrect_val = grade_answer == "INCORRECT"
    is_not_attempted_val = grade_answer == "NOT_ATTEMPTED"

    return {
        "problem": problem,
        "answer": answer,
        "predicted_answer": report_content,
        "grade_str": grade_answer,
        "is_correct": is_correct_val,
        "is_incorrect": is_incorrect_val,
        "is_not_attempted": is_not_attempted_val,
        "fail_search": False,
        "grade_answer_report": grade_answer_report,
    }


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run SimpleQA Benchmark")
    parser.add_argument(
        "--path_to_simpleqa",
        type=str,
        required=True,
        help="Path to simpleqa_verified.csv",
    )
    parser.add_argument(
        "--path_to_sgr_reports",
        type=str,
        required=True,
        help="Path to SGR reports directory",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=False,
        help="Path to output Excel file",
        default="simpleqa_bench_results.xlsx",
    )

    parser.add_argument(
        "--judge_model_name", type=str, required=True, help="Judge model name"
    )
    parser.add_argument(
        "--judge_model_base_url", type=str, required=True, help="Judge model base URL"
    )
    parser.add_argument(
        "--judge_model_api_key", type=str, required=True, help="Judge model API key"
    )

    parser.add_argument(
        "--sgr_agent_name", type=str, required=True, help="SGR agent name"
    )

    parser.add_argument(
        "--n_samples",
        type=int,
        required=True,
        help="Number of samples to process from simpleqa",
    )

    args = parser.parse_args()

    judge_model_config = {
        "base_url": args.judge_model_base_url,
        "api_key": args.judge_model_api_key,
        "model": args.judge_model_name,
    }

    sgr_reports_path = args.path_to_sgr_reports
    simpleqa_path = args.path_to_simpleqa
    output_path = args.output_path

    sgr_agent_name = args.sgr_agent_name

    df = pd.read_csv(simpleqa_path)

    n_samples = args.n_samples

    df_sample = df.head(n_samples)

    results_list = []

    if os.path.exists(output_path):
        results_df = pd.read_excel(output_path)
        results_list = results_df.to_dict(orient="records")
        processed_indices = set(range(len(results_df)))
    else:
        results_df = pd.DataFrame()
        results_list = []
        processed_indices = set()

    # Выполнение поиска для каждого вопроса и сохранение результатов на каждом шаге
    for idx, row in df_sample.iterrows():
        if len(processed_indices) > 0 and idx <= max(processed_indices):
            continue
        logger.info("=============================================")
        logger.info(f"Processing problem: idx:{idx}, problem:{row['problem']}")

        result_run_task = simpleqa_run_task(
            row, judge_model_config, sgr_reports_path, sgr_agent_name
        )

        results_list.append(result_run_task)

        results_df = pd.DataFrame(results_list)
        results_df.to_excel(output_path, index=False)

    num_correct = results_df["is_correct"].sum()
    num_incorrect = results_df["is_incorrect"].sum()
    metric_f1 = get_f1_score(results_df)
    metrics_path = output_path.replace(".xlsx", "_metrics.txt")

    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write(f"F1 score: {metric_f1}\n")
        f.write(f"Количество правильных: {num_correct}\n")
        f.write(f"Количество неправильных: {num_incorrect}\n")
