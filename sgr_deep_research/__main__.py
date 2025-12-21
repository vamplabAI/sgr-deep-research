"""Main entry point for SGR Agent Core API server."""

import logging
from pathlib import Path

import uvicorn
import yaml

from sgr_agent_core.agent_config import GlobalConfig
from sgr_deep_research.app import app
from sgr_deep_research.default_definitions import get_default_agents_definitions
from sgr_deep_research.settings import ServerConfig

logger = logging.getLogger(__name__)


def load_config(config_file: str, agents_file: str | None = None) -> GlobalConfig:
    """Load configuration and agents from YAML files.

    This function implements the configuration loading logic:
    1. Load config.yaml (including agents section if present)
    2. Add default agents
    3. Load agents.yaml if provided (overrides existing agents)

    Args:
        config_file: Path to config.yaml file
        agents_file: Optional path to agents.yaml file

    Returns:
        GlobalConfig instance with loaded configuration and agents
    """
    config = GlobalConfig.from_yaml(config_file)
    config.agents.update(get_default_agents_definitions())

    # Load agents from separate file if exists
    if agents_file and Path(agents_file).exists():
        try:
            config.definitions_from_yaml(agents_file)
        except ValueError as e:
            logger.error(f"Invalid agents file format '{agents_file}': {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in agents file '{agents_file}': {e}")
            raise

    return config


def main():
    """Start FastAPI server."""
    args = ServerConfig()

    load_config(args.config_file, args.agents_file)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
