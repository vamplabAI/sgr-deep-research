from __future__ import annotations
from .state import AgentState
from .decoding import generate_json

PLANNER_PROMPT = """You are a research assistant. Create a simple research plan.

Query: {query}

Respond with valid JSON only:
{{
  "facts": [],
  "goals": ["{query}"],
  "plan": ["research jazz history", "find jazz origins", "identify key influences"],
  "constraints": {{}},
  "step": 0
}}"""

EXECUTOR_PROMPT = """Execute the research plan and generate facts.

Output ONLY valid JSON in this exact format:
{{
  "facts": [
    {{"text": "Jazz originated in New Orleans in the early 1900s", "source": null, "confidence": 0.8}},
    {{"text": "Jazz combined African rhythms with European harmonies", "source": null, "confidence": 0.7}}
  ],
  "goals": [],
  "plan": [],
  "constraints": {{}},
  "step": 1
}}

Current state: {state}"""

def plan_once(llm, state: AgentState, params) -> AgentState:
    query = state.goals[0] if state.goals else "research topic"
    prompt = PLANNER_PROMPT.format(query=query, state=state.brief_context())
    ok, model, err = generate_json(llm, prompt, AgentState, {**params, "temperature": 0.15, "top_p": 0.8})
    if not ok:
        raise RuntimeError(f"Planner failed: {err}")
    model.step = state.step + 1
    return AgentState(
        facts=state.facts, goals=state.goals, plan=model.plan,
        constraints=state.constraints, step=model.step
    )

def execute_once(llm, state: AgentState, params) -> AgentState:
    prompt = EXECUTOR_PROMPT.format(state=state.brief_context())
    ok, model, err = generate_json(llm, prompt, AgentState, {**params, "temperature": 0.3, "top_p": 0.85})
    if not ok:
        raise RuntimeError(f"Executor failed: {err}")
    merged = list(state.facts)
    for f in model.facts:
        if all(f.text.strip().lower() != g.text.strip().lower() for g in merged):
            merged.append(f)
    return AgentState(
        facts=merged, goals=state.goals, plan=state.plan,
        constraints=state.constraints, step=state.step
    )
