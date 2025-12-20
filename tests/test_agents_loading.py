"""
Tests for agents loading from config.yaml and agents.yaml files.

This module tests the loading order and override behavior:
1. If agents.yaml exists, load agents from it
2. If agents section exists in config.yaml, load agents from it
3. If both exist, load agents.yaml first, then override with config.yaml
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from sgr_agent_core.agent_config import GlobalConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def reset_global_config():
    """Reset GlobalConfig singleton before and after each test."""
    # Save original state
    original_instance = GlobalConfig._instance
    original_initialized = GlobalConfig._initialized

    # Reset before test
    GlobalConfig._instance = None
    GlobalConfig._initialized = False

    yield

    # Reset after test
    GlobalConfig._instance = original_instance
    GlobalConfig._initialized = original_initialized


class TestAgentsLoadingFromAgentsYaml:
    """Test loading agents from agents.yaml file."""

    def test_load_agents_from_agents_yaml_only(self, temp_dir, reset_global_config):
        """Test that agents are loaded from agents.yaml when it exists."""
        # Create agents.yaml
        agents_yaml = temp_dir / "agents.yaml"
        agents_data = {
            "agents": {
                "test_agent_from_agents_yaml": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
                    "tools": ["FinalAnswerTool"],
                }
            }
        }
        agents_yaml.write_text(yaml.dump(agents_data), encoding="utf-8")

        # Create minimal config.yaml without agents section
        config_yaml = temp_dir / "config.yaml"
        config_data = {
            "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
        }
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load config: simulate __main__.py logic
        config_data_loaded = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data_loaded.pop("agents", {})
        
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data_loaded)
        
        # Load agents.yaml
        config.definitions_from_yaml(str(agents_yaml))
        
        # Apply agents from config.yaml (empty in this case)
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Verify agent was loaded from agents.yaml
        assert "test_agent_from_agents_yaml" in config.agents
        assert config.agents["test_agent_from_agents_yaml"].name == "test_agent_from_agents_yaml"

    def test_load_agents_from_agents_yaml_with_config_override(self, temp_dir, reset_global_config):
        """Test that agents.yaml is loaded first, then config.yaml overrides."""
        # Create agents.yaml with initial agent
        agents_yaml = temp_dir / "agents.yaml"
        agents_data = {
            "agents": {
                "test_agent": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini", "temperature": 0.5},
                    "tools": ["FinalAnswerTool"],
                }
            }
        }
        agents_yaml.write_text(yaml.dump(agents_data), encoding="utf-8")

        # Create config.yaml with agents section that overrides temperature
        config_yaml = temp_dir / "config.yaml"
        config_data = {
            "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
            "agents": {
                "test_agent": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini", "temperature": 0.8},
                    "tools": ["FinalAnswerTool"],
                }
            },
        }
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load base config without agents
        config_data = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data.pop("agents", {})
        
        # Create config with base settings
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data)
        
        # Load agents.yaml first
        config.definitions_from_yaml(str(agents_yaml))
        
        # Then apply agents from config.yaml for override
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Verify agent exists and has overridden temperature from config.yaml
        assert "test_agent" in config.agents
        # config.yaml should override agents.yaml, so temperature should be 0.8
        assert config.agents["test_agent"].llm.temperature == 0.8  # From config.yaml (loaded last, overrides)


class TestAgentsLoadingFromConfigYaml:
    """Test loading agents from config.yaml file."""

    def test_load_agents_from_config_yaml_only(self, temp_dir, reset_global_config):
        """Test that agents are loaded from config.yaml when agents.yaml doesn't exist."""
        # Create config.yaml with agents section
        config_yaml = temp_dir / "config.yaml"
        config_data = {
            "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
            "agents": {
                "test_agent_from_config": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
                    "tools": ["FinalAnswerTool"],
                }
            },
        }
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load config: simulate __main__.py logic (no agents.yaml)
        config_data_loaded = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data_loaded.pop("agents", {})
        
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data_loaded)
        
        # No agents.yaml, so apply agents from config.yaml
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Verify agent was loaded from config.yaml
        assert "test_agent_from_config" in config.agents
        assert config.agents["test_agent_from_config"].name == "test_agent_from_config"


