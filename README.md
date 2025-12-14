# SourceMapR

**Evidence observability for RAG.** See what your RAG system actually saw.

SourceMapR traces every answer back to the exact document evidence that produced it — and shows how that evidence was created (parse → chunk → embed → retrieve → answer).

---

## Why SourceMapR?

| Problem | SourceMapR Solution |
|---------|---------------------|
| "Which chunks did the retriever return?" | See every retrieved chunk with similarity scores |
| "What prompt was sent to the LLM?" | Full prompt/response capture with token counts |
| "Why did the model hallucinate?" | Click any chunk to view it in the original PDF |
| "Is my chunking strategy working?" | Compare experiments side by side |

**Two lines of code. Full evidence lineage.**

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/kamathhrishi/sourcemapr.git
cd sourcemapr && pip install -e .

# Start dashboard
sourcemapr server
```

```python
from sourcemapr import init_tracing, stop_tracing

init_tracing(endpoint="http://localhost:5000")

# Your LlamaIndex / LangChain code here — unchanged
# Everything is automatically traced

stop_tracing()
```

Open **http://localhost:5000** to see traces.

---

## Supported Frameworks

| Framework | Documents | Chunks | Retrieval | LLM Calls |
|-----------|-----------|--------|-----------|-----------|
| **LlamaIndex** | ✅ | ✅ | ✅ | ✅ |
| **LangChain** | ✅ | ✅ | ✅ | ✅ |
| **OpenAI** | — | — | — | ✅ |

See [Supported Features](sourcemapr/providers/README.md) for details.

---

## Features

- **Answer → Evidence** — Trace responses to exact chunks with scores
- **PDF Source Viewer** — Click any chunk to see it in the original document
- **Full LLM Capture** — Prompts, responses, tokens, latency
- **Experiment Tracking** — A/B test configurations
- **Real-time Dashboard** — Watch traces appear live

---

## Examples

```bash
# LlamaIndex
python examples/demo.py

# LangChain
python examples/langchain_demo.py
```

See [Examples](examples/README.md) for more.

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
