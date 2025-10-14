"""Основная точка входа для SGR Deep Research API сервера."""

import argparse
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from sgr_deep_research import __version__
from sgr_deep_research.api.endpoints import router
from sgr_deep_research.services import MCP2ToolConverter
from sgr_deep_research.settings import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await MCP2ToolConverter().build_tools_from_mcp()
    yield


app = FastAPI(title="SGR Deep Research API", version=__version__, lifespan=lifespan)
app.include_router(router)


def main():
    """Запуск FastAPI сервера."""

    parser = argparse.ArgumentParser(description="SGR Deep Research Server")
    parser.add_argument(
        "--host", type=str, dest="host", default=os.environ.get("HOST", "0.0.0.0"), help="Хост для прослушивания"
    )
    parser.add_argument(
        "--port", type=int, dest="port", default=int(os.environ.get("PORT", 8010)), help="Порт для прослушивания"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
