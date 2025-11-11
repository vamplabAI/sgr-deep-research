"""Tests for BenchmarkAgent.

This module contains comprehensive tests for the BenchmarkAgent class,
including initialization, tool preparation, and execution flow for
benchmarking.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from benchmark.benchmark_agent import BenchmarkAgent
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools import ExtractPageContentTool, FinalAnswerTool, ReasoningTool, WebSearchTool


class TestBenchmarkAgentInitialization:
    """Tests for BenchmarkAgent initialization and setup."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_initialization_basic(self, mock_openai, mock_get_config):
        """Test basic initialization with required parameters."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Benchmark test task")

        assert agent.task == "Benchmark test task"
        assert agent.name == "benchmark_agent"
        # Default values from parent classes
        assert agent.max_iterations == 10
        assert agent.max_clarifications == 3
        assert agent.max_searches == 4

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_initialization_with_custom_parameters(self, mock_openai, mock_get_config):
        """Test initialization with custom parameters."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Custom benchmark task", max_clarifications=5, max_iterations=15, max_searches=8)

        assert agent.task == "Custom benchmark task"
        assert agent.max_clarifications == 5
        assert agent.max_iterations == 15
        assert agent.max_searches == 8

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_toolkit_initialization(self, mock_openai, mock_get_config):
        """Test that toolkit is properly initialized with benchmark-specific
        tools."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Test toolkit")

        # Verify specific benchmark tools are present
        expected_tools = [ReasoningTool, WebSearchTool, ExtractPageContentTool, FinalAnswerTool]

        assert len(agent.toolkit) == len(expected_tools)
        for tool in expected_tools:
            assert tool in agent.toolkit

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_inheritance_from_sgr_tool_calling_agent(self, mock_openai, mock_get_config):
        """Test that BenchmarkAgent properly inherits from
        SGRToolCallingAgent."""
        from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent

        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Inheritance test")

        assert isinstance(agent, SGRToolCallingAgent)
        # Should inherit tool_choice property
        assert hasattr(agent, "tool_choice")


class TestBenchmarkAgentToolPreparation:
    """Tests for BenchmarkAgent tool preparation logic."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_tools_normal_conditions(self, mock_openai, mock_get_config):
        """Test tool preparation under normal conditions."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Tool preparation test")
        agent._context = ResearchContext()

        # Normal conditions - no limits reached
        tools = await agent._prepare_tools()

        # Should have all tools available
        assert len(tools) == 4  # All 4 benchmark tools

        # Verify tool names are present
        # pydantic_function_tool returns dict, not object with .function attribute
        tool_names = [tool["function"]["name"] for tool in tools]
        expected_names = ["reasoningtool", "websearchtool", "extractpagecontenttool", "finalanswertool"]

        for expected_name in expected_names:
            assert expected_name in tool_names

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_tools_max_iterations_reached(self, mock_openai, mock_get_config):
        """Test tool preparation when max iterations are reached."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Max iterations test", max_iterations=5)
        agent._context = ResearchContext()
        agent._context.iteration = 5  # Reached max iterations

        tools = await agent._prepare_tools()

        # Should only have ReasoningTool and FinalAnswerTool
        assert len(tools) == 2

        tool_names = [tool["function"]["name"] for tool in tools]
        assert "reasoningtool" in tool_names
        assert "finalanswertool" in tool_names
        assert "websearchtool" not in tool_names
        assert "extractpagecontenttool" not in tool_names

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_tools_max_searches_reached(self, mock_openai, mock_get_config):
        """Test tool preparation when max searches are reached."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Max searches test", max_searches=3)
        agent._context = ResearchContext()
        agent._context.searches_used = 3  # Reached max searches

        tools = await agent._prepare_tools()

        # Should have all tools except WebSearchTool
        assert len(tools) == 3

        tool_names = [tool["function"]["name"] for tool in tools]
        assert "reasoningtool" in tool_names
        assert "extractpagecontenttool" in tool_names
        assert "finalanswertool" in tool_names
        assert "websearchtool" not in tool_names

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_prepare_tools_both_limits_reached(self, mock_openai, mock_get_config):
        """Test tool preparation when both max iterations and searches are
        reached."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Both limits test", max_iterations=5, max_searches=3)
        agent._context = ResearchContext()
        agent._context.iteration = 5  # Reached max iterations
        agent._context.searches_used = 3  # Reached max searches

        tools = await agent._prepare_tools()

        # Max iterations takes precedence - should only have ReasoningTool and FinalAnswerTool
        assert len(tools) == 2

        tool_names = [tool["function"]["name"] for tool in tools]
        assert "reasoningtool" in tool_names
        assert "finalanswertool" in tool_names


