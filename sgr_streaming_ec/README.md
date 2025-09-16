# Error-Corrected Streaming (ECS)

This module adds a *plan → execute → critic → (commit|retry/backtrack)* loop that reduces self-conditioning drift in small models.

**Run**
```bash
python -m sgr_streaming_ec.run --query "Who built the first turbojet and when?" --max-steps 8
Output
- Prints a concise Markdown report to the console.
- Saves the report to the configured `reports_dir` (default: `reports/`) as `YYYYMMDD_HHMMSS_<query>.md`.
