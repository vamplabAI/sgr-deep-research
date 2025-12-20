"""Main entry point for SGR Agent Core API server."""

import logging
from pathlib import Path

import uvicorn
from app import app
from default_definitions import get_default_agents_definitions
from settings import ServerConfig

from sgr_agent_core.agent_config import GlobalConfig

logger = logging.getLogger(__name__)


def main():
    """Start FastAPI server."""
    args = ServerConfig()

    config = GlobalConfig.from_yaml(args.config_file)
    config.agents.update(get_default_agents_definitions())

    # Load agents from separate file if exists
    if args.agents_file:
        agents_path = Path(args.agents_file)
        if agents_path.exists():
            # Check if file is not empty
            agents_content = agents_path.read_text(encoding="utf-8").strip()
            if not agents_content:
                logger.warning(f"Agents file '{agents_path}' is empty, skipping")
            else:
                config.definitions_from_yaml(args.agents_file)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
