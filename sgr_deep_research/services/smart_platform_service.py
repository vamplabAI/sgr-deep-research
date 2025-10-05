"""
Smart Platform Service for KNN search in Confluence.

This service provides access to Smart Platform's agent-based search capabilities
for corporate knowledge base through KNN (K-Nearest Neighbors) search.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from sgr_deep_research.settings import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SmartPlatformSearchResult(BaseModel):
    """Result from Smart Platform KNN search."""
    
    response_id: str
    agent_id: str
    response: str
    send_at: str
    sources: List[Dict[str, Any]]


class SmartPlatformService:
    """Service for interacting with Smart Platform API for KNN search."""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.smart_platform.base_url
        self.api_key = self.config.smart_platform.api_key
        self.default_chat_id = self.config.smart_platform.chat_id
        self.default_agent_id = self.config.smart_platform.agent_id
        self.timeout = self.config.smart_platform.timeout
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Basic {self.api_key}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
        )
    
    async def search(
        self,
        query: str,
        agent_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        is_return_debug: bool = False
    ) -> SmartPlatformSearchResult:
        """
        Perform KNN search through Smart Platform.
        
        Args:
            query: Search query string
            agent_id: Smart Platform agent ID (uses default from config if not provided)
            chat_id: Chat ID for conversation context (uses default from config if not provided)
            is_return_debug: Whether to return debug information
            
        Returns:
            SmartPlatformSearchResult with response and sources
        """
        # Use defaults from config if not provided
        if not agent_id:
            agent_id = self.default_agent_id
        if not chat_id:
            chat_id = self.default_chat_id
        
        # Build payload - chat_id is REQUIRED by API
        payload = {
            "chat_id": chat_id,
            "user_query": query,
            "is_return_debug": is_return_debug
        }
        
        endpoint = f"/v3/agents/{agent_id}/query"
        full_url = f"{self.base_url}{endpoint}"
        
        logger.info(
            f"🔍 Smart Platform KNN search\n"
            f"   Query: '{query}'\n"
            f"   Agent ID: {agent_id}\n"
            f"   Chat ID: {payload.get('chat_id', 'not provided - will be created')}\n"
            f"   URL: {full_url}\n"
            f"   Payload: {payload}"
        )
        
        try:
            # Use streaming to handle SSE-like response
            async with self._client.stream(
                "POST",
                endpoint,
                json=payload
            ) as response:
                status_code = response.status_code
                logger.info(f"📡 Smart Platform response status: {status_code}")
                
                if status_code != 200:
                    # Read error response body
                    error_body = await response.aread()
                    logger.error(
                        f"❌ Smart Platform API returned {status_code}\n"
                        f"   URL: {full_url}\n"
                        f"   Agent ID: {agent_id}\n"
                        f"   Response body: {error_body.decode('utf-8', errors='replace')[:500]}"
                    )
                
                response.raise_for_status()
                
                # Collect all chunks
                chunks = []
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                
                logger.debug(f"📦 Received {len(chunks)} chunks from Smart Platform")
                
                # Parse the streaming response
                result_data = self._parse_streaming_response('\n'.join(chunks))
            
            logger.info(f"✅ Smart Platform search successful, {len(result_data.get('sources', []))} sources found")
            return SmartPlatformSearchResult(**result_data)
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Smart Platform HTTP Status Error\n"
                f"   Status Code: {e.response.status_code}\n"
                f"   URL: {full_url}\n"
                f"   Agent ID: {agent_id}\n"
                f"   Request: {e.request.method} {e.request.url}\n"
                f"   Response: {e.response.text[:500]}"
            )
            raise Exception(f"Smart Platform returned {e.response.status_code}: {e.response.text[:200]}")
        except httpx.HTTPError as e:
            logger.error(
                f"❌ Smart Platform HTTP Error\n"
                f"   Error: {str(e)}\n"
                f"   URL: {full_url}\n"
                f"   Agent ID: {agent_id}"
            )
            raise Exception(f"Smart Platform HTTP error: {e}")
        except Exception as e:
            logger.error(
                f"❌ Smart Platform search error\n"
                f"   Error: {str(e)}\n"
                f"   URL: {full_url}\n"
                f"   Agent ID: {agent_id}"
            )
            raise Exception(f"Smart Platform search failed: {e}")
    
    def _parse_streaming_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse streaming response from Smart Platform.
        
        The response comes as multiple JSON lines (SSE format), we need to find the final result
        with stage_name='Save Response' which contains the actual response data.
        """
        import json
        
        lines = response_text.strip().split('\n')
        logger.debug(f"📋 Parsing {len(lines)} lines from streaming response")
        
        # Find the final result line with stage_name='Save Response'
        save_response_data = None
        parsed_stages = []
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                stage_name = data.get('stage_name', 'unknown')
                parsed_stages.append(stage_name)
                
                # Look for the Save Response stage which contains the final result
                if stage_name == 'Save Response' and 'result' in data:
                    save_response_data = data
                    logger.debug(f"✅ Found 'Save Response' stage")
                    break
            except json.JSONDecodeError as e:
                logger.debug(f"Could not parse line: {line[:100]} - {e}")
                continue
        
        logger.debug(f"📊 Parsed stages: {parsed_stages}")
        
        if not save_response_data:
            logger.error(
                f"❌ Could not find 'Save Response' stage\n"
                f"   Parsed stages: {parsed_stages}\n"
                f"   Total lines: {len(lines)}\n"
                f"   First line sample: {lines[0][:200] if lines else 'no lines'}"
            )
            raise Exception("Could not find 'Save Response' stage in Smart Platform response")
        
        # The actual result is in the 'result' field as a JSON string
        result_json_str = save_response_data.get('result', '')
        
        if not result_json_str:
            logger.error("❌ 'result' field is empty in Save Response stage")
            raise Exception("'result' field is empty in Save Response stage")
        
        try:
            # Parse the nested JSON string
            result_data = json.loads(result_json_str)
            
            # Validate required fields
            if 'response' not in result_data:
                logger.error(f"❌ Missing 'response' field. Available fields: {list(result_data.keys())}")
                raise Exception("Missing 'response' field in result data")
            
            # Ensure sources is a list
            if 'sources' not in result_data:
                result_data['sources'] = []
                logger.debug("⚠️ No sources field, setting empty list")
            
            logger.debug(f"✅ Successfully parsed result with {len(result_data.get('sources', []))} sources")
            return result_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse result JSON: {result_json_str[:200]} - {e}")
            raise Exception(f"Could not parse Smart Platform result JSON: {e}")
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
