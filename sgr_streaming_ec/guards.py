from __future__ import annotations
from .state import AgentState

def coverage_gain(prev: AgentState, cand: AgentState) -> float:
    prev_texts = [f.text for f in prev.facts]
    new = [f for f in cand.facts if f.text not in prev_texts]
    return len(new) / max(1, len(cand.facts))

def non_contradiction(prev: AgentState, cand: AgentState) -> float:
    # Placeholder: add stricter logic if needed
    return 1.0

def schema_valid(cand: AgentState) -> float:
    try:
        AgentState.model_validate(cand.model_dump())
        return 1.0
    except Exception:
        return 0.0

def novelty(prev: AgentState, cand: AgentState) -> float:
    return 1.0 if cand.plan and cand.plan != prev.plan else 0.3

def score_state(prev: AgentState, cand: AgentState) -> float:
    return (
        0.4 * coverage_gain(prev, cand)
        + 0.3 * non_contradiction(prev, cand)
        + 0.2 * schema_valid(cand)
        + 0.1 * novelty(prev, cand)
    )
