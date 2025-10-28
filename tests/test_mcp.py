"""Tests for MCP (Model Context Protocol) integration.

This module contains comprehensive tests for MCPBaseTool and MCP2ToolConverter,
including mocking of FastMCP Client and tool creation from MCP schemas.
"""

import json
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, Field

from sgr_deep_research.core.base_tool import BaseTool, MCPBaseTool
from sgr_deep_research.core.models import ResearchContext


class TestMCPBaseTool:
    """Tests for MCPBaseTool base class."""

    def test_mcp_base_tool_inherits_from_base_tool(self):
        """Test that MCPBaseTool inherits from BaseTool."""
        assert issubclass(MCPBaseTool, BaseTool)

    def test_mcp_base_tool_has_client_attribute(self):
        """Test that MCPBaseTool has _client class variable."""
        assert hasattr(MCPBaseTool, "_client")

    def test_mcp_base_tool_client_is_class_var(self):
        """Test that _client is a ClassVar."""
        # Check that _client is defined as ClassVar in annotations
        assert "_client" in MCPBaseTool.__annotations__

    def test_mcp_base_tool_client_default_is_none(self):
        """Test that _client defaults to None."""
        assert MCPBaseTool._client is None

    def test_mcp_base_tool_can_be_instantiated(self):
        """Test that MCPBaseTool can be instantiated."""
        tool = MCPBaseTool()
        assert isinstance(tool, MCPBaseTool)
        assert isinstance(tool, BaseTool)

    def test_mcp_base_tool_subclass_can_set_client(self):
        """Test that subclass can set custom _client."""
        class CustomMCPTool(MCPBaseTool):
            _client: ClassVar = Mock()

        assert CustomMCPTool._client is not None
        assert isinstance(CustomMCPTool._client, Mock)

    @pytest.mark.asyncio
    async def test_mcp_base_tool_call_with_mock_client_success(self):
        """Test MCPBaseTool __call__ with successful mock client."""
        # Create mock client
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.content = [
            Mock(model_dump_json=Mock(return_value='{"result": "test"}'))
        ]
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Create tool with mock client
        class TestMCPTool(MCPBaseTool):
            test_field: str = Field(default="test")
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        result = await tool(context)
        
        assert isinstance(result, str)
        assert "test" in result.lower()

    @pytest.mark.asyncio
    async def test_mcp_base_tool_call_passes_payload(self):
        """Test that __call__ passes correct payload to client."""
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(model_dump_json=Mock(return_value='{}'))]
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        class TestMCPTool(MCPBaseTool):
            param1: str = "value1"
            param2: int = 42
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        await tool(context)
        
        # Verify call_tool was called with correct arguments
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args
        assert call_args[0][0] == "test_tool"  # tool name
        assert call_args[0][1]["param1"] == "value1"  # payload
        assert call_args[0][1]["param2"] == 42

    @pytest.mark.asyncio
    async def test_mcp_base_tool_call_handles_error(self):
        """Test that __call__ handles errors gracefully."""
        mock_client = AsyncMock()
        mock_client.call_tool = AsyncMock(side_effect=Exception("MCP Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        class TestMCPTool(MCPBaseTool):
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        result = await tool(context)
        
        assert "Error" in result
        assert "MCP Error" in result

    @pytest.mark.asyncio
    @patch("sgr_deep_research.core.base_tool.config")
    async def test_mcp_base_tool_call_truncates_by_context_limit(self, mock_config):
        """Test that result is truncated by context_limit."""
        mock_config.mcp.context_limit = 20
        
        mock_client = AsyncMock()
        mock_result = Mock()
        long_content = "A" * 100
        mock_result.content = [
            Mock(model_dump_json=Mock(return_value=f'"{long_content}"'))
        ]
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        class TestMCPTool(MCPBaseTool):
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        result = await tool(context)
        
        assert len(result) == 20

    @pytest.mark.asyncio
    async def test_mcp_base_tool_call_multiple_content_items(self):
        """Test __call__ with multiple content items."""
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.content = [
            Mock(model_dump_json=Mock(return_value='{"item": 1}')),
            Mock(model_dump_json=Mock(return_value='{"item": 2}')),
            Mock(model_dump_json=Mock(return_value='{"item": 3}'))
        ]
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        class TestMCPTool(MCPBaseTool):
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        result = await tool(context)
        
        # Should be a JSON array containing all items
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert '{"item": 1}' in parsed
        assert '{"item": 2}' in parsed
        assert '{"item": 3}' in parsed

    @pytest.mark.asyncio
    async def test_mcp_base_tool_call_ensures_ascii_false(self):
        """Test that JSON dumps uses ensure_ascii=False for Unicode."""
        mock_client = AsyncMock()
        mock_result = Mock()
        unicode_content = "世界"
        mock_result.content = [
            Mock(model_dump_json=Mock(return_value=f'"{unicode_content}"'))
        ]
        mock_client.call_tool = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        class TestMCPTool(MCPBaseTool):
            _client: ClassVar = mock_client

        TestMCPTool.tool_name = "test_tool"
        
        tool = TestMCPTool()
        context = ResearchContext()
        
        result = await tool(context)
        
        # Unicode should be preserved (not escaped)
        assert unicode_content in result


class TestMCP2ToolConverter:
    """Tests for MCP2ToolConverter Singleton class."""

    def test_mcp2tool_converter_is_singleton(self):
        """Test that MCP2ToolConverter follows Singleton pattern."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        instance1 = MCP2ToolConverter()
        instance2 = MCP2ToolConverter()
        
        assert instance1 is instance2

    @patch("sgr_deep_research.services.mcp_service.get_config")
    def test_mcp2tool_converter_init_without_config(self, mock_get_config):
        """Test initialization when MCP config is not present."""
        mock_config = Mock()
        mock_config.mcp.transport_config = None
        mock_get_config.return_value = mock_config
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        # Clear singleton instance
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        
        assert converter.toolkit == []
        assert not hasattr(converter, "client")

    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    def test_mcp2tool_converter_init_with_config(self, mock_client_class, mock_get_config):
        """Test initialization with valid MCP config."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        # Clear singleton
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        
        assert hasattr(converter, "client")
        mock_client_class.assert_called_once_with({"type": "stdio"})

    def test_to_camel_case_simple(self):
        """Test _to_CamelCase with simple snake_case."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        converter = MCP2ToolConverter()
        
        assert converter._to_CamelCase("test_tool") == "TestTool"
        assert converter._to_CamelCase("my_function") == "MyFunction"

    def test_to_camel_case_single_word(self):
        """Test _to_CamelCase with single word."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        converter = MCP2ToolConverter()
        
        assert converter._to_CamelCase("test") == "Test"

    def test_to_camel_case_already_camel(self):
        """Test _to_CamelCase with already CamelCase input."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        converter = MCP2ToolConverter()
        
        assert converter._to_CamelCase("TestTool") == "Testtool"

    def test_to_camel_case_multiple_underscores(self):
        """Test _to_CamelCase with multiple underscores."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        converter = MCP2ToolConverter()
        
        assert converter._to_CamelCase("test_my_long_tool_name") == "TestMyLongToolName"

    def test_to_camel_case_with_numbers(self):
        """Test _to_CamelCase with numbers."""
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        converter = MCP2ToolConverter()
        
        assert converter._to_CamelCase("test_tool_2") == "TestTool2"

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    async def test_build_tools_without_config(self, mock_get_config):
        """Test build_tools_from_mcp when config is missing."""
        mock_config = Mock()
        mock_config.mcp.transport_config = None
        mock_get_config.return_value = mock_config
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        # Clear singleton
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        assert converter.toolkit == []

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    @patch("sgr_deep_research.services.mcp_service.SchemaConverter")
    @patch("sgr_deep_research.services.mcp_service.create_model")
    async def test_build_tools_basic(
        self, mock_create_model, mock_schema_converter, mock_client_class, mock_get_config
    ):
        """Test basic tool building from MCP."""
        # Setup config
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        # Setup client
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {"param": {"type": "string"}}
        }
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        # Setup schema converter
        mock_pydantic_model = Mock()
        mock_schema_converter.build.return_value = mock_pydantic_model
        
        # Setup create_model
        mock_tool_class = Mock()
        mock_tool_class.tool_name = "test_tool"
        mock_tool_class.description = "Test tool description"
        mock_create_model.return_value = mock_tool_class
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        # Clear singleton
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        assert len(converter.toolkit) == 1
        assert converter.toolkit[0].tool_name == "test_tool"

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    async def test_build_tools_skips_tool_without_name(self, mock_client_class, mock_get_config):
        """Test that tools without name are skipped."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = None  # No name
        mock_tool.inputSchema = {"type": "object"}
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        assert len(converter.toolkit) == 0

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    async def test_build_tools_skips_tool_without_schema(self, mock_client_class, mock_get_config):
        """Test that tools without inputSchema are skipped."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.inputSchema = None  # No schema
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        assert len(converter.toolkit) == 0

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    @patch("sgr_deep_research.services.mcp_service.SchemaConverter")
    async def test_build_tools_handles_schema_error(
        self, mock_schema_converter, mock_client_class, mock_get_config
    ):
        """Test handling of schema conversion errors."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test"
        mock_tool.inputSchema = {"type": "invalid"}
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        # Make schema converter raise error
        mock_schema_converter.build.side_effect = Exception("Schema error")
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        # Should skip tool with error
        assert len(converter.toolkit) == 0

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    @patch("sgr_deep_research.services.mcp_service.SchemaConverter")
    @patch("sgr_deep_research.services.mcp_service.create_model")
    async def test_build_tools_multiple_tools(
        self, mock_create_model, mock_schema_converter, mock_client_class, mock_get_config
    ):
        """Test building multiple tools."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tools = [
            Mock(name="tool1", description="Tool 1", inputSchema={"type": "object"}),
            Mock(name="tool2", description="Tool 2", inputSchema={"type": "object"}),
            Mock(name="tool3", description="Tool 3", inputSchema={"type": "object"}),
        ]
        mock_client.list_tools = AsyncMock(return_value=mock_tools)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        mock_pydantic_model = Mock()
        mock_schema_converter.build.return_value = mock_pydantic_model
        
        def create_tool_class(name, **kwargs):
            tool_class = Mock()
            tool_class.tool_name = name.replace("MCP", "").lower()
            return tool_class
        
        mock_create_model.side_effect = create_tool_class
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        assert len(converter.toolkit) == 3

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    @patch("sgr_deep_research.services.mcp_service.SchemaConverter")
    @patch("sgr_deep_research.services.mcp_service.create_model")
    async def test_build_tools_sets_client_reference(
        self, mock_create_model, mock_schema_converter, mock_client_class, mock_get_config
    ):
        """Test that built tools have _client reference set."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test"
        mock_tool.inputSchema = {"type": "object"}
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        mock_pydantic_model = Mock()
        mock_schema_converter.build.return_value = mock_pydantic_model
        
        mock_tool_class = Mock()
        mock_create_model.return_value = mock_tool_class
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        # Verify _client was set
        assert mock_tool_class._client == mock_client

    @pytest.mark.asyncio
    @patch("sgr_deep_research.services.mcp_service.get_config")
    @patch("sgr_deep_research.services.mcp_service.Client")
    @patch("sgr_deep_research.services.mcp_service.SchemaConverter")
    @patch("sgr_deep_research.services.mcp_service.create_model")
    async def test_build_tools_schema_title_set(
        self, mock_create_model, mock_schema_converter, mock_client_class, mock_get_config
    ):
        """Test that schema title is set to CamelCase tool name."""
        mock_config = Mock()
        mock_config.mcp.transport_config = {"type": "stdio"}
        mock_get_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test"
        mock_tool.inputSchema = {"type": "object"}
        mock_client.list_tools = AsyncMock(return_value=[mock_tool])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        
        mock_pydantic_model = Mock()
        mock_schema_converter.build.return_value = mock_pydantic_model
        mock_create_model.return_value = Mock()
        
        from sgr_deep_research.services.mcp_service import MCP2ToolConverter
        
        if MCP2ToolConverter in MCP2ToolConverter._instances:
            del MCP2ToolConverter._instances[MCP2ToolConverter]
        
        converter = MCP2ToolConverter()
        await converter.build_tools_from_mcp()
        
        # Check that schema converter was called with modified schema
        called_schema = mock_schema_converter.build.call_args[0][0]
        assert called_schema["title"] == "TestTool"

