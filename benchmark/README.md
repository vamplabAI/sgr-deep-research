# 📊 SGR Deep Research Benchmark

Benchmark suite for evaluating SGR Deep Research agent performance using SimpleQA dataset.

## 🚀 Quick Start

### 1. Setup Environment

Create `.env` file from example:

```bash
cp env.example .env
```

Edit `.env` with your judge model settings:

```bash
JUDGE_BASE_URL=https://api.openai.com/v1
JUDGE_API_KEY=your-api-key-here
JUDGE_MODEL_NAME=gpt-4o-mini
```

### 2. Download SimpleQA Dataset

Download SimpleQA Verified from [Kaggle](https://www.kaggle.com/datasets/deepmind/simpleqa-verified/data) and place `simpleqa_verified.csv` in your data directory.

### 3. Run Benchmark

```bash
# Process 100 samples with batch size 3
python benchmark_agent.py \
    --path_to_simpleqa ./data/simpleqa_verified.csv \
    --output_path ./simpleqa_bench_results.xlsx \
    --n_samples 100 \
    --batch_size 3
```

## 📋 Configuration

### Environment Variables

| Variable           | Description                              | Example                          |
| ------------------ | ---------------------------------------- | -------------------------------- |
| `JUDGE_BASE_URL`   | Base URL for judge model API             | `https://api.openai.com/v1`      |
| `JUDGE_API_KEY`    | API key for judge model                  | `sk-...`                         |
| `JUDGE_MODEL_NAME` | Judge model name                         | `gpt-4o-mini`                    |

### Command Line Arguments

| Parameter            | Required | Default                     | Description                                |
| -------------------- | -------- | --------------------------- | ------------------------------------------ |
| `--path_to_simpleqa` | Yes      | -                           | Path to simpleqa_verified.csv dataset      |
| `--output_path`      | No       | simpleqa_bench_results.xlsx | Output Excel file path                     |
| `--n_samples`        | No       | All samples                 | Number of samples to process               |
| `--batch_size`       | No       | 10                          | Number of questions to process in parallel |

## 📊 Output

The benchmark generates an Excel file with:

- **question**: Original question from SimpleQA
- **answer**: Ground truth answer
- **predicted_answer**: Answer from SGR agent
- **grade_str**: Grade (CORRECT/INCORRECT/NOT_ATTEMPTED)
- **is_correct**: Boolean flag for correct answers
- **is_incorrect**: Boolean flag for incorrect answers
- **is_not_attempted**: Boolean flag for not attempted answers
- **fail_search**: Boolean flag for failed attempts
- **grade_answer_report**: Detailed grading report from judge
- **Error text**: Error message if any

## ✨ Features

### 🔄 Auto-Resume

If interrupted, the benchmark automatically resumes from the last completed question. Just rerun the same command.

### 📊 Batch Processing

Process multiple questions in parallel for faster execution. Adjust `--batch_size` based on your system capacity.

### 📝 Detailed Logging

Real-time logs show:
- Config file being used
- Batch progress (e.g., "Начался батч 3/10")
- Number of processed questions
- Completion status

Example log output:

```
2024-01-13 12:00:00 - __main__ - INFO - Using config file: C:\path\to\config.yaml
2024-01-13 12:00:05 - __main__ - INFO - Начался батч 1/34 (вопросы 1-3)
2024-01-13 12:00:45 - __main__ - INFO - Завершен батч 1/34. Обработано вопросов: 3/100
```

## 🎯 Judge Model Options

**Recommended Models:**
- `gpt-4o-mini` - Best cost/accuracy balance
- `gpt-4o` - Highest accuracy
- `claude-3-sonnet` - Alternative provider
- Local models - Use your own endpoint

## 🛠️ Architecture

### BenchmarkAgent

Extends `SGRToolCallingResearchAgent` with tools:
- GeneratePlanTool
- AdaptPlanTool
- ReasoningTool
- WebSearchTool
- ExtractPageContentTool
- FinalAnswerTool

### Grading Process

1. Agent processes question and generates answer
2. Answer is extracted from agent's execution result
3. Judge model evaluates answer against ground truth
4. Grade is assigned: CORRECT/INCORRECT/NOT_ATTEMPTED
5. Results are saved to Excel with detailed report

## 📁 Files

- `benchmark_agent.py` - Main benchmark script
- `prompts.py` - Grading prompt templates
- `env.example` - Environment variables example
- `README.md` - This file

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows project style
- Tests pass
- Documentation is updated

