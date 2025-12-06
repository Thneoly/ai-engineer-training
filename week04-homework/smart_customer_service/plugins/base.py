"""Plugin abstraction for extending customer service capabilities."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    capabilities: List[str]


class BasePlugin(ABC):
    """All plugins must implement the `handle` interface."""

    metadata: PluginMetadata

    @abstractmethod
    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process payload and return structured result."""

    def matches(self, capability: str) -> bool:
        return capability in self.metadata.capabilities
