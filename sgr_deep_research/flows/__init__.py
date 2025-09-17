"""Prefect flows for SGR Deep Research agents."""

from .research_flow import research_flow
from .batch_simple import batch_simple_flow

__all__ = ["research_flow", "batch_simple_flow"]