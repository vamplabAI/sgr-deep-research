from __future__ import annotations
from typing import Dict

class CallableAdapter:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, prompt: str, params: Dict):
        return self.fn(prompt=prompt, **params)
