# Supported Frameworks

SourceMapR auto-detects and instruments available frameworks.

---

## LlamaIndex

**Full support** — Documents, chunks, embeddings, retrieval, LLM calls.

### Document Loading

| Function | What's Traced |
|----------|---------------|
| `SimpleDirectoryReader.load_data()` | File paths, page counts, text length, full text |
| `FlatReader.load_data()` | HTML/text files, file path, text content |

### Chunking

| Function | What's Traced |
|----------|---------------|
| `NodeParser.get_nodes_from_documents()` | All node parsers (SentenceSplitter, etc.) |
| ↳ Per chunk | Chunk ID, text, index, page number, start/end char positions, metadata |

### Indexing

| Function | What's Traced |
|----------|---------------|
| `VectorStoreIndex.from_documents()` | Document count, index creation |

### Embeddings

| Function | What's Traced |
|----------|---------------|
| `HuggingFaceEmbedding._get_text_embedding()` | Model name, dimensions, duration (ms) |

### Query & Retrieval (via Callbacks)

| Event | What's Traced |
|-------|---------------|
| `CBEventType.QUERY` | Query string, duration |
| ↳ Response | Source nodes, similarity scores, response text |
| `CBEventType.LLM` | Model, temperature, max_tokens |
| ↳ Input | Messages (role + content) or prompt string |
| ↳ Output | Response text, prompt/completion/total tokens, latency |

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

### Document Loading

| Function | What's Traced |
|----------|---------------|
| `BaseLoader.load()` | Base class - catches all loaders |
| `PyPDFLoader.load()` | PDF files, pages, text content |
| `PyPDFLoader.lazy_load()` | Lazy loading (used by DirectoryLoader) |
| `DirectoryLoader.load()` | Batch loading, file paths, page counts |
| `TextLoader.load()` | Plain text files |
| `UnstructuredFileLoader.load()` | Various file formats |
| ↳ Per document | Filename, absolute file path, page count, full text |

### Chunking

| Function | What's Traced |
|----------|---------------|
| `TextSplitter.split_documents()` | Base class - catches all splitters |
| ↳ RecursiveCharacterTextSplitter | Chunk text, index, page number, source path |
| ↳ CharacterTextSplitter | Chunk text, index, page number, source path |
| ↳ Per chunk | Chunk ID, doc ID, text, index, page number, metadata |

### Retrieval (via Callbacks)

| Callback | What's Traced |
|----------|---------------|
| `on_retriever_start()` | Query string, start time |
| `on_retriever_end()` | Retrieved documents, duration |
| ↳ Per result | Chunk ID, score, text (500 chars), doc ID, page number, file path |

### LLM Calls (via Callbacks)

| Callback | What's Traced |
|----------|---------------|
| `on_llm_start()` | Model name, prompts |
| `on_llm_end()` | Response text, prompt/completion/total tokens, latency |
| `on_llm_error()` | Error message, duration |
| `on_chat_model_start()` | Model name, messages (role + content) |

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

# Or in retrievers
retriever.invoke(query, config={"callbacks": [handler]})
```

---

## OpenAI

**LLM calls only** — Direct OpenAI client instrumentation.

### Chat Completions (v1.x)

| Function | What's Traced |
|----------|---------------|
| `client.chat.completions.create()` | Full chat completion calls |
| ↳ Input | Messages (role + content), model, temperature, max_tokens, stop |
| ↳ Output | Response text, finish_reason, tool_calls |
| ↳ Usage | Prompt tokens, completion tokens, total tokens |
| ↳ Timing | Duration (ms) |
| ↳ Errors | Error message on failure |

### Chat Completions (v0.x Legacy)

| Function | What's Traced |
|----------|---------------|
| `openai.ChatCompletion.create()` | Legacy chat API |
| ↳ Input | Messages, model, temperature, max_tokens |
| ↳ Output | Response text, token usage, duration |

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

## What Gets Traced (Summary)

| Stage | Data Captured |
|-------|---------------|
| **Document Loading** | Filename, absolute path, page count, text length, full text |
| **Parsing** | Full extracted text with page breaks |
| **Chunking** | Chunk ID, text, index, page number, char positions, metadata |
| **Embeddings** | Model name, vector dimensions, duration |
| **Retrieval** | Query, top-k results, similarity scores, source file paths |
| **LLM Calls** | Model, messages/prompt, response, tokens, latency, tool calls |

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
