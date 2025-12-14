# Supported Frameworks

SourceMapR auto-detects and instruments available frameworks.

---

## LlamaIndex

**Full support** — Documents, chunks, embeddings, retrieval, LLM calls.

| Component | What's Traced |
|-----------|---------------|
| `SimpleDirectoryReader` | Document loading, file paths, page counts |
| `SentenceSplitter` | Chunk text, indices, page numbers, char positions |
| `VectorStoreIndex` | Index creation |
| `QueryEngine` | Queries, retrieved chunks, similarity scores |
| `HuggingFaceEmbedding` | Model, dimensions, duration |
| **LLM calls** | Prompts, responses, tokens, latency (via callbacks) |

### Usage

```python
from sourcemapr import init_tracing, stop_tracing

init_tracing(endpoint="http://localhost:5000")

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

docs = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(docs)
response = index.as_query_engine().query("What is RAG?")

stop_tracing()
```

---

## LangChain

**Full support** — Documents, chunks, retrieval, LLM calls.

| Component | What's Traced |
|-----------|---------------|
| `PyPDFLoader` | Document loading, file paths, page counts |
| `DirectoryLoader` | Batch document loading |
| `RecursiveCharacterTextSplitter` | Chunk text, indices, metadata |
| **Retrievers** | Queries, retrieved docs, scores (via callbacks) |
| **LLM calls** | Prompts/messages, responses, tokens (via callbacks) |

### Usage

```python
from sourcemapr import init_tracing, stop_tracing, get_langchain_handler

init_tracing(endpoint="http://localhost:5000")
handler = get_langchain_handler()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI

# Document loading and chunking are auto-traced
loader = PyPDFLoader("doc.pdf")
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=512)
chunks = splitter.split_documents(docs)

# Pass handler to trace LLM calls and retrieval
llm = ChatOpenAI(model="gpt-4o-mini")
response = llm.invoke("Hello", config={"callbacks": [handler]})

stop_tracing()
```

### Callback Handler

For LangChain, use `get_langchain_handler()` to get a callback handler:

```python
from sourcemapr import get_langchain_handler

handler = get_langchain_handler()

# Use in chains
chain.invoke(query, config={"callbacks": [handler]})

# Or set globally
from langchain_core.globals import set_llm_cache
# handler can be added to any chain's config
```

---

## OpenAI

**LLM calls only** — Direct OpenAI client instrumentation.

| Component | What's Traced |
|-----------|---------------|
| `chat.completions.create` | Messages, response, tokens, latency, tool calls |
| `ChatCompletion.create` (v0) | Messages, response, tokens, latency |

### Usage

```python
from sourcemapr import init_tracing, stop_tracing

init_tracing(endpoint="http://localhost:5000")

from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}]
)

stop_tracing()
```

---

## What Gets Traced

| Stage | Data Captured |
|-------|---------------|
| **Document Loading** | Filename, path, page count, text length |
| **Parsing** | Full extracted text |
| **Chunking** | Chunk text, index, page number, char positions |
| **Embeddings** | Model, dimensions, duration |
| **Retrieval** | Query, top-k chunks, similarity scores |
| **LLM Calls** | Model, messages/prompt, response, tokens, latency |

---

## Adding New Providers

Create a new provider in `sourcemapr/providers/`:

```python
from sourcemapr.providers.base import BaseProvider

class MyFrameworkProvider(BaseProvider):
    name = "myframework"

    def is_available(self) -> bool:
        try:
            import myframework
            return True
        except ImportError:
            return False

    def instrument(self) -> bool:
        # Patch methods here
        return True

    def uninstrument(self) -> None:
        # Restore original methods
        pass
```

Then add to `tracer.py`:

```python
def _try_provider(self, name: str):
    # ...
    elif name == 'myframework':
        from sourcemapr.providers.myframework import MyFrameworkProvider
        provider = MyFrameworkProvider(self.store)
```
