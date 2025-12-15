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
                import os
                run_id_str = str(run_id)
                retriever_data = self._retriever_starts.pop(run_id_str, {
                    "start_time": time.time(),
                    "query": "",
                })
                duration_ms = (time.time() - retriever_data["start_time"]) * 1000

                results = []
                for i, doc in enumerate(documents):
                    metadata = getattr(doc, 'metadata', {})
                    # Get source path and convert to absolute
                    source = metadata.get('source', metadata.get('file_path', ''))
                    abs_path = os.path.abspath(source) if source else ''
                    filename = os.path.basename(source) if source else ''

                    results.append({
                        "chunk_id": metadata.get('chunk_id', f"{filename}_{i}"),
                        "score": metadata.get('score', 0),
                        "text": doc.page_content[:500] if hasattr(doc, 'page_content') else str(doc)[:500],
                        "doc_id": filename,  # Use filename to match document
                        "page_number": metadata.get('page', metadata.get('page_label')),
                        "file_path": abs_path,
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
        import os
        store = self.store
        logged_sources = set()  # Track what we've already logged to avoid duplicates

        def log_documents_from_result(result, loader_instance=None, loader_name="unknown"):
            """Helper to log documents from loader results."""
            if not result:
                return

            docs_by_source = {}
            for doc in result:
                source = doc.metadata.get('source', 'unknown')
                if source not in docs_by_source:
                    docs_by_source[source] = []
                docs_by_source[source].append(doc)

            for source, docs in docs_by_source.items():
                # Skip if already logged this source
                if source in logged_sources:
                    continue
                logged_sources.add(source)

                # Convert to absolute path for file serving
                abs_path = os.path.abspath(source) if source != 'unknown' else source
                filename = os.path.basename(source) if source != 'unknown' else 'unknown'

                # Join page content with page breaks for better readability
                full_text = "\n\n--- PAGE BREAK ---\n\n".join([d.page_content for d in docs])

                store.log_document(
                    doc_id=filename,
                    filename=filename,
                    file_path=abs_path,
                    text_length=len(full_text),
                    num_pages=len(docs)
                )

                store.log_parsed(
                    doc_id=filename,
                    filename=filename,
                    text=full_text
                )
                print(f"[SourcemapR] Document loaded: {filename} ({len(docs)} pages, path: {abs_path})")

        # Patch PyPDFLoader
        try:
            from langchain_community.document_loaders import PyPDFLoader
            original_load = PyPDFLoader.load

            def patched_pypdf_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)
                log_documents_from_result(result, self_loader, "PyPDFLoader")
                return result

            PyPDFLoader.load = patched_pypdf_load
            self._original_handlers['PyPDFLoader.load'] = original_load
        except ImportError:
            pass

        # Patch PyPDFLoader.lazy_load (used by DirectoryLoader)
        try:
            from langchain_community.document_loaders import PyPDFLoader
            if hasattr(PyPDFLoader, 'lazy_load'):
                original_lazy_load = PyPDFLoader.lazy_load

                def patched_pypdf_lazy_load(self_loader, *args, **kwargs):
                    result = list(original_lazy_load(self_loader, *args, **kwargs))
                    log_documents_from_result(result, self_loader, "PyPDFLoader.lazy_load")
                    for doc in result:
                        yield doc

                PyPDFLoader.lazy_load = patched_pypdf_lazy_load
                self._original_handlers['PyPDFLoader.lazy_load'] = original_lazy_load
        except ImportError:
            pass

        # Patch DirectoryLoader
        try:
            from langchain_community.document_loaders import DirectoryLoader
            original_load = DirectoryLoader.load

            def patched_directory_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)
                log_documents_from_result(result, self_loader, "DirectoryLoader")
                return result

            DirectoryLoader.load = patched_directory_load
            self._original_handlers['DirectoryLoader.load'] = original_load
        except ImportError:
            pass

        # Patch TextLoader
        try:
            from langchain_community.document_loaders import TextLoader
            original_load = TextLoader.load

            def patched_text_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)
                log_documents_from_result(result, self_loader, "TextLoader")
                return result

            TextLoader.load = patched_text_load
            self._original_handlers['TextLoader.load'] = original_load
        except ImportError:
            pass

        # Patch UnstructuredFileLoader
        try:
            from langchain_community.document_loaders import UnstructuredFileLoader
            original_load = UnstructuredFileLoader.load

            def patched_unstructured_load(self_loader, *args, **kwargs):
                result = original_load(self_loader, *args, **kwargs)
                log_documents_from_result(result, self_loader, "UnstructuredFileLoader")
                return result

            UnstructuredFileLoader.load = patched_unstructured_load
            self._original_handlers['UnstructuredFileLoader.load'] = original_load
        except ImportError:
            pass

    def _patch_text_splitters(self):
        """Patch text splitters."""
        import os
        store = self.store

        def create_patched_split(original_split, splitter_name):
            """Create a patched split_documents method."""
            def patched_split(self_splitter, documents, *args, **kwargs):
                result = original_split(self_splitter, documents, *args, **kwargs)

                for i, doc in enumerate(result):
                    metadata = doc.metadata or {}
                    source = metadata.get('source', '')
                    abs_path = os.path.abspath(source) if source else ''
                    filename = os.path.basename(source) if source else ''

                    # Include file_path in metadata for chunk linking
                    chunk_metadata = dict(metadata)
                    chunk_metadata['file_path'] = abs_path

                    store.log_chunk(
                        chunk_id=f"{filename}_{i}",
                        doc_id=filename,
                        index=i,
                        text=doc.page_content,
                        page_number=metadata.get('page'),
                        metadata=chunk_metadata
                    )

                print(f"[SourcemapR] {splitter_name}: {len(result)} chunks created")
                return result
            return patched_split

        # Patch RecursiveCharacterTextSplitter from langchain_text_splitters
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            original = RecursiveCharacterTextSplitter.split_documents
            RecursiveCharacterTextSplitter.split_documents = create_patched_split(original, "RecursiveCharacterTextSplitter")
            self._original_handlers['langchain_text_splitters.RecursiveCharacterTextSplitter.split_documents'] = original
            print("[SourcemapR] Patched RecursiveCharacterTextSplitter (langchain_text_splitters)")
        except ImportError:
            pass

        # Also patch from langchain.text_splitter (legacy import path)
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter as LegacyRecursive
            # Only patch if it's a different class
            if not hasattr(LegacyRecursive.split_documents, '_sourcemapr_patched'):
                original = LegacyRecursive.split_documents
                patched = create_patched_split(original, "RecursiveCharacterTextSplitter")
                patched._sourcemapr_patched = True
                LegacyRecursive.split_documents = patched
                self._original_handlers['langchain.text_splitter.RecursiveCharacterTextSplitter.split_documents'] = original
        except ImportError:
            pass

        # Patch CharacterTextSplitter
        try:
            from langchain_text_splitters import CharacterTextSplitter
            original = CharacterTextSplitter.split_documents
            CharacterTextSplitter.split_documents = create_patched_split(original, "CharacterTextSplitter")
            self._original_handlers['langchain_text_splitters.CharacterTextSplitter.split_documents'] = original
        except ImportError:
            pass

        # Patch TokenTextSplitter
        try:
            from langchain_text_splitters import TokenTextSplitter
            original = TokenTextSplitter.split_documents
            TokenTextSplitter.split_documents = create_patched_split(original, "TokenTextSplitter")
            self._original_handlers['langchain_text_splitters.TokenTextSplitter.split_documents'] = original
        except ImportError:
            pass

        # Patch base TextSplitter class (split_documents is often inherited)
        try:
            from langchain_text_splitters.base import TextSplitter
            if not hasattr(TextSplitter.split_documents, '_sourcemapr_patched'):
                original = TextSplitter.split_documents
                patched = create_patched_split(original, "TextSplitter")
                patched._sourcemapr_patched = True
                TextSplitter.split_documents = patched
                self._original_handlers['langchain_text_splitters.base.TextSplitter.split_documents'] = original
                print("[SourcemapR] Patched TextSplitter base class")
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
                    elif cls_name == 'TextLoader':
                        from langchain_community.document_loaders import TextLoader
                        setattr(TextLoader, method_name, original)
                    elif cls_name == 'UnstructuredFileLoader':
                        from langchain_community.document_loaders import UnstructuredFileLoader
                        setattr(UnstructuredFileLoader, method_name, original)
                    elif cls_name == 'RecursiveCharacterTextSplitter':
                        from langchain_text_splitters import RecursiveCharacterTextSplitter
                        setattr(RecursiveCharacterTextSplitter, method_name, original)
            except Exception:
                pass

        self._original_handlers.clear()
        self._instrumented = False
