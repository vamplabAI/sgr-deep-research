# Add Support for Qwen3-Thinking Models via Function Calling

## Overview

This PR introduces comprehensive support for **qwen3-thinking models**, which do not support Structured Output (SO) but work excellently through Function Calling (FC). The implementation maintains full compatibility with the SGR framework while enabling the use of thinking models that provide intermediate reasoning in their outputs.

## Key Features

### 1. Universal Pydantic to Function Calling Converter
- **File**: `sgr_deep_research/core/utils/pydantic_convert.py`
- Automatic JSON Schema generation from Pydantic models
- Support for complex types: `Literal`, `Optional`, `Union`, `List`, `Dict`
- Handles nested models and constraints (min/max, length, pattern)

### 2. Qwen3-Thinking Response Adapter
- **File**: `sgr_deep_research/core/adapters/qwen3_thinking_adapter.py`
- Three-strategy extraction from "dirty" thinking model outputs:
  - Strategy 1: `tool_calls` with JSON in `arguments`
  - Strategy 2: `content` with `<tool_call>...</tool_call>` tags (priority)
  - Strategy 3: `content` with raw JSON (fallback)
- Robust parsing with detailed error diagnostics

### 3. SGRQwen3ThinkingAgent
- **File**: `sgr_deep_research/core/agents/sgr_qwen3_thinking_agent.py`
- Full-featured SGR agent adapted for thinking models
- Uses Function Calling instead of Structured Output
- Modified system prompt with thinking model instructions
- Maintains complete SGR architecture: reasoning → action → evaluation

## Documentation & Examples

- **Comprehensive Documentation**: `docs/QWEN3_THINKING_SUPPORT.md`
  - Detailed component descriptions
  - Configuration examples
  - Usage patterns
  - Troubleshooting guide
  - Performance comparison with instruct models

- **Practical Examples**: `examples/qwen3_thinking_example.py`
  - Basic usage
  - Clarification handling
  - Configuration loading

## ️ Architecture

```
SGRQwen3ThinkingAgent
│
├── Pydantic → FC Conversion (pydantic_convert.py)
│   └── Auto-generates OpenAI Function Calling schema
│
├── Modified System Prompt
│   └── Includes thinking model instructions + dynamic schema
│
├── Reasoning Phase (Function Calling)
│   └── LLM generates reasoning + tool call
│
├── Response Extraction (qwen3_thinking_adapter.py)
│   └── Extracts structured data from mixed output
│
└── Action & Evaluation
    └── Standard SGR flow
```

## Design Decisions

1. **Function Calling over Structured Output**: Thinking models don't support SO, but FC provides equivalent functionality while preserving reasoning visibility

2. **Multi-Strategy Extraction**: Thinking models can output in various formats depending on vLLM configuration - the adapter handles all cases gracefully

3. **Modified System Prompt**: Incorporates base prompt from config + schema + thinking-specific instructions

4. **Full SGR Compatibility**: Maintains all SGR agent features (clarifications, planning, tool selection, etc.)

## Backward Compatibility

This PR:
- Does not modify existing agents or tools
- Adds new optional components
- Works alongside standard SGR agents
- Uses existing configuration system from `agents-config-definitions` branch

## Configuration

### config.yaml
```yaml
llm:
  model: "Qwen/Qwen3-14B-thinking"
  temperature: 0.3
  max_tokens: 12000
```

### agents.yaml
```yaml
agents:
  - name: "qwen3_thinking_agent"
    base_class: "SGRQwen3ThinkingAgent"
    llm:
      model: "Qwen/Qwen3-14B-thinking"
    tools:
      - "WebSearchTool"
      - "CreateReportTool"
      - "FinalAnswerTool"
```

