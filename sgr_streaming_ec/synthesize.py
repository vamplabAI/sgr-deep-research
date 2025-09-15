from __future__ import annotations
from .state import AgentState

def report_from_state(state: AgentState) -> str:
    return "Findings:\n" + "\n".join(
        f"- {f.text}{' ('+str(f.source)+')' if f.source else ''}" for f in state.facts
    )
