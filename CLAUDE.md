# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup configuration
cp config.yaml.example config.yaml
# Edit config.yaml with your API keys (OpenAI, Azure, Tavily)
# For custom Tavily servers (like SearXNG), set api_key to "" and configure api_base_url

# Install dependencies
uv sync
```

### Running the Server
```bash
# Start the API server
uv run python sgr_deep_research

# Custom host/port
uv run python sgr_deep_research --host 127.0.0.1 --port 8080
```

### CLI Usage
The system includes a command-line interface for direct agent interaction:

```bash
# Interactive mode (recommended)
uv run python -m sgr_deep_research.cli

# One-shot queries
uv run python -m sgr_deep_research.cli --query "Your research question"

# Select specific agent
uv run python -m sgr_deep_research.cli --agent sgr-tools --query "Research AI trends"

# Save results to file
uv run python -m sgr_deep_research.cli --query "Python best practices" --output report.md

# Deep research mode with levels (1-5+)
uv run python -m sgr_deep_research.cli --deep 1 --query "AI trends"    # 20 steps
uv run python -m sgr_deep_research.cli --deep 2 --query "AI research"  # 40 steps
uv run python -m sgr_deep_research.cli --deep 3 --query "Deep analysis" # 60 steps

# List available agents
uv run python -m sgr_deep_research.cli --list-agents

# Debug mode
uv run python -m sgr_deep_research.cli --debug --query "Your question"
```

**Available agent types:**
- `sgr` - Pure SGR implementation using Structured Output
- `sgr-tools` - SGR + Function Calling hybrid (recommended)
- `sgr-auto-tools` - SGR + Auto Function Calling
- `sgr-so-tools` - SGR + Structured Output tools
- `tools` - Pure Function Calling agent

**Interactive mode commands:**
- `help` - Show help
- `agents` - List available agents
- `agent <type>` - Switch agent type
- `deep <question>` - Deep research mode (20+ steps)
- `quit/exit/q` - Exit
- `<your question>` - Start research

**Research Depth Configuration:**
- **Normal mode**: 6 steps, 4 searches, ~1-2 min
- **Deep Level 1**: 24 steps, 8 searches, ~10-30 min
- **Deep Level 2**: 42 steps, 12 searches, ~20-60 min  
- **Deep Level 3**: 60 steps, 16 searches, ~30-90 min
- **Deep Level 4**: 78 steps, 20 searches, ~40-120 min

**Dynamic Deep Mode Features:**
- Exponential scaling: steps = 6 × (3×level + 1), searches = 4 × (level + 1)
- Each search can fetch up to 50 results (increased from 10)
- Agents automatically perform more comprehensive analysis
- Extended research time proportional to depth level

### Development Tools
```bash
# Format and lint code
make format
# This runs pre-commit hooks including ruff, docformatter, mdformat

# Clean build artifacts
make clean

