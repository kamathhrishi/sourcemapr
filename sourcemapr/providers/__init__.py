"""
SourcemapR Providers - Framework-specific instrumentation.
"""

from sourcemapr.providers.base import BaseProvider
from sourcemapr.providers.llamaindex import LlamaIndexProvider
from sourcemapr.providers.openai import OpenAIProvider

__all__ = ['BaseProvider', 'LlamaIndexProvider', 'OpenAIProvider']

# Try to import LangChain provider if available
try:
    from sourcemapr.providers.langchain import LangChainProvider
    __all__.append('LangChainProvider')
except ImportError:
    pass
