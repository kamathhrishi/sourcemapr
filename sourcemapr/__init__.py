"""
SourcemapR - RAG Observability Platform

Trace, debug and understand your RAG pipelines with ease.

Usage:
    from sourcemapr import init_tracing, stop_tracing

    # Initialize tracing (connects to SourcemapR server)
    init_tracing(endpoint="http://localhost:5000")

    # Your LlamaIndex code here...

    # Stop tracing when done
    stop_tracing()

To start the server:
    sourcemapr server
"""

from sourcemapr.tracer import init_tracing, stop_tracing, get_tracer, get_langchain_handler

__version__ = "0.1.1"
__all__ = ["init_tracing", "stop_tracing", "get_tracer", "get_langchain_handler", "__version__"]
