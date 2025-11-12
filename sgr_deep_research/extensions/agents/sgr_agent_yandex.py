import httpx

from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.extensions.utils.yandex_utils import extractCloudFolder
from sgr_deep_research.settings import get_config

config = get_config()

class SGRAgentYandex(SGRAgent):
    """Agent for deep research tasks using SGR framework.
    Takes into account the specifics of YandexGPT API"""

    name: str = "sgr_agent_yandex"

    def create_client_kwargs(self, config):
        yandex_cloud_folder = extractCloudFolder(config.openai.model)
        client_kwargs = {"base_url": config.openai.base_url, "api_key": config.openai.api_key,
                         "project":yandex_cloud_folder}
        if config.openai.proxy.strip():
            client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.openai.proxy)
        return client_kwargs