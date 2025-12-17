"""Main entry point for SGR Agent Core API server."""

import uvicorn

from sgr_agent_core.agent_config import GlobalConfig
from sgr_deep_research.app import app
from sgr_deep_research.default_definitions import get_default_agents_definitions
from sgr_deep_research.settings import ServerConfig


def main():
    """Start FastAPI server."""
    args = ServerConfig()

    config = GlobalConfig.from_yaml(args.config_file)
    config.agents.update(get_default_agents_definitions())
    config.definitions_from_yaml(args.agents_file)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
