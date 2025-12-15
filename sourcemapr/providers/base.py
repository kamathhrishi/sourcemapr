"""
Base provider class for SourcemapR instrumentation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from sourcemapr.store import TraceStore


class BaseProvider(ABC):
    """Base class for all framework providers."""

    name: str = "base"

    def __init__(self, store: TraceStore):
        self.store = store
        self._instrumented = False
        self._original_handlers: Dict[str, Any] = {}

    def _register_framework(self):
        """Register this framework with the store."""
        if self.name and self.name != "base":
            self.store.frameworks.add(self.name)

    @abstractmethod
    def instrument(self) -> bool:
        """
        Install hooks for this framework.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def uninstrument(self) -> None:
        """Remove hooks and restore original methods."""
        pass

    def is_available(self) -> bool:
        """Check if this framework is available."""
        return False
