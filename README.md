# 🧠 SGR Deep Research - Open-Source Schema-Guided Reasoning System

## 📚 Documents

[Project's Wiki](https://github.com/vamplabAI/sgr-deep-research/wiki) - Main documentation of project

[Quick start](https://github.com/vamplabAI/sgr-deep-research/wiki/SGR-Quick-Start) - Data for quick start

[Description API](https://github.com/vamplabAI/sgr-deep-research/wiki/SGR-Description-API) - Description API with examples using

## 📊 Benchmarking with SimpleQA

We conducted a comprehensive benchmark evaluation using the [SimpleQA](https://huggingface.co/datasets/basicv8vc/SimpleQA) dataset - a factuality benchmark that measures the ability of language models to answer short, fact-seeking questions.

### Our Benchmark Results

![SimpleQA Benchmark Comparison](docs/simpleqa_benchmark_comprasion.png)

**Performance Metrics:**

- **Accuracy:** 86.08%
- **Correct:** 3,724 answers
- **Incorrect:** 554 answers
- **Not Attempted:** 48 answers

**Benchmark Configuration:**

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

Detailed benchmark results are available in [this spreadsheet](docs/simpleqa_result.xlsx).

______________________________________________________________________

## 📖 Description

Production-ready open-source system for automated research using Schema-Guided Reasoning (SGR). Features real-time streaming responses, OpenAI-compatible API, and comprehensive research capabilities with agent interruption support.

SGR Deep Research is an agent-driven research system with a chat interface. It can run with small LLMs for a fully local mode.

This project is developed by the **neuraldeep** community. It is inspired by the Schema-Guided Reasoning (SGR) work and [SGR Agent Demo](https://abdullin.com/schema-guided-reasoning/demo) delivered by "LLM Under the Hood" community and AI R&D Hub of [TIMETOACT GROUP Österreich](https://www.timetoact-group.at)

If you have any questions - feel free to reach out to [Valerii Kovalskii](https://www.linkedin.com/in/vakovalskii/).

## 🚀 Main use-cases

### The SGR system excels at various research scenarios:

- **Market Research**: "Analyze BMW X6 2025 pricing across European markets"
- **Technology Trends**: "Research current developments in quantum computing"
- **Competitive Analysis**: "Compare features of top 5 CRM systems in 2024"
- **Industry Reports**: "Investigate renewable energy adoption in Germany"

### Schema-Guided Reasoning Capabilities:

1. **🤔 Clarification** - clarifying questions when unclear
2. **📋 Plan Generation** - research plan creation
3. **🔍 Web Search** - internet information search
4. **🔄 Plan Adaptation** - plan adaptation based on results
5. **📝 Report Creation** - detailed report creation
6. **✅ Completion** - task completion

## 👥 Open-Source Development Team

### This project is built by the community with pure enthusiasm as an open-source initiative:

- **SGR Concept Creator** // [@abdullin](https://t.me/llm_under_hood)
- **Project Coordinator & Vision** // [@VaKovaLskii](https://t.me/neuraldeep)
- **Lead Core Developer** // [@virrius](https://t.me/virrius_tech)
- **API Development** // [Pavel Zloi](https://t.me/evilfreelancer)
- **Hybrid FC Mode** // [@Shadekss](https://t.me/Shadekss)
- **DevOps & Deployment** // [@mixaill76](https://t.me/mixaill76)

*All development is driven by pure enthusiasm and open-source community collaboration. We welcome contributors of all skill levels!*
