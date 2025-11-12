"""Tests for agent factory and configuration-based agent creation.

This module contains tests for the new architecture of creating agents
from configuration, including API model mapping and dynamic agent
instantiation.
"""

from unittest.mock import Mock, patch

import pytest

from sgr_deep_research.api.models import (
    AGENT_MODEL_MAPPING,
    AgentModel,
)
from sgr_deep_research.core.agents import (
    BaseAgent,
    SGRAgent,
    SGRAutoToolCallingAgent,
    SGRSOToolCallingAgent,
    SGRToolCallingAgent,
    ToolCallingAgent,
)


class TestAgentModelEnum:
    """Tests for AgentModel enum and its values."""

    def test_agent_model_enum_values(self):
        """Test that AgentModel enum has correct string values."""
        assert AgentModel.SGR_AGENT.value == "sgr_agent"
        assert AgentModel.SGR_TOOL_CALLING_AGENT.value == "sgr_tool_calling_agent"
        assert AgentModel.SGR_AUTO_TOOL_CALLING_AGENT.value == "sgr_auto_tool_calling_agent"
        assert AgentModel.SGR_SO_TOOL_CALLING_AGENT.value == "sgr_so_tool_calling_agent"
        assert AgentModel.TOOL_CALLING_AGENT.value == "tool_calling_agent"

    def test_agent_model_enum_count(self):
        """Test that AgentModel enum has exactly the expected number of
        models."""
        expected_count = 5
        assert len(AgentModel) == expected_count

    def test_agent_model_enum_iteration(self):
        """Test that all agent models can be iterated."""
        model_values = [model.value for model in AgentModel]
        expected_values = [
            "sgr_agent",
            "sgr_tool_calling_agent",
            "sgr_auto_tool_calling_agent",
            "sgr_so_tool_calling_agent",
            "tool_calling_agent",
        ]
        assert set(model_values) == set(expected_values)


class TestAgentModelMapping:
    """Tests for AGENT_MODEL_MAPPING configuration."""

    def test_agent_model_mapping_keys(self):
        """Test that mapping contains all AgentModel enum values."""
        mapping_keys = set(AGENT_MODEL_MAPPING.keys())
        enum_values = set(AgentModel)
        assert mapping_keys == enum_values

    def test_agent_model_mapping_values(self):
        """Test that mapping values are correct agent classes."""
        assert AGENT_MODEL_MAPPING[AgentModel.SGR_AGENT] == SGRAgent
        assert AGENT_MODEL_MAPPING[AgentModel.SGR_TOOL_CALLING_AGENT] == SGRToolCallingAgent
        assert AGENT_MODEL_MAPPING[AgentModel.SGR_AUTO_TOOL_CALLING_AGENT] == SGRAutoToolCallingAgent
        assert AGENT_MODEL_MAPPING[AgentModel.SGR_SO_TOOL_CALLING_AGENT] == SGRSOToolCallingAgent
        assert AGENT_MODEL_MAPPING[AgentModel.TOOL_CALLING_AGENT] == ToolCallingAgent

    def test_agent_model_mapping_inheritance(self):
        """Test that all mapped classes inherit from BaseAgent."""
        for agent_class in AGENT_MODEL_MAPPING.values():
            assert issubclass(agent_class, BaseAgent)

    def test_agent_model_mapping_completeness(self):
        """Test that mapping covers all enum values without extras."""
        assert len(AGENT_MODEL_MAPPING) == len(AgentModel)


