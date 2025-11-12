from sgr_deep_research.settings import get_config
from enum import Enum

def initialize_extensions():
    """Инициализировать расширения (вызывать после загрузки конфига)"""
    config = get_config()
    if not config.extensions:
        return

    import sgr_deep_research.api.models as api_models

    members = {member.name: member.value for member in api_models.AgentModel}
    mapping = api_models.AGENT_MODEL_MAPPING.copy()

    added_count = 0
    for agent_config in config.extensions.agent_models:
        try:
            agent_class = agent_config.agent_class
            enum_name = agent_config.enum_name
            enum_value = agent_config.name
            members[enum_name] = enum_value
            mapping[enum_value] = agent_class

            added_count += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")

    api_models.AgentModel = Enum('AgentModel', members, type=str)
    api_models.AGENT_MODEL_MAPPING = mapping
