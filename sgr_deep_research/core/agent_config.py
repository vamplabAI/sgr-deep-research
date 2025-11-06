from pathlib import Path
from typing import ClassVar, Self

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from sgr_deep_research.core.agent_definition import AgentConfig, Definitions


class GlobalConfig(BaseSettings, AgentConfig, Definitions):
    _instance: ClassVar[Self | None] = None
    _initialized: ClassVar[bool] = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        if self._initialized:
            return
        super().__init__(*args, **kwargs)
        self.__class__._initialized = True

    model_config = SettingsConfigDict(
        env_prefix="SGR__",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> Self:
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        config_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if cls._instance is None:
            cls._instance = cls(**config_data)
        else:
            cls._initialized = False
            cls._instance = cls(**config_data, agents=cls._instance.agents)
        return cls._instance

    @classmethod
    def definitions_from_yaml(cls, agents_yaml_path: str) -> Self:
        agents_yaml_path = Path(agents_yaml_path)
        if not agents_yaml_path.exists():
            raise FileNotFoundError(f"Agents definitions file not found: {agents_yaml_path}")
        cls._instance.agents = Definitions(**yaml.safe_load(agents_yaml_path.read_text(encoding="utf-8"))).agents
        return cls._instance
