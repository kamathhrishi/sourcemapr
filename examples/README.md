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

## PDF Examples (Recommended)

### LlamaIndex PDF Example

**File:** `llamaindex_pdf_demo.py`

Basic RAG with LlamaIndex using PDF documents (attention paper, Llama 2 paper, RAG paper).

```bash
python examples/llamaindex_pdf_demo.py
```

**What it does:**
- Loads PDFs from `./data`
- Creates vector index with HuggingFace embeddings
- Queries: "What is attention?", "How was Llama 2 trained?", "What is RAG?"

---

### LangChain PDF Example

**File:** `langchain_pdf_demo.py`

Basic RAG with LangChain using FAISS and OpenAI with PDF documents.

```bash
pip install langchain langchain-openai langchain-community faiss-cpu pypdf
python examples/langchain_pdf_demo.py
```

**What it does:**
- Loads PDFs with DirectoryLoader
- Chunks with RecursiveCharacterTextSplitter
- Creates FAISS vector store
- Builds RAG chain with ChatOpenAI

---

## HTML Examples (Experimental)

> **Note:** HTML document support is experimental. The document viewer works best with PDFs. HTML files may render but chunk highlighting and page navigation may not work as expected.

### Tesla 10K SEC Filing (LlamaIndex)

**File:** `tesla_10k_sec.py`

Demonstrates hierarchical retrieval with SEC HTML filings.

```bash
python examples/tesla_10k_sec.py
```

### Tesla 10K SEC Filing (LangChain)

**File:** `tesla_10k_sec_langchain.py`

Same as above but using LangChain.

```bash
python examples/tesla_10k_sec_langchain.py
```

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
