from typing import Literal

import pandas as pd
from openai import OpenAI
from prompts import GRADER_TEMPLATE
from pydantic import BaseModel, Field


class GradeAnswerModel(BaseModel):
    """Grade the predicted answer of this new question as one of:
    CORRECT
    INCORRECT
    NOT_ATTEMPTED
    """

    reasoning: str = Field(..., description="Brief rationale for the choice")
    truth_answer: str = Field(..., description="Repeat ground truth answer")
    predicted_answer: str = Field(..., description="Extracted main answer")
    grade_answer: Literal["CORRECT", "INCORRECT", "NOT_ATTEMPTED"] = Field(..., description="Grade of the answer")


def grading_answer(predicted_answer, problem, answer, model_config):
    client = OpenAI(base_url=model_config["base_url"], api_key=model_config["api_key"])

    completion = client.beta.chat.completions.parse(
        model=model_config["model"],
        messages=[
            {
                "role": "user",
                "content": GRADER_TEMPLATE(problem, answer, predicted_answer),
            },
        ],
        response_format=GradeAnswerModel,
    )
    return completion.choices[0].message.parsed


def save_result(results, output_path):
    results_df = pd.DataFrame(results)
    results_df.to_excel(output_path, index=False)


def get_accuracy_given_attempted(df) -> float:
    attempted_count = df["is_correct"].sum() + df["is_incorrect"].sum()
    if attempted_count == 0:
        return 0.0
    return df["is_correct"].sum() / attempted_count


def get_f1_score(df) -> float:
    if df.empty or not ("is_correct" in df.columns and "is_incorrect" in df.columns):
        return 0.0

    num_total_samples = len(df)
    if num_total_samples == 0:
        return 0.0

    mean_correct = df["is_correct"].sum() / num_total_samples  # Precision-like term over all samples

    accuracy_given_attempted_val = get_accuracy_given_attempted(df)  # Recall-like term on attempted samples

    numerator = 2 * accuracy_given_attempted_val * mean_correct
    denominator = accuracy_given_attempted_val + mean_correct
    if denominator == 0:
        return 0.0
    return numerator / denominator
