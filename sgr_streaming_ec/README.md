# Error-Corrected Streaming (ECS)

This module adds a *plan → execute → critic → (commit|retry/backtrack)* loop that reduces self-conditioning drift in small models.

**Run**
```bash
python -m sgr_streaming_ec.run --query "Who built the first turbojet and when?" --max-steps 8
