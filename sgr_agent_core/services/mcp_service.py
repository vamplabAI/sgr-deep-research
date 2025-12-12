import logging
from typing import Type

from fastmcp import Client
from fastmcp.mcp_config import MCPConfig
from jambo import SchemaConverter
from pydantic import create_model

logger = logging.getLogger(__name__)


class MCP2ToolConverter:
    @staticmethod
    def _to_CamelCase(name: str) -> str:
        return name.replace("_", " ").title().replace(" ", "")

    @classmethod
    async def build_tools_from_mcp(cls, config: MCPConfig):
        from sgr_agent_core import BaseTool, MCPBaseTool

        tools = []
        if not config.mcpServers:
            return tools

        client: Client = Client(config)
        async with client:
            mcp_tools = await client.list_tools()

            for t in mcp_tools:
                if not t.name or not t.inputSchema:
                    logger.error(f"Skipping tool due to missing name or input schema: {t}")
                    continue

                try:
                    t.inputSchema["title"] = cls._to_CamelCase(t.name)
                    PdModel = SchemaConverter.build(t.inputSchema)
                except Exception as e:
                    logger.error(f"Error creating model {t.name} from schema: {t.inputSchema}: {e}")
                    continue

                ToolCls: Type[BaseTool] = create_model(
                    f"MCP{cls._to_CamelCase(t.name)}", __base__=(PdModel, MCPBaseTool), __doc__=t.description or ""
                )
                ToolCls.tool_name = t.name
                ToolCls.description = t.description or ""
                ToolCls._client = client
                tools.append(ToolCls)
                logger.info(f"Built MCP Tool: {ToolCls.tool_name}")

            logger.info(f"Built {len(tools)} MCP tools.")
            return tools
