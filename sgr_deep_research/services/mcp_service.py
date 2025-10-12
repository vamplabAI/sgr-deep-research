import logging
from typing import Type

from fastmcp import Client
from jambo import SchemaConverter
from pydantic import create_model

from sgr_deep_research.core.tools import BaseTool, MCPBaseTool
from sgr_deep_research.settings import get_config

logger = logging.getLogger(__name__)


class Singleton(type):
    """Singleton metaclass."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class MCP2ToolConverter(metaclass=Singleton):
    def __init__(self):
        self.toolkit: list[Type[BaseTool]] = []
        if not get_config().mcp.transport_config:
            logger.warning("No MCP configuration found. MCP2ToolConverter will not function properly.")
            return
        self.client: Client = Client(get_config().mcp.transport_config)

    def _to_CamelCase(self, name: str) -> str:
        return name.replace("_", " ").title().replace(" ", "")

    async def build_tools_from_mcp(self):
        if not get_config().mcp.transport_config:
            logger.warning("No MCP configuration found. Nothing to build.")
            return

        async with self.client:
            mcp_tools = await self.client.list_tools()

            for t in mcp_tools:
                if not t.name or not t.inputSchema:
                    logger.error(f"Skipping tool due to missing name or input schema: {t}")
                    continue

                try:
                    t.inputSchema["title"] = self._to_CamelCase(t.name)
                    PdModel = SchemaConverter.build(t.inputSchema)
                except Exception as e:
                    logger.error(f"Error creating model {t.name} from schema: {t.inputSchema}: {e}")
                    continue

                ToolCls: Type[BaseTool] = create_model(
                    f"MCP{self._to_CamelCase(t.name)}", __base__=(PdModel, MCPBaseTool), __doc__=t.description or ""
                )
                ToolCls.tool_name = t.name
                ToolCls.description = t.description or ""
                ToolCls._client = self.client
                logger.info(f"Built MCP Tool: {ToolCls.tool_name}")
                self.toolkit.append(ToolCls)

            logger.info(f"Built {len(self.toolkit)} MCP tools.")
