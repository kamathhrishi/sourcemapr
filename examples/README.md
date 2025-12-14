# Examples

## Prerequisites

1. Start the SourceMapR server:
   ```bash
   sourcemapr server
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your-key
   ```

3. Add some PDFs to the `data/` folder

---

## LlamaIndex Example

**File:** `demo.py`

Basic RAG with LlamaIndex using the attention paper, Llama 2 paper, and RAG paper.

```bash
python examples/demo.py
```

**What it does:**
- Loads PDFs from `./data`
- Creates vector index with HuggingFace embeddings
- Queries: "What is attention?", "How was Llama 2 trained?", "What is RAG?"

---

## LangChain Example

**File:** `langchain_demo.py`

Basic RAG with LangChain using FAISS and OpenAI.

```bash
pip install langchain langchain-openai langchain-community faiss-cpu pypdf
python examples/langchain_demo.py
```

**What it does:**
- Loads PDFs with DirectoryLoader
- Chunks with RecursiveCharacterTextSplitter
- Creates FAISS vector store
- Builds RAG chain with ChatOpenAI

---

## Experiment Tracking

Compare different configurations:

```python
from sourcemapr import init_tracing, stop_tracing

# Experiment 1
init_tracing(endpoint="http://localhost:5000", experiment="chunk-256")
# ... run with chunk_size=256 ...
stop_tracing()

# Experiment 2
init_tracing(endpoint="http://localhost:5000", experiment="chunk-1024")
# ... run with chunk_size=1024 ...
stop_tracing()
```

Then use the experiment dropdown in the dashboard to compare.
