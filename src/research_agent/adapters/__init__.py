"""Modular adapters connecting the research agent to external services and documentation."""

from research_agent.adapters.composio_client import ComposioAdapter
from research_agent.adapters.documentation_search import DocumentationSearchAdapter
from research_agent.adapters.groq_client import GroqAdapter

__all__ = [
    "ComposioAdapter",
    "DocumentationSearchAdapter",
    "GroqAdapter",
]
