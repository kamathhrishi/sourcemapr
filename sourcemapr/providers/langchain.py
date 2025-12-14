"""
LangChain provider for SourcemapR.

Instruments LangChain components:
- Document loaders
- Text splitters
- Retrievers
- LLM calls via callbacks
"""

import time
from typing import Optional, Dict, Any, List
from uuid import UUID

from sourcemapr.providers.base import BaseProvider
from sourcemapr.store import TraceStore


class LangChainProvider(BaseProvider):
    """LangChain instrumentation provider."""

    name = "langchain"

    def __init__(self, store: TraceStore):
        super().__init__(store)
        self._callback_handler = None

    def is_available(self) -> bool:
        try:
            import langchain
            return True
        except ImportError:
            return False

    def instrument(self) -> bool:
        if self._instrumented:
            return True

        if not self.is_available():
            return False

        try:
            self._setup_callbacks()
            self._patch_document_loaders()
            self._patch_text_splitters()
            self._patch_retrievers()
            self._instrumented = True
            print("[SourcemapR] LangChain provider enabled")
            return True
        except Exception as e:
            print(f"[SourcemapR] LangChain provider error: {e}")
            return False

    def get_callback_handler(self):
        """Get the callback handler for use in LangChain chains."""
        return self._callback_handler

    def _setup_callbacks(self):
        """Set up LangChain callback handler."""
        from langchain_core.callbacks import BaseCallbackHandler
        from langchain_core.outputs import LLMResult

        store = self.store

        class SourcemapRLangChainHandler(BaseCallbackHandler):
            """Callback handler for LangChain."""

            def __init__(self):
                self._llm_starts: Dict[str, Dict] = {}
                self._retriever_starts: Dict[str, Dict] = {}
                self._chain_starts: Dict[str, Dict] = {}

            @property
            def always_verbose(self) -> bool:
                return True

            # LLM callbacks
            def on_llm_start(
                self,
                serialized: Dict[str, Any],
                prompts: List[str],
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                model = serialized.get('name', serialized.get('id', ['unknown'])[-1])
                self._llm_starts[str(run_id)] = {
                    "start_time": time.time(),
                    "model": model,
                    "prompts": prompts,
                    "serialized": serialized,
                }
                print(f"[SourcemapR] LLM call started: {model}")

            def on_llm_end(
                self,
                response: LLMResult,
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                run_id_str = str(run_id)
                llm_data = self._llm_starts.pop(run_id_str, {
                    "start_time": time.time(),
                    "model": "unknown",
                    "prompts": [],
                })
                duration_ms = (time.time() - llm_data["start_time"]) * 1000

                response_text = ""
                if response.generations and response.generations[0]:
                    response_text = response.generations[0][0].text

                # Extract token usage
                prompt_tokens = None
                completion_tokens = None
                total_tokens = None

                if hasattr(response, 'llm_output') and response.llm_output:
                    usage = response.llm_output.get('token_usage', {})
                    prompt_tokens = usage.get('prompt_tokens')
                    completion_tokens = usage.get('completion_tokens')
                    total_tokens = usage.get('total_tokens')

                store.log_llm(
                    model=llm_data.get("model", "unknown"),
                    duration_ms=duration_ms,
                    prompt="\n".join(llm_data.get("prompts", [])),
                    response=response_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    provider="langchain"
                )
                print(f"[SourcemapR] LLM call logged: {llm_data.get('model', 'unknown')} ({duration_ms:.0f}ms)")

            def on_llm_error(
                self,
                error: Exception,
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                run_id_str = str(run_id)
                llm_data = self._llm_starts.pop(run_id_str, {
                    "start_time": time.time(),
                    "model": "unknown",
                })
                duration_ms = (time.time() - llm_data["start_time"]) * 1000

                store.log_llm(
                    model=llm_data.get("model", "unknown"),
                    duration_ms=duration_ms,
                    prompt="\n".join(llm_data.get("prompts", [])),
                    error=str(error),
                    provider="langchain"
                )

            # Chat model callbacks
            def on_chat_model_start(
                self,
                serialized: Dict[str, Any],
                messages: List[List[Any]],
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                model = serialized.get('name', serialized.get('id', ['unknown'])[-1])

                # Format messages
                formatted_messages = []
                for msg_list in messages:
                    for msg in msg_list:
                        if hasattr(msg, 'type') and hasattr(msg, 'content'):
                            formatted_messages.append({
                                'role': msg.type,
                                'content': msg.content
                            })

                self._llm_starts[str(run_id)] = {
                    "start_time": time.time(),
                    "model": model,
                    "messages": formatted_messages,
                    "serialized": serialized,
                }
                print(f"[SourcemapR] Chat model started: {model}")

            # Retriever callbacks
            def on_retriever_start(
                self,
                serialized: Dict[str, Any],
                query: str,
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                self._retriever_starts[str(run_id)] = {
                    "start_time": time.time(),
                    "query": query,
                }
                print(f"[SourcemapR] Retrieval started: {query[:50]}...")

            def on_retriever_end(
                self,
                documents: List[Any],
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                run_id_str = str(run_id)
                retriever_data = self._retriever_starts.pop(run_id_str, {
                    "start_time": time.time(),
                    "query": "",
                })
                duration_ms = (time.time() - retriever_data["start_time"]) * 1000

                results = []
                for i, doc in enumerate(documents):
                    metadata = getattr(doc, 'metadata', {})
                    results.append({
                        "chunk_id": metadata.get('chunk_id', str(i)),
                        "score": metadata.get('score', 0),
                        "text": doc.page_content[:500] if hasattr(doc, 'page_content') else str(doc)[:500],
                        "doc_id": metadata.get('source', metadata.get('file_name', '')),
                        "page_number": metadata.get('page', metadata.get('page_label')),
                        "file_path": metadata.get('file_path', ''),
                    })

                store.log_retrieval(
                    query=retriever_data.get("query", ""),
                    results=results,
                    duration_ms=duration_ms,
                )
                print(f"[SourcemapR] Retrieval completed: {len(documents)} documents")

            def on_retriever_error(
                self,
                error: Exception,
                *,
                run_id: UUID,
                parent_run_id: Optional[UUID] = None,
                **kwargs: Any,
            ) -> None:
                self._retriever_starts.pop(str(run_id), None)

        self._callback_handler = SourcemapRLangChainHandler()

    def _patch_document_loaders(self):
        """Patch common document loaders."""
        store = self.store

        # Patch PyPDFLoader
        try:
            from langchain_community.document_loaders import PyPDFLoader
            original_load = PyPDFLoader.load

            def patched_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)

                filename = getattr(self_loader, 'file_path', 'unknown')
                if isinstance(filename, str):
                    filename = filename.split('/')[-1].split('\\')[-1]

                full_text = "\n\n".join([doc.page_content for doc in result])

                store.log_document(
                    doc_id=filename,
                    filename=filename,
                    file_path=getattr(self_loader, 'file_path', ''),
                    text_length=len(full_text),
                    num_pages=len(result)
                )

                store.log_parsed(
                    doc_id=filename,
                    filename=filename,
                    text=full_text
                )

                return result

            PyPDFLoader.load = patched_load
            self._original_handlers['PyPDFLoader.load'] = original_load
        except ImportError:
            pass

        # Patch DirectoryLoader
        try:
            from langchain_community.document_loaders import DirectoryLoader
            original_load = DirectoryLoader.load

            def patched_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)

                docs_by_source = {}
                for doc in result:
                    source = doc.metadata.get('source', 'unknown')
                    if source not in docs_by_source:
                        docs_by_source[source] = []
                    docs_by_source[source].append(doc)

                for source, docs in docs_by_source.items():
                    filename = source.split('/')[-1].split('\\')[-1]
                    full_text = "\n\n".join([d.page_content for d in docs])

                    store.log_document(
                        doc_id=filename,
                        filename=filename,
                        file_path=source,
                        text_length=len(full_text),
                        num_pages=len(docs)
                    )

                    store.log_parsed(
                        doc_id=filename,
                        filename=filename,
                        text=full_text
                    )

                return result

            DirectoryLoader.load = patched_load
            self._original_handlers['DirectoryLoader.load'] = original_load
        except ImportError:
            pass

    def _patch_text_splitters(self):
        """Patch text splitters."""
        store = self.store

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            original_split = RecursiveCharacterTextSplitter.split_documents

            def patched_split(self_splitter, documents, *args, **kwargs):
                result = original_split(self_splitter, documents, *args, **kwargs)

                for i, doc in enumerate(result):
                    metadata = doc.metadata or {}
                    source = metadata.get('source', '')
                    filename = source.split('/')[-1].split('\\')[-1] if source else ''

                    store.log_chunk(
                        chunk_id=f"{filename}_{i}",
                        doc_id=filename,
                        index=i,
                        text=doc.page_content,
                        page_number=metadata.get('page'),
                        metadata=metadata
                    )

                return result

            RecursiveCharacterTextSplitter.split_documents = patched_split
            self._original_handlers['RecursiveCharacterTextSplitter.split_documents'] = original_split
        except ImportError:
            pass

    def _patch_retrievers(self):
        """Patch retrievers - handled via callbacks."""
        pass  # Retrieval is handled via callbacks

    def uninstrument(self) -> None:
        """Restore original methods."""
        for name, original in self._original_handlers.items():
            try:
                parts = name.split('.')
                if len(parts) == 2:
                    cls_name, method_name = parts
                    if cls_name == 'PyPDFLoader':
                        from langchain_community.document_loaders import PyPDFLoader
                        setattr(PyPDFLoader, method_name, original)
                    elif cls_name == 'DirectoryLoader':
                        from langchain_community.document_loaders import DirectoryLoader
                        setattr(DirectoryLoader, method_name, original)
                    elif cls_name == 'RecursiveCharacterTextSplitter':
                        from langchain_text_splitters import RecursiveCharacterTextSplitter
                        setattr(RecursiveCharacterTextSplitter, method_name, original)
            except Exception:
                pass

        self._original_handlers.clear()
        self._instrumented = False
