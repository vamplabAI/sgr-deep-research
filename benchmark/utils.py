from pydantic import BaseModel, Field
from typing import Literal
from openai import OpenAI
from prompts import GRADER_TEMPLATE


class GradeAnswerModel(BaseModel):
    """Grade the predicted answer of this new question as one of:
        CORRECT
        INCORRECT
        NOT_ATTEMPTED
    """
    reasoning: str = Field(..., description="Brief rationale for the choice")
    truth_answer: str = Field(..., description="Repeat ground truth answer")
    answer_from_report: str = Field(..., description="Extract main answer from report")
    grade_answer: Literal["CORRECT", "INCORRECT", "NOT_ATTEMPTED"] = Field(..., description="Grade of the answer")


def _grade_answer(report_content, problem, answer, judge_model_config):
    client = OpenAI(base_url=judge_model_config["base_url"], api_key=judge_model_config["api_key"])

    completion = client.beta.chat.completions.parse(
        model=judge_model_config["model"],
        messages=[
            {"role": "user", "content": GRADER_TEMPLATE(problem, answer, report_content)},
        ],
        response_format=GradeAnswerModel,
    )
    return completion.choices[0].message.parsed
    
def grading_answer(report_path, problem, answer, judge_model_config):
    
    with open(report_path, 'r', encoding='utf-8') as f: 
        report_content = f.read()

    grade_answer_report = _grade_answer(report_content, problem, answer, judge_model_config)
        
    return grade_answer_report, report_content

def call_sgr_agent(agent, problem):
    # Make research request
    try:
        response = agent.chat.completions.create(
            model="sgr_auto_tool_calling_agent",
            messages=[{"role": "user", "content": problem}],
            temperature=0.4,
        )
        return True, None
    except Exception as ex:
        return False, str(ex)
    

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
        
    mean_correct = df["is_correct"].sum() / num_total_samples # Precision-like term over all samples

    accuracy_given_attempted_val = get_accuracy_given_attempted(df) # Recall-like term on attempted samples

    numerator = 2 * accuracy_given_attempted_val * mean_correct
    denominator = accuracy_given_attempted_val + mean_correct
    if denominator == 0:
        return 0.0
    return numerator / denominator