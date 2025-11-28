"""FastAPI application instance creation and configuration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sgr_deep_research import AgentFactory, __version__
from sgr_deep_research.api.endpoints import router
from sgr_deep_research.core import AgentRegistry, ToolRegistry
from sgr_deep_research.settings import setup_logging

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
