"""Base types shared across all sub-agents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    """Unified response from any sub-agent."""

    content: str  # The response text
    agent: str  # Which agent handled it
    confidence: float  # 0-1 confidence
    metadata: dict = field(default_factory=dict)  # Agent-specific data
    follow_up: str | None = None  # Suggested follow-up question
