# SourceMapR

**Evidence observability for RAG.** See what your RAG system actually saw.

SourceMapR traces every answer back to the exact document evidence that produced it — and shows how that evidence was created (parse → chunk → embed → retrieve → answer).

> Ever wondered why your RAG app returned a weird answer? Now you can see exactly which chunks were retrieved, what prompts were sent to the LLM, and trace the entire flow from query to response.

---

## Why SourceMapR?

Most "LLM observability" tools stop at tracing calls and showing retrieved text. SourceMapR goes deeper.

| Problem | SourceMapR Solution |
|---------|---------------------|
| "Which chunks did the retriever return?" | See every retrieved chunk with similarity scores |
| "What prompt was sent to the LLM?" | Full prompt/response capture with token counts |
| "Why did the model hallucinate?" | Click any chunk to view it in the original PDF |
| "Is my chunking strategy working?" | Compare experiments side by side |

**Two lines of code. Full evidence lineage.**

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/kamathhrishi/sourcemapr.git
cd sourcemapr
pip install -e .
```

### 2. Start the Dashboard

```bash
sourcemapr server
```

Opens at [http://localhost:5000](http://localhost:5000)

### 3. Add Two Lines to Your Code

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

### 4. See the Evidence

Open [http://localhost:5000](http://localhost:5000) and watch your traces appear in real-time.

---

## What You'll See

### Documents Tab
- Every PDF, text file, and document loaded
- Page counts and chunk counts
- Click to expand and see all chunks with text previews

### Queries Tab
- Every query with retrieved chunks and similarity scores
- Full LLM prompt and response
- Token usage and latency
- **Click "View Source"** to see chunks highlighted in the original PDF

### Experiments
- Organize runs into experiments
- Filter by experiment
- Compare "chunk-size-256" vs "chunk-size-512" side by side

---

## Features

| Feature | Description |
|---------|-------------|
| **Answer → Evidence** | Trace responses to exact chunks with scores |
| **PDF Source Viewer** | Click any chunk to see it in the original document |
| **Full LLM Capture** | Prompts, responses, tokens, latency |
| **Experiment Tracking** | A/B test chunking strategies |
| **Real-time Dashboard** | Watch traces appear live |
| **Zero Config** | Just `init_tracing()` — everything else is automatic |

---

## Example: Research Papers

```python
from sourcemapr import init_tracing, stop_tracing

# Start tracing with an experiment name
init_tracing(
    endpoint="http://localhost:5000",
    experiment="attention-paper-analysis"
)

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Configure
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Load papers
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# Query
engine = index.as_query_engine(similarity_top_k=3)

queries = [
    "What is the attention mechanism?",
    "How was Llama 2 trained?",
    "What is retrieval augmented generation?",
]

for q in queries:
    print(f"Q: {q}")
    print(f"A: {engine.query(q)}\n")

stop_tracing()
```

Now check the dashboard to see:
- How many chunks were created from each paper
- Which chunks were retrieved for each query
- The exact prompts sent to the LLM
- Full responses with token counts

---

## Experiment Tracking

Compare different RAG configurations:

```python
# Experiment 1: Small chunks
init_tracing(endpoint="http://localhost:5000", experiment="small-chunks-256")
Settings.node_parser = SentenceSplitter(chunk_size=256)
# ... run queries ...
stop_tracing()

# Experiment 2: Large chunks
init_tracing(endpoint="http://localhost:5000", experiment="large-chunks-1024")
Settings.node_parser = SentenceSplitter(chunk_size=1024)
# ... run same queries ...
stop_tracing()
```

Use the experiment dropdown in the dashboard to compare results.

---

## What Gets Traced

| Stage | What's Captured |
|-------|-----------------|
| **Document Loading** | Filename, path, page count |
| **Parsing** | Full extracted text |
| **Chunking** | Each chunk's text, index, page number |
| **Retrieval** | Query, top-k chunks, similarity scores |
| **LLM Calls** | Model, prompt, response, tokens, latency |

---

## CLI

```bash
sourcemapr server              # Start dashboard on :5000
sourcemapr server --port 8080  # Custom port
sourcemapr version             # Show version
```

---

## API Reference

### `init_tracing(endpoint, experiment)`

```python
init_tracing(
    endpoint="http://localhost:5000",  # Server URL
    experiment="my-experiment"          # Optional: group traces
)
```

**Important:** Call `init_tracing()` *before* importing LlamaIndex for best results.

### `stop_tracing()`

Stop tracing and flush pending data. Always call before exit.

---

## REST API

| Endpoint | Description |
|----------|-------------|
| `GET /api/data` | All trace data |
| `GET /api/stats` | Summary statistics |
| `GET /api/documents` | List documents |
| `GET /api/chunks` | List chunks |
| `GET /api/retrievals` | List queries |
| `GET /api/llm` | List LLM calls |
| `GET /api/experiments` | List experiments |
| `POST /api/clear` | Clear all data |

Add `?experiment_id=X` to filter.

---

## Troubleshooting

**Traces not showing?**
1. Server running? `sourcemapr server`
2. Correct endpoint? `init_tracing(endpoint="http://localhost:5000")`
3. Called `stop_tracing()` before exit?

**Only some operations traced?**
```python
# ✓ Correct: tracing first
from sourcemapr import init_tracing
init_tracing(endpoint="http://localhost:5000")
from llama_index.core import VectorStoreIndex

# ✗ Wrong: LlamaIndex imported first
from llama_index.core import VectorStoreIndex
from sourcemapr import init_tracing  # Too late!
```

---

## Project Structure

```
sourcemapr/
├── __init__.py      # init_tracing, stop_tracing, get_tracer
├── tracer.py        # LlamaIndex instrumentation
├── store.py         # Sends traces to server
├── cli.py           # CLI (sourcemapr server)
└── server/
    ├── app.py       # FastAPI server
    ├── database.py  # SQLite storage
    └── templates/   # Dashboard
```

---

## Contributing

```bash
git clone https://github.com/kamathhrishi/sourcemapr.git
cd sourcemapr
pip install -e ".[dev]"
pytest
```

---

## License

MIT

---

**Built for developers who are tired of print-debugging RAG pipelines.**

[Website](https://yourusername.github.io/sourcemapr) · [GitHub](https://github.com/kamathhrishi/sourcemapr) · [Issues](https://github.com/kamathhrishi/sourcemapr/issues)
