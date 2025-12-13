# SourcemapR

RAG Observability Platform - Trace, debug and understand your RAG pipelines with ease.

## Features

- **Document Tracing**: Track document loading, parsing, and chunking
- **Embedding Monitoring**: Monitor embedding generation with timing
- **Query Tracing**: Full visibility into retrieval operations and results
- **LLM Call Logging**: Capture prompts, responses, and token usage
- **Experiments**: Organize traces into experiments for A/B testing
- **Web Dashboard**: Real-time visualization of your RAG pipeline

## Installation

```bash
pip install sourcemapr
```

Or install from source:

```bash
git clone https://github.com/yourusername/sourcemapr.git
cd sourcemapr
pip install -e .
```

For LlamaIndex integration:

```bash
pip install sourcemapr[llamaindex]
```

## Quick Start

### 1. Start the Server

```bash
sourcemapr server
```

This starts the observability dashboard at http://localhost:5000

### 2. Add Tracing to Your Code

```python
from sourcemapr import init_tracing, stop_tracing

# Initialize tracing (connects to SourcemapR server)
init_tracing(endpoint="http://localhost:5000")

# Your LlamaIndex code here...
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

# Load documents (automatically traced)
documents = SimpleDirectoryReader("./data").load_data()

# Create index (chunking and embeddings traced)
index = VectorStoreIndex.from_documents(documents)

# Query (retrieval and LLM calls traced)
query_engine = index.as_query_engine()
response = query_engine.query("What is RAG?")

# Stop tracing when done
stop_tracing()
```

### 3. View Results

Open http://localhost:5000 in your browser to see:
- Documents loaded and parsed
- Chunks created with text preview
- Embedding generation times
- Query results with retrieved chunks
- LLM prompts and responses

## Experiment Tracking

Organize your traces into experiments:

```python
from sourcemapr import init_tracing

# Traces will be automatically assigned to this experiment
init_tracing(
    endpoint="http://localhost:5000",
    experiment="chunking-strategy-v2"
)
```

## What Gets Traced

| Operation | Tracked Data |
|-----------|--------------|
| **Documents** | Filename, path, page count, text length |
| **Chunks** | Index, text content, length, parent doc |
| **Embeddings** | Model, dimensions, duration |
| **Retrievals** | Query, results with scores, duration |
| **LLM Calls** | Model, messages, response, tokens, duration |

## API Reference

### init_tracing

```python
init_tracing(
    endpoint: str = "http://localhost:5000",
    experiment: str = None  # Optional experiment name
)
```

Initializes the tracing system and connects to the SourcemapR server.

### stop_tracing

```python
stop_tracing()
```

Stops tracing and flushes any pending data to the server.

### get_tracer

```python
from sourcemapr import get_tracer

tracer = get_tracer()
```

Returns the current TraceStore instance for advanced usage.

## CLI Commands

```bash
# Start the server
sourcemapr server

# Start on a custom port
sourcemapr server --port 8000

# Show version
sourcemapr version
```

## Dashboard Features

- **Documents Tab**: View all loaded documents with page counts and chunk counts
- **Queries Tab**: See all queries with retrieved chunks, LLM calls, and latency
- **Experiments**: Filter data by experiment, create/rename/delete experiments
- **Source Viewer**: Click on any chunk to see it highlighted in the original document

## Platform API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data` | GET | All trace data |
| `/api/stats` | GET | Summary stats |
| `/api/traces` | POST | Receive trace (from lib) |
| `/api/experiments` | GET/POST | List/create experiments |
| `/api/experiments/{id}` | PUT/DELETE | Update/delete experiment |
| `/api/documents` | GET | List documents |
| `/api/chunks` | GET | List chunks |
| `/api/retrievals` | GET | List retrievals |
| `/api/llm` | GET | List LLM calls |
| `/api/clear` | POST | Clear all data |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black sourcemapr
ruff check sourcemapr
```

## Architecture

```
sourcemapr/
├── __init__.py       # Main exports (init_tracing, stop_tracing)
├── tracer.py         # LlamaIndex instrumentation
├── store.py          # Trace storage and sending
├── cli.py            # CLI entry point
└── server/
    ├── app.py        # FastAPI server
    ├── database.py   # SQLite storage
    └── templates/    # Web dashboard
```

## How It Works

The library uses monkey-patching to hook into LlamaIndex classes:

1. `SimpleDirectoryReader.load_data` - tracks documents
2. `SentenceSplitter.get_nodes_from_documents` - tracks chunks
3. `VectorStoreIndex.from_documents` - tracks indexing
4. `RetrieverQueryEngine.query` - tracks queries & retrievals
5. `OpenAI.chat/complete` - tracks LLM calls

All hooks are installed automatically when you call `init_tracing()`.

## License

MIT
