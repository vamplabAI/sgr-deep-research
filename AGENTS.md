# Repository Guidelines

## Critical Rules
- Deterministic tests only: mock network/keys; prefer `pytest -q`. Name tests `test_*`; import schemas from `sgr_streaming.py` (no duplication).
- File creation: write artifacts to `logs/`, `reports/`, or `.tmp/`; never commit logs or secrets. Clean `.tmp/` after use.
- Feature changes: review `.kiro/steering/*` first; update those docs when behavior/structure/config changes.

## Project Structure & Module Organization
- Root: `config.yaml(.example)`, `requirements.txt`, utilities, connection tests.
- `sgr-classic/`: `sgr-deep-research.py`, scraping, version config/deps.
- `sgr-streaming/`: `sgr_streaming.py`, schema utils, visualizer, many `test_*.py` and `reports/`.
- `sgr_streaming_ec/`: EC loop entry `run.py`.
- Logs: `logs/`, `sgr-streaming/logs/`. Reports live under version dir or `reports_dir`.

## Build, Test, and Development Commands
- Env/deps: `python -m venv .venv && source .venv/bin/activate`; `pip install -r requirements.txt`; then install per-version inside its folder.
- Run: classic `python sgr-deep-research.py`; streaming `python sgr_streaming.py`; EC `python -m sgr_streaming_ec.run --query "Who built the first turbojet?" --max-steps 6`.
- Tests: `cd sgr-streaming && pytest -q`; root: `pytest -q test_*.py`. Use `.tmp/` for scratch, then clean.

## Coding Style & Naming Conventions
- Python (PEP 8), 4-space indent; add type hints where practical.
- Names: functions/vars `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Files: modules `snake_case.py`; tests `test_*.py` near related code.
- Keep functions small; isolate side effects.

## Testing Guidelines
- Use `pytest`; focus on schema validation, JSON parsing, plan/execute loops.
- Naming: `test_<area>.py`; functions `test_<behavior>()`.
- Deterministic runs; mock network; redact secrets in logs.
- Permanent tests beside modules (streaming). Use `.tmp/` for scratch.

## Commit & Pull Request Guidelines
- Commits: clear, imperative; Conventional Commits welcome (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Group related changes.
- PRs: summary, motivation, linked issues, repro/verify steps, and before/after logs or screenshots. Update docs/config examples when behavior changes.

## Security & Configuration Tips
- Never commit secrets. `config.yaml` is gitignored. Copy `config.yaml.example` → `config.yaml`; set `openai.api_key` and `tavily.api_key`.
- Review `logs/` and reports before sharing; they can include scraped/model output.
- Avoid hardcoded paths/keys; keep configuration external.

## Steering Docs (.kiro)
- See `.kiro/steering/` for deeper context and rules.
- `product.md`: goals, capabilities, and when to use each version.
- `structure.md`: directory layout, schema management rules (import models; do not duplicate), testing/demos placement, proxy notes.
- `tech.md`: stack, key dependencies, and useful debugging workflows (e.g., JSON parsing checks, local model flow).