# Build package
make all  # includes clean, format, and sdist
```

### Testing
The project uses pytest for testing:
```bash
uv run pytest                    # Run all tests
uv run pytest tests/            # Run specific test directory
uv run pytest -v               # Verbose output
uv run pytest --cov           # With coverage
```

### Docker Deployment
```bash
cd services
docker-compose build
docker-compose up -d
curl http://localhost:8010/health  # Check health
```

## Architecture Overview

### Core System Structure
This is a **Schema-Guided Reasoning (SGR)** system for automated research, built as a FastAPI service with OpenAI-compatible API.

**Key Architecture Components:**

1. **Agent System (`sgr_deep_research/core/agents/`)**:
   - `base_agent.py`: Base agent interface with state management
   - `sgr_agent.py`: Pure SGR implementation using Structured Output
   - `sgr_tools_agent.py`: SGR + Function Calling hybrid
   - `sgr_auto_tools_agent.py`: SGR + Auto Function Calling  
   - `sgr_so_tools_agent.py`: SGR + Structured Output tools
   - `tools_agent.py`: Pure Function Calling agent

2. **API Layer (`sgr_deep_research/api/`)**:
   - `endpoints.py`: FastAPI routes with OpenAI-compatible interface
   - `models.py`: Pydantic models for requests/responses
   - Supports streaming responses and agent interruption

3. **Core Tools (`sgr_deep_research/core/tools/`)**:
   - `research.py`: Web search, content scraping, report generation
   - `base.py`: Tool interface definitions
   - Integrated with Tavily API for web search

4. **Configuration (`sgr_deep_research/settings.py`)**:
   - YAML-based configuration with API keys
   - Supports OpenAI, Azure OpenAI, Tavily (including custom servers), proxy settings
   - Environment variable overrides

### Agent Selection Strategy
- **SGR vs Function Calling**: SGR forces structured reasoning for smaller models (<32B), Function Calling works better on large models (32B+)
- **Hybrid modes**: Combine SGR decision-making with FC execution
- **Agent interruption**: Agents can request clarification mid-execution

### Key Design Patterns

**Schema-Guided Reasoning Flow:**
1. Structured Output for decision making (NextStep schema)
2. Deterministic tool execution based on reasoning
3. Context-aware step limitation (max 6 steps)
4. Agent state persistence for clarification handling

**OpenAI API Compatibility:**
- Standard `/v1/chat/completions` endpoint
- Streaming responses with SSE
- Agent ID in model field for continuation
- Tool calls for clarification requests

### Important Files
- `config.yaml.example`: Configuration template
- `pyproject.toml`: Python project configuration and dependencies
- `.pre-commit-config.yaml`: Code quality automation (ruff, docformatter, etc.)
- `Makefile`: Build and development commands
- `sgr_deep_research/__main__.py`: Entry point for CLI/server

### Dependencies
- **Core**: OpenAI, Pydantic, FastAPI, Uvicorn
- **Research**: Tavily (search, supports custom servers), Trafilatura (scraping), YouTube-transcript-api
- **Utils**: Rich (CLI), PyYAML (config), httpx (HTTP with proxy support)
- **Dev**: Ruff (linting), Black/isort (formatting), pytest (testing)

### Notable Features
- **Multi-agent architecture**: 5 different agent types for various use cases  
- **Real-time streaming**: Full SSE support with agent state tracking
- **Agent interruption**: Clarification flow with conversation continuation
- **Comprehensive reporting**: Markdown reports with citations and sources
- **Docker deployment**: Production-ready containerization
- **Proxy support**: SOCKS5/HTTP proxy configuration for restricted environments

This system is designed for production use with extensible architecture for adding new reasoning schemas and research tools.

## Custom Search Integration

### Tavily-Compatible Custom Servers
The system supports custom Tavily-compatible search servers (like SearXNG with Tavily adapter):

1. **Configuration**: Set `tavily.api_key` to empty string and configure `api_base_url`
2. **Example**: SearXNG-Docker-Tavily-Adapter at `http://localhost:8013`
3. **Benefits**: No API costs, local search control, privacy-focused


## USE SUB-AGENTS FOR CONTEXT OPTIMIZATION

### 1. Always use the file-analyzer sub-agent when asked to read files.
The file-analyzer agent is an expert in extracting and summarizing critical information from files, particularly log files and verbose outputs. It provides concise, actionable summaries that preserve essential information while dramatically reducing context usage.

### 2. Always use the code-analyzer sub-agent when asked to search code, analyze code, research bugs, or trace logic flow.

The code-analyzer agent is an expert in code analysis, logic tracing, and vulnerability detection. It provides concise, actionable summaries that preserve essential information while dramatically reducing context usage.

### 3. Always use the test-runner sub-agent to run tests and analyze the test results.

Using the test-runner agent ensures:

- Full test output is captured for debugging
- Main conversation stays clean and focused
- Context usage is optimized
- All issues are properly surfaced
- No approval dialogs interrupt the workflow