class TestAgentFactory:
    """Tests for dynamic agent creation from configuration."""

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_create_agent_from_model_string(self, mock_openai, mock_get_config):
        """Test creating agent from model string."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Test SGRAgent creation
        model_name = "sgr_agent"
        agent_model = AgentModel(model_name)
        agent_class = AGENT_MODEL_MAPPING[agent_model]
        agent = agent_class(task="Test task")

        assert isinstance(agent, SGRAgent)
        assert agent.task == "Test task"
        assert agent.name == "sgr_agent"

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_create_all_agent_types(self, mock_openai, mock_get_config):
        """Test creating all available agent types."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        task = "Universal test task"

        for agent_model in AgentModel:
            agent_class = AGENT_MODEL_MAPPING[agent_model]
            agent = agent_class(task=task)

            assert isinstance(agent, BaseAgent)
            assert agent.task == task
            assert agent.name == agent_model.value

    def test_invalid_agent_model_string(self):
        """Test that invalid model string raises ValueError."""
        with pytest.raises(ValueError):
            AgentModel("invalid_agent_model")

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_agent_factory_with_custom_params(self, mock_openai, mock_get_config):
        """Test creating agents with custom initialization parameters."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Test with custom parameters that are common to all agents
        agent_model = AgentModel.SGR_TOOL_CALLING_AGENT
        agent_class = AGENT_MODEL_MAPPING[agent_model]

        agent = agent_class(task="Custom task", max_clarifications=5, max_iterations=15, max_searches=10)

        assert agent.task == "Custom task"
        assert agent.max_clarifications == 5
        assert agent.max_iterations == 15
        assert agent.max_searches == 10

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_agent_creation_preserves_agent_properties(self, mock_openai, mock_get_config):
        """Test that agent creation preserves specific agent properties."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Test SGRToolCallingAgent specific properties
        agent_model = AgentModel.SGR_TOOL_CALLING_AGENT
        agent_class = AGENT_MODEL_MAPPING[agent_model]
        agent = agent_class(task="Test")

        # Should have tool_choice property for tool calling agents
        if hasattr(agent, "tool_choice"):
            assert agent.tool_choice == "required"


class TestConfigurationBasedAgentCreation:
    """Tests for creating agents based on configuration patterns."""

    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_agent_config_integration(self, mock_openai):
        """Test that agents properly integrate configuration from settings."""
        # Agents use real config from config.yaml
        # Just verify agent can be created successfully
        agent_class = AGENT_MODEL_MAPPING[AgentModel.SGR_AGENT]
        agent = agent_class(task="Test config integration")

        # Verify agent was created successfully
        assert agent.task == "Test config integration"
        assert agent.name == "sgr_agent"

        # Verify OpenAI client was initialized (any params)
        assert mock_openai.called

    def test_agent_model_name_consistency(self):
        """Test that agent model names are consistent with class names."""
        for agent_model, agent_class in AGENT_MODEL_MAPPING.items():
            # Create a temporary instance to check name consistency
            # We expect the class name attribute to match the enum value
            assert agent_class.name == agent_model.value

    @patch("sgr_deep_research.core.base_agent.get_config")
    @patch("sgr_deep_research.core.base_agent.AsyncOpenAI")
    def test_multiple_agent_creation_independence(self, mock_openai, mock_get_config):
        """Test that multiple agents can be created independently."""
        mock_config = Mock()
        mock_config.openai.base_url = "https://api.openai.com/v1"
        mock_config.openai.api_key = "test-key"
        mock_config.openai.proxy = ""
        mock_get_config.return_value = mock_config

        # Create multiple different agent types
        agents = []
        tasks = ["Task 1", "Task 2", "Task 3"]

        for i, agent_model in enumerate(list(AgentModel)[:3]):  # Test first 3 types
            agent_class = AGENT_MODEL_MAPPING[agent_model]
            agent = agent_class(task=tasks[i])
            agents.append(agent)

        # Verify all agents are independent
        for i, agent in enumerate(agents):
            assert agent.task == tasks[i]
            assert agent.id != agents[(i + 1) % len(agents)].id  # Different IDs

        # Verify different types
        assert (type(agents[0]) is not type(agents[1])) if len(agents) > 1 else True


class TestAgentCreationEdgeCases:
    """Tests for edge cases in agent creation."""

    def test_empty_task_creation(self):
        """Test creating agent with empty task."""
        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "test-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            agent_class = AGENT_MODEL_MAPPING[AgentModel.SGR_AGENT]
            agent = agent_class(task="")

            assert agent.task == ""
            assert agent.name == "sgr_agent"

    def test_agent_creation_with_toolkit(self):
        """Test creating agent with custom toolkit."""
        from sgr_deep_research.core.tools import BaseTool

        class CustomTool(BaseTool):
            tool_name = "custom_tool"
            description = "A custom test tool"

        with (
            patch("sgr_deep_research.core.base_agent.get_config") as mock_get_config,
            patch("sgr_deep_research.core.base_agent.AsyncOpenAI"),
        ):
            mock_config = Mock()
            mock_config.openai.base_url = "https://api.openai.com/v1"
            mock_config.openai.api_key = "test-key"
            mock_config.openai.proxy = ""
            mock_get_config.return_value = mock_config

            agent_class = AGENT_MODEL_MAPPING[AgentModel.SGR_AGENT]
            agent = agent_class(task="Test", toolkit=[CustomTool])

            # Verify custom tool was added to toolkit
            assert CustomTool in agent.toolkit