class TestAgentsLoadingOrder:
    """Test the correct loading order: agents.yaml first, then config.yaml override."""

    def test_agents_yaml_first_then_config_override(self, temp_dir, reset_global_config):
        """Test that agents.yaml is loaded first, then config.yaml overrides settings."""
        # Create agents.yaml with agent having temperature 0.5
        agents_yaml = temp_dir / "agents.yaml"
        agents_data = {
            "agents": {
                "overridden_agent": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini", "temperature": 0.5},
                    "tools": ["FinalAnswerTool"],
                }
            }
        }
        agents_yaml.write_text(yaml.dump(agents_data), encoding="utf-8")

        # Create config.yaml with same agent but different temperature
        config_yaml = temp_dir / "config.yaml"
        config_data = {
            "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
            "agents": {
                "overridden_agent": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini", "temperature": 0.8},
                    "tools": ["FinalAnswerTool"],
                }
            },
        }
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load: agents.yaml first, then config.yaml for override
        # Simulate the loading order from __main__.py
        # Load base config without agents
        config_data = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data.pop("agents", {})
        
        # Create config with base settings
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data)
        
        # Load agents.yaml first
        config.definitions_from_yaml(str(agents_yaml))
        
        # Then apply agents from config.yaml for override
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Verify: config.yaml should override agents.yaml
        assert "overridden_agent" in config.agents
        assert config.agents["overridden_agent"].llm.temperature == 0.8  # From config.yaml (overrides agents.yaml)

    def test_both_files_different_agents(self, temp_dir, reset_global_config):
        """Test loading different agents from both files."""
        # Create agents.yaml with agent1
        agents_yaml = temp_dir / "agents.yaml"
        agents_data = {
            "agents": {
                "agent_from_agents_yaml": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
                    "tools": ["FinalAnswerTool"],
                }
            }
        }
        agents_yaml.write_text(yaml.dump(agents_data), encoding="utf-8")

        # Create config.yaml with agent2
        config_yaml = temp_dir / "config.yaml"
        config_data = {
            "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
            "agents": {
                "agent_from_config": {
                    "base_class": "sgr_agent_core.agents.sgr_agent.SGRAgent",
                    "llm": {"api_key": "test-key", "model": "gpt-4o-mini"},
                    "tools": ["FinalAnswerTool"],
                }
            },
        }
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load both: simulate __main__.py logic
        config_data_loaded = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data_loaded.pop("agents", {})
        
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data_loaded)
        
        # Load agents.yaml first
        config.definitions_from_yaml(str(agents_yaml))
        
        # Then apply agents from config.yaml
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Verify both agents exist
        assert "agent_from_agents_yaml" in config.agents
        assert "agent_from_config" in config.agents

    def test_agents_yaml_missing_agents_key(self, temp_dir, reset_global_config):
        """Test that missing 'agents' key in agents.yaml raises ValueError."""
        # Create agents.yaml without 'agents' key
        agents_yaml = temp_dir / "agents.yaml"
        agents_data = {"some_other_key": "value"}
        agents_yaml.write_text(yaml.dump(agents_data), encoding="utf-8")

        # Create config.yaml
        config_yaml = temp_dir / "config.yaml"
        config_data = {"llm": {"api_key": "test-key", "model": "gpt-4o-mini"}}
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load config: simulate __main__.py logic
        config_data_loaded = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data_loaded.pop("agents", {})
        
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data_loaded)

        # Loading agents.yaml without 'agents' key should raise ValueError
        with pytest.raises(ValueError, match="must contain 'agents' key"):
            config.definitions_from_yaml(str(agents_yaml))

    def test_config_yaml_without_agents_section(self, temp_dir, reset_global_config):
        """Test that config.yaml can be loaded without agents section."""
        # Create config.yaml without agents section
        config_yaml = temp_dir / "config.yaml"
        config_data = {"llm": {"api_key": "test-key", "model": "gpt-4o-mini"}}
        config_yaml.write_text(yaml.dump(config_data), encoding="utf-8")

        # Load config: simulate __main__.py logic
        config_data_loaded = yaml.safe_load(Path(config_yaml).read_text(encoding="utf-8"))
        main_config_agents = config_data_loaded.pop("agents", {})
        
        GlobalConfig._instance = None
        GlobalConfig._initialized = False
        config = GlobalConfig(**config_data_loaded)
        
        # Apply agents from config.yaml (empty in this case)
        if main_config_agents:
            config._definitions_from_dict({"agents": main_config_agents})

        # Agents dict should be empty or contain defaults
        assert isinstance(config.agents, dict)