class TestBenchmarkAgentExecution:
    """Tests for BenchmarkAgent execution flow."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_execute_calls_parent_execute(self, mock_openai, mock_get_config):
        """Test that execute method calls parent class execute."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="Execute test")

        # Mock the parent execute method
        with patch.object(agent.__class__.__bases__[0], "execute", new_callable=AsyncMock) as mock_parent_execute:
            await agent.execute()

            # Verify parent execute was called
            mock_parent_execute.assert_called_once()

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_config_integration(self, mock_openai):
        """Test that BenchmarkAgent properly integrates with configuration
        system."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent = BenchmarkAgent(task="Config integration test")

        assert agent.task == "Config integration test"
        assert agent.name == "benchmark_agent"

        # Verify OpenAI client was initialized
        assert mock_openai.called


class TestBenchmarkAgentIntegration:
    """Integration tests for BenchmarkAgent with other components."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_in_agent_model_mapping(self, mock_openai, mock_get_config):
        """Test that BenchmarkAgent can be used in agent factory pattern."""
        from sgr_deep_research.api.models import AgentModel

        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # BenchmarkAgent is not in the standard mapping, but test the pattern works
        test_mapping = {AgentModel.SGR_TOOL_CALLING_AGENT: BenchmarkAgent}

        agent_model = AgentModel.SGR_TOOL_CALLING_AGENT
        agent_class = test_mapping[agent_model]
        agent = agent_class(task="Integration test")

        assert isinstance(agent, BenchmarkAgent)
        assert agent.task == "Integration test"

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_unique_properties(self, mock_openai, mock_get_config):
        """Test that BenchmarkAgent has unique properties compared to base
        SGRToolCallingAgent."""
        from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent

        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        benchmark_agent = BenchmarkAgent(task="Benchmark task")
        sgr_agent = SGRToolCallingAgent(task="Regular task")

        # Different names
        assert benchmark_agent.name == "benchmark_agent"
        assert sgr_agent.name == "sgr_tool_calling_agent"

        # Different toolkit sizes (BenchmarkAgent has limited tools)
        assert len(benchmark_agent.toolkit) < len(sgr_agent.toolkit)

        # BenchmarkAgent should have exactly 4 tools
        assert len(benchmark_agent.toolkit) == 4


class TestBenchmarkAgentEdgeCases:
    """Tests for edge cases and error conditions in BenchmarkAgent."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_empty_task(self, mock_openai, mock_get_config):
        """Test BenchmarkAgent with empty task."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        agent = BenchmarkAgent(task="")

        assert agent.task == ""
        assert agent.name == "benchmark_agent"
        assert len(agent.toolkit) == 4

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_extreme_limits(self, mock_openai, mock_get_config):
        """Test BenchmarkAgent with extreme limit values."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Test with very high limits
        agent = BenchmarkAgent(
            task="Extreme limits test", max_iterations=1000, max_searches=500, max_clarifications=100
        )

        assert agent.max_iterations == 1000
        assert agent.max_searches == 500
        assert agent.max_clarifications == 100

        # Test with zero/minimal limits
        agent_minimal = BenchmarkAgent(
            task="Minimal limits test", max_iterations=1, max_searches=0, max_clarifications=0
        )

        assert agent_minimal.max_iterations == 1
        assert agent_minimal.max_searches == 0
        assert agent_minimal.max_clarifications == 0

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_benchmark_agent_with_additional_args(self, mock_openai, mock_get_config):
        """Test BenchmarkAgent with positional argument."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Test with positional argument - task is required parameter
        agent = BenchmarkAgent(task="Test task", max_iterations=5)

        assert agent.task == "Test task"
        assert agent.max_iterations == 5
