from __future__ import annotations
from typing import Tuple, Callable
from pydantic import ValidationError
from .state import AgentState
import json, re

# Optional outlines JSON constraint (not required)
try:
    from outlines.fsm.json_schema import build_regex_from_schema  # noqa: F401
    USE_OUTLINES = True
except Exception:
    USE_OUTLINES = False

def try_validate_and_repair(raw: str, Model) -> Tuple[bool, AgentState | None, str]:
    # Parse JSON, attempt small repairs on failure
    try:
        obj = json.loads(raw)
    except Exception:
        # Try basic cleanup
        candidate = re.sub(r"^[^{]*", "", raw, flags=re.S)
        candidate = re.sub(r"([^}])+$", "", candidate, flags=re.S)
        
        # Fix common JSON errors
        # Fix double opening braces in arrays: [{{ -> [{
        candidate = re.sub(r'\[\{\{', '[{', candidate)
        # Fix double closing braces in arrays: }}] -> }]
        candidate = re.sub(r'\}\}\]', '}]', candidate)
        # Fix missing commas between objects
        candidate = re.sub(r'\}\s*\{', '}, {', candidate)
        
        try:
            obj = json.loads(candidate)
        except Exception as e2:
            print(f"DEBUG - Cleaned JSON: {candidate[:200]}...")
            return False, None, f"JSON parse failed: {e2}"
    
    try:
        model = Model.model_validate(obj)
        return True, model, ""
    except ValidationError as ve:
        return False, None, f"Schema validation failed: {ve.errors()[:3]}"

def generate_json(llm: Callable[[str, dict], str], prompt: str, Model, params: dict):
    raw = llm(prompt, params)
    print(f"DEBUG - Raw response: {raw[:200]}...")
    return try_validate_and_repair(raw, Model)
