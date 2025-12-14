"""
SourcemapR Tracer - Main instrumentation orchestrator.

Automatically detects and instruments available frameworks:
- LlamaIndex
- LangChain
- OpenAI
"""

from typing import Optional, List
from contextlib import contextmanager

from sourcemapr.store import TraceStore
from sourcemapr.providers.base import BaseProvider

# Global tracer instance
_tracer: Optional['Tracer'] = None


class Tracer:
    """
    Main tracer that orchestrates all framework providers.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        experiment: Optional[str] = None,
        project_name: str = "default"
    ):
        self.store = TraceStore(endpoint=endpoint, experiment=experiment)
        self.project_name = project_name
        self.providers: List[BaseProvider] = []
        self._instrumented = False

    def instrument(self):
        """Install hooks for all available frameworks."""
        if self._instrumented:
            return

        # Try each provider
        self._try_provider('llamaindex')
        self._try_provider('openai')
        self._try_provider('langchain')

        self._instrumented = True
        print(f"[SourcemapR] Tracing enabled -> {self.store.endpoint or 'local'}")

    def _try_provider(self, name: str):
        """Try to load and instrument a provider."""
        try:
            if name == 'llamaindex':
                from sourcemapr.providers.llamaindex import LlamaIndexProvider
                provider = LlamaIndexProvider(self.store)
            elif name == 'openai':
                from sourcemapr.providers.openai import OpenAIProvider
                provider = OpenAIProvider(self.store)
            elif name == 'langchain':
                from sourcemapr.providers.langchain import LangChainProvider
                provider = LangChainProvider(self.store)
            else:
                return

            if provider.is_available() and provider.instrument():
                self.providers.append(provider)
        except ImportError:
            pass
        except Exception as e:
            print(f"[SourcemapR] Warning: Could not load {name} provider: {e}")

    def get_langchain_handler(self):
        """Get the LangChain callback handler for use in chains."""
        for provider in self.providers:
            if provider.name == 'langchain':
                return provider.get_callback_handler()
        return None

    def uninstrument(self):
        """Remove all hooks."""
        for provider in self.providers:
            provider.uninstrument()
        self.providers.clear()
        self._instrumented = False

    @contextmanager
    def trace(self, name: str = ""):
        """Context manager for manual tracing."""
        self.store.start_trace(name)
        try:
            yield
        finally:
            self.store.end_trace()

    def stop(self):
        """Stop the tracer and flush pending data."""
        self.store.stop()


def init_tracing(
    endpoint: Optional[str] = None,
    experiment: Optional[str] = None,
    project_name: str = "default"
) -> Tracer:
    """
    Initialize tracing for RAG frameworks.

    Args:
        endpoint: URL of the SourcemapR server (e.g., "http://localhost:5000")
        experiment: Optional experiment name to group traces
        project_name: Name for this project

    Example:
        >>> from sourcemapr import init_tracing
        >>> init_tracing(endpoint="http://localhost:5000")

        # With experiment tracking
        >>> init_tracing(endpoint="http://localhost:5000", experiment="chunk-size-512")
    """
    global _tracer
    if _tracer is None:
        _tracer = Tracer(endpoint=endpoint, experiment=experiment, project_name=project_name)
        _tracer.instrument()
    return _tracer


def stop_tracing():
    """Stop tracing and flush pending data."""
    global _tracer
    if _tracer:
        _tracer.stop()
        _tracer = None


def get_tracer() -> Optional[Tracer]:
    """Get the current tracer instance."""
    return _tracer


def get_langchain_handler():
    """
    Get the LangChain callback handler for use in chains.

    Example:
        >>> from sourcemapr import init_tracing, get_langchain_handler
        >>> init_tracing(endpoint="http://localhost:5000")
        >>> handler = get_langchain_handler()
        >>> chain.invoke({"query": "..."}, config={"callbacks": [handler]})
    """
    if _tracer:
        return _tracer.get_langchain_handler()
    return None
