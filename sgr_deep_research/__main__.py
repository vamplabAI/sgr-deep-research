"""Основная точка входа для SGR Agent Core API сервера."""

import argparse
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sgr_deep_research import __version__
from sgr_deep_research.api.endpoints import router
from sgr_deep_research.services import MCP2ToolConverter
from sgr_deep_research.settings import get_config, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await MCP2ToolConverter().build_tools_from_mcp()
    yield


app = FastAPI(title="SGR Agent Core API", version=__version__, lifespan=lifespan)

config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS enabled for origins: http://localhost:5173")

app.include_router(router)


def main():
    """Запуск FastAPI сервера."""

    parser = argparse.ArgumentParser(description="SGR Agent Core Server")
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
