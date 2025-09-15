from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict

class Fact(BaseModel):
    text: str
    source: Optional[HttpUrl] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)

class AgentState(BaseModel):
    """Trusted, compact state carried between steps.
    Avoids conditioning on sprawling scratchpads."""
    facts: List[Fact] = []
    goals: List[str] = []
    plan: List[str] = []            # next bounded actions only
    constraints: Dict = {}          # schema rules, must/forbidden lists
    step: int = 0

    def brief_context(self) -> str:
        facts_str = "\n".join(
            f"- {f.text} [conf={f.confidence:.2f}{' src='+str(f.source) if f.source else ''}]"
            for f in self.facts[:24]
        )
        goals_str = "\n".join(f"- {g}" for g in self.goals[:10])
        return f"FACTS:\n{facts_str}\n\nGOALS:\n{goals_str}\n"

def start_state(user_goal: str, constraints: Dict | None = None) -> AgentState:
    return AgentState(goals=[user_goal], constraints=constraints or {})
