# Repository Guidelines

## Project Structure & Module Organization
Code lives in `sgr_deep_research/`: `api/` serves FastAPI, `cli.py` powers the UV CLI, `core/` and `services/` host agents and tools, and `flows/` contains Prefect orchestration. Prompts live in `prompts/`; batch artefacts reside in `batches/`, `batch_results/`, and `reports/`. Keep tests at the repo root as `test_*.py` modules.

## Environment & Configuration Setup
Install UV (`curl -LsSf https://astral.sh/uv/install.sh | sh`), copy `config.yaml.example` to `config.yaml`, and add OpenAI, Azure, and Tavily credentials. Set `tavily.api_key=""` for local adapters, use env vars in CI, and document new knobs and proxy tips in the example file.

## Build, Test, and Development Commands
- `uv sync`: install dependencies into `.venv` from `uv.lock`.
- `uv run python -m sgr_deep_research.cli -i`: launch the interactive CLI.
- `uv run python -m sgr_deep_research.cli --query "Topic" --agent sgr-tools`: run a single-shot session with a chosen agent.
- `uv run python sgr_deep_research`: start the FastAPI server.
- `uv run pytest [--cov=sgr_deep_research]`: run tests and optional coverage.
- `uv run ruff check . --fix` / `uv run ruff format .`: lint and format.
- `make format`: execute the pre-commit bundle.

## API Usage Patterns

### Streaming API (Existing)
Use `/v1/chat/completions` for quick interactive queries and real-time development:
```bash
curl -X POST http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "sgr-tools", "messages": [{"role": "user", "content": "Quick research query"}], "stream": true}'
```

### Jobs API (New - Long-Running Operations)
Use `/jobs` endpoints for multi-hour calculations and batch processing:
```bash
# Submit long-running job
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "Deep research topic", "agent_type": "sgr-tools", "deep_level": 2}'

# Check job status
curl http://localhost:8010/jobs/{job_id}

# Stream real-time updates
curl -N http://localhost:8010/jobs/{job_id}/stream
```

## Agent Modes & Research Depth
Agents include `sgr` (pure SGR), `sgr-tools` (default hybrid), `sgr-auto-tools`, `sgr-so-tools`, and `tools` (function calling). In interactive mode list options with `agents` and switch via `agent <type>`. Deep research scales ≈ `6 × (3 × level + 1)` steps and `4 × (level + 1)` searches; `deep 2 "topic"` or `batch-deep 2 "topic"` yield ~40-step Prefect runs.

## Coding Style & Naming Conventions
Target Python 3.10+, 4-space indentation, and LF endings. Ruff enforces a 120-character limit and import ordering; keep modules/functions snake_case, classes PascalCase, constants UPPER_CASE, and docstrings concise. Prefer typed pydantic settings objects over ad-hoc dictionaries.

## Testing Guidelines
Use `pytest`, naming files `test_<feature>.py` and async fixtures `_async`. Cover new agents with unit tests plus CLI smoke checks (`uv run pytest -k agent`). Require a clean `uv run pytest --cov`; justify skips or xfails in the PR.

## Commit & Pull Request Guidelines
Follow Conventional Commits (`feat:`, `fix:`, `refactor:`). PRs should state motivation, behavioural change, verification commands, and linked issues. Include updated CLI examples or config diffs when workflows change, and share logs or reports only when they unblock review.

## Deployment Notes
Run `docker-compose` in `services/` for container setups (`docker-compose up -d`; `curl http://localhost:8010/health` to verify). Prefect batch flows write Markdown artefacts to `batch_results/`.
