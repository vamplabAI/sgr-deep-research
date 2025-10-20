# Problem Statement

The objective of this research was to test the SGR Deep Research system and compare it with analogues.

# Methodology

The first step was to find a benchmark. During the search, it was decided to use SimpleQA as the benchmark. This is an open dataset from OpenAI designed to evaluate the factual accuracy of LLMs. It consists of 4326 questions and answers covering various topics: science, politics, sports, and others.
The dataset for this benchmark was taken from Hugging Face from here (https://huggingface.co/datasets/basicv8vc/SimpleQA).
For comparison with other search tools, the leaderboard from the ROMA repository was used (https://github.com/sentient-agi/ROMA).

The next step was the implementation of the testing logic. We isolated the `sgr_tool_calling_agent` and limited it to the following tools:

- ReasoningTool;
- WebSearchTool;
- ExtractPageContentTool;
- FinalAnswerTool.

System configuration during the benchmark run:

## ⚙️ Agent Configuration for Benchmark Run

| Component         | Parameter        | Value                  |
| ----------------- | ---------------- | ---------------------- |
| **Search Engine** | Provider         | Tavily Basic Search    |
|                   | Scraping Enabled | Yes                    |
|                   | Max Pages        | 5                      |
|                   | Content Limit    | 33,000 characters      |
| **Agent**         | Name             | sgr_tool_calling_agent |
|                   | Max Steps        | 20                     |
| **LLM (Agent)**   | Model            | gpt-4.1-mini           |
|                   | Max Tokens       | 12,000                 |
|                   | Temperature      | 0.2                    |
| **LLM (Judge)**   | Model            | gpt-4o                 |
|                   | Max Tokens       | Default                |
|                   | Temperature      | Default                |

# Results

![alt text](../assets/simpleqa_benchmark_comprasion.png)

As a result, our agent achieved an Accuracy = 0.861

Numbers:
232 million tokens
8k requests to /search
1200 requests to /extract
The full test of this benchmark cost $170

# Conclusions

Our result shows that even small LLMs, using the Schema-Guided Reasoning approach, can achieve quality comparable to LLMs on popular search tools.
