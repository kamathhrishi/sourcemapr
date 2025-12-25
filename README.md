# SourceMapR

[![PyPI version](https://img.shields.io/pypi/v/sourcemapr.svg)](https://pypi.org/project/sourcemapr/)
[![Python versions](https://img.shields.io/pypi/pyversions/sourcemapr.svg)](https://pypi.org/project/sourcemapr/)
[![License](https://img.shields.io/pypi/l/sourcemapr.svg)](https://github.com/kamathhrishi/sourcemapr/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/sourcemapr.svg)](https://pypi.org/project/sourcemapr/)

**See what your RAG system actually saw.**

SourceMapR provides evidence observability for RAG pipelines. Trace every LLM answer back to the exact document evidence that produced it, with complete evidence lineage.

---

## Why SourceMapR?

| Problem | SourceMapR Solution |
|---------|---------------------|
| "Which chunks did the retriever return?" | See every retrieved chunk with similarity scores |
| "What prompt was sent to the LLM?" | Full prompt/response capture with token counts |
| "Why did the model hallucinate?" | Click any chunk to view it in the original PDF |
| "Is my chunking strategy working?" | Compare experiments side by side |

**Add RAG observability in two lines of code.**

---

## Document Support

| Format | Status | Notes |
|--------|--------|-------|
| **PDF** | ✅ Supported | Full support with chunk highlighting and source viewing |
| HTML | 🧪 Experimental | Basic rendering, chunk highlighting may not work |
| Other formats | 🧪 Experimental | Under development |

> **Current Focus:** SourceMapR is optimized for **PDF documents**. Support for HTML and other file types is experimental and under active development.

---

## Quick Start

```bash
pip install sourcemapr
sourcemapr server
```

### LlamaIndex

```python
from sourcemapr import init_tracing, stop_tracing
init_tracing(endpoint="http://localhost:5000")

# Your existing LlamaIndex code — unchanged
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

documents = SimpleDirectoryReader("./papers").load_data()
index = VectorStoreIndex.from_documents(documents)

response = index.as_query_engine().query("What is attention?")
print(response)

stop_tracing()
```

### LangChain

```python
from sourcemapr import init_tracing, stop_tracing
init_tracing(endpoint="http://localhost:5000")

# Your existing LangChain code — unchanged
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

loader = PyPDFLoader("./papers/attention.pdf")
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=512)
chunks = splitter.split_documents(documents)

vectorstore = FAISS.from_documents(chunks, embeddings)
results = vectorstore.similarity_search("What is attention?")

stop_tracing()
```

Open **http://localhost:5000** to see the full evidence lineage.

---

## Supported Frameworks

| Framework | Documents | Chunks | Retrieval | LLM Calls |
|-----------|-----------|--------|-----------|-----------|
| **LlamaIndex** | ✅ | ✅ | ✅ | ✅ |
| **LangChain** | ✅ | ✅ | ✅ | ✅ |
| **OpenAI** | — | — | — | ✅ |

### Pipeline Support

> **⚠️ Experimental:** Pipeline tracing (e.g., `langchain_pipeline_demo.py`) is currently experimental and does not have stable support. Basic functionality works but may have limitations.

See [Supported Features](sourcemapr/providers/README.md) for details.

---

## Features

- **Trace LLM Answers to Sources** — Trace responses to exact chunks with similarity scores and rankings
- **PDF Chunk Viewer** — Click any chunk to see it highlighted in the original PDF
- **Full LLM Tracing** — Prompts, responses, tokens, latency for every query
- **Experiment Tracking** — Organize runs and compare chunking strategies
- **Evidence Lineage** — Complete trace from document load → parse → chunk → embed → retrieve → answer
- **Debug RAG Hallucinations** — Verify grounding without guessing

---

## CLI Commands

```bash
# Server management
sourcemapr server            # Start server (foreground)
sourcemapr server -b         # Start server in background
sourcemapr server -p 8080    # Start on custom port
sourcemapr stop              # Stop running server
sourcemapr restart           # Restart server
sourcemapr status            # Check if server is running

# Data management
sourcemapr clear             # Clear all trace data (with confirmation)
sourcemapr clear -y          # Clear without confirmation
sourcemapr init              # Initialize database
sourcemapr init --reset      # Delete and recreate database

# Info
sourcemapr version           # Show version
```

---

## Examples

```bash
# LlamaIndex with PDFs
python examples/llamaindex_pdf_demo.py

# LangChain with PDFs
python examples/langchain_pdf_demo.py
```

See [Examples](examples/README.md) for more.

---

## Installation

### From PyPI

```bash
pip install sourcemapr
```

### From Source

```bash
git clone https://github.com/kamathhrishi/sourcemapr.git
cd sourcemapr && pip install -e .
```

---

## Documentation

- [Supported Features](sourcemapr/providers/README.md) — Framework coverage
- [Examples](examples/README.md) — Usage examples
- [REST API](docs/API.md) — API endpoints

---

## License

MIT

---

**Built for developers who are tired of print-debugging RAG pipelines.**

[Website](https://kamathhrishi.github.io/sourcemapr) · [GitHub](https://github.com/kamathhrishi/sourcemapr)
