"""OpenAI-compatible models for API endpoints."""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from sgr_deep_research.core.agents import (
    SGRAutoToolCallingResearchAgent,
    SGRResearchAgent,
    SGRSOToolCallingResearchAgent,
    SGRToolCallingResearchAgent,
    ToolCallingResearchAgent,
)


class AgentModel(str, Enum):
    """Available agent models for chat completion."""

    SGR_AGENT = SGRResearchAgent.name
    SGR_TOOLS_AGENT = SGRToolCallingResearchAgent.name
    SGR_AUTO_TOOLS_AGENT = SGRAutoToolCallingResearchAgent.name
    SGR_SO_TOOLS_AGENT = SGRSOToolCallingResearchAgent.name
    TOOLS_AGENT = ToolCallingResearchAgent.name


# Mapping of agent types to their classes
AGENT_MODEL_MAPPING = {
    AgentModel.SGR_AGENT: SGRResearchAgent,
    AgentModel.SGR_TOOLS_AGENT: SGRToolCallingResearchAgent,
    AgentModel.SGR_AUTO_TOOLS_AGENT: SGRAutoToolCallingResearchAgent,
    AgentModel.SGR_SO_TOOLS_AGENT: SGRSOToolCallingResearchAgent,
    AgentModel.TOOLS_AGENT: ToolCallingResearchAgent,
}


class ChatMessage(BaseModel):
    """Chat message."""

    role: Literal["system", "user", "assistant", "tool"] = Field(default="user", description="Sender role")
    content: str = Field(description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request for creating chat completion."""

    model: str | None = Field(
        default=AgentModel.SGR_AGENT,
        description="Agent type or existing agent identifier",
        examples=[AgentModel.SGR_AGENT.value],
    )
    messages: List[ChatMessage] = Field(description="List of messages")
    stream: bool = Field(default=True, description="Enable streaming mode")
    max_tokens: int | None = Field(default=1500, description="Maximum number of tokens")
    temperature: float | None = Field(default=0, description="Generation temperature")


class ChatCompletionChoice(BaseModel):
    """Choice in chat completion response."""

    index: int = Field(description="Choice index")
    message: ChatMessage = Field(description="Response message")
    finish_reason: str | None = Field(description="Finish reason")


class ChatCompletionResponse(BaseModel):
    """Chat completion response (non-streaming)."""

    id: str = Field(description="Response ID")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(description="Creation time")
    model: str = Field(description="Model used")
    choices: List[ChatCompletionChoice] = Field(description="List of choices")
    usage: Dict[str, int] | None = Field(default=None, description="Usage information")


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: str = Field(default="SGR Deep Research API", description="Service name")


class AgentStateResponse(BaseModel):
    agent_id: str = Field(description="Agent ID")
    task: str = Field(description="Agent task")
    state: str = Field(description="Current agent state")
    iteration: int = Field(description="Current iteration number")
    searches_used: int = Field(description="Number of searches performed")
    clarifications_used: int = Field(description="Number of clarifications requested")
    sources_count: int = Field(description="Number of sources found")
    current_step_reasoning: Dict[str, Any] | None = Field(default=None, description="Current agent step")


class AgentListItem(BaseModel):
    agent_id: str = Field(description="Agent ID")
    task: str = Field(description="Agent task")
    state: str = Field(description="Current agent state")


class AgentListResponse(BaseModel):
    agents: List[AgentListItem] = Field(description="List of agents")
    total: int = Field(description="Total number of agents")


class ClarificationRequest(BaseModel):
    """Simple request for providing clarifications to an agent."""

    clarifications: str = Field(description="Clarification text to provide to the agent")
