"""Main entry point for SGR Agent Core API server."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sgr_deep_research import AgentFactory, __version__
from sgr_deep_research.api.endpoints import router
from sgr_deep_research.core import AgentRegistry, ToolRegistry
from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.default_definitions import get_default_agents_definitions
from sgr_deep_research.settings import ServerConfig, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for tool in ToolRegistry.list_items():
        logger.info(f"Tool registered: {tool.__name__}")
    for agent in AgentRegistry.list_items():
        logger.info(f"Agent registered: {agent.__name__}")
    for defn in AgentFactory.get_definitions_list():
        logger.info(f"Agent definition loaded: {defn}")
    yield


def main():
    """Start FastAPI server."""
    args = ServerConfig()
    config = GlobalConfig.from_yaml(args.config_file)
    config.agents.update(get_default_agents_definitions())
    config.definitions_from_yaml(args.agents_file)
    app = FastAPI(title="SGR Deep Research API", version=__version__, lifespan=lifespan)
    # Don't use this CORS setting in production!
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
