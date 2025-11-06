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

        with open(yaml_path, encoding="utf-8") as f:
            if cls._instance is None:
                cls._instance = cls(**yaml.safe_load(f))
            else:
                cls._initialized = False
                cls._instance = cls(**yaml.safe_load(f), agents=cls._instance.agents)
            return cls._instance

    @classmethod
    def definitions_from_yaml(cls, agents_yaml_path: str) -> Self:
        yaml_path = Path(agents_yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, encoding="utf-8") as f:
            cls._instance.agents = Definitions(**yaml.safe_load(f)).agents
            return cls._instance
