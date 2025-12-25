"""
LangChain provider for SourcemapR.

Instruments LangChain components:
- Document loaders (via monkey patching)
- Text splitters (via monkey patching)
- Retrievers (via callbacks)
- LLM calls (via callbacks)
"""

import time
import os
import threading
from typing import Optional, Dict, Any, List
from uuid import UUID

from sourcemapr.providers.base import BaseProvider
from sourcemapr.store import TraceStore


# Thread-local flag to skip callback logging when inside a patched pipeline retriever
_pipeline_context = threading.local()

def _in_pipeline_retriever():
    """Check if we're currently inside a patched pipeline retriever."""
    return getattr(_pipeline_context, 'active', False)

def _set_pipeline_context(active: bool):
    """Set whether we're inside a patched pipeline retriever."""
    _pipeline_context.active = active

def _get_pending_pipeline_queries():
    """Get set of queries that have pending pipeline results (skip callback logging for these)."""
    if not hasattr(_pipeline_context, 'pending_queries'):
        _pipeline_context.pending_queries = set()
    return _pipeline_context.pending_queries


# ============================================================================
# CALLBACK HANDLER
# ============================================================================

def _create_callback_handler(store: TraceStore, skip_llm_logging: bool = False):
    """Create LangChain callback handler.

    Args:
        store: TraceStore instance
        skip_llm_logging: If True, skip LLM call logging (use when OpenAI provider is also active)
    """
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult

    class SourcemapRLangChainHandler(BaseCallbackHandler):
        """Callback handler for LangChain LLM and retrieval events."""

        def __init__(self):
            super().__init__()
            self.store = store
            self._llm_starts: Dict[str, Dict] = {}
            self._retriever_starts: Dict[str, Dict] = {}
            self._skip_llm_logging = skip_llm_logging
        
        @property
        def always_verbose(self) -> bool:
            return True

        def on_llm_start(
            self,
            serialized: Dict[str, Any],
            prompts: List[str],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
        ) -> None:
            """Called when LLM starts."""
            if self._skip_llm_logging:
                return
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
            response,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
        ) -> None:
            """Called when LLM finishes."""
            if self._skip_llm_logging:
                return
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

            self.store.log_llm(
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
            """Called when LLM errors."""
            if self._skip_llm_logging:
                return
            run_id_str = str(run_id)
            llm_data = self._llm_starts.pop(run_id_str, {
                "start_time": time.time(),
                "model": "unknown",
            })
            duration_ms = (time.time() - llm_data["start_time"]) * 1000

            self.store.log_llm(
                model=llm_data.get("model", "unknown"),
                duration_ms=duration_ms,
                prompt="\n".join(llm_data.get("prompts", [])),
                error=str(error),
                provider="langchain"
            )

        def on_chat_model_start(
            self,
            serialized: Dict[str, Any],
            messages: List[List[Any]],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
        ) -> None:
            """Called when chat model starts."""
            if self._skip_llm_logging:
                return
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

        def on_retriever_start(
            self,
            serialized: Dict[str, Any],
            query: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
        ) -> None:
            """Called when retrieval starts."""
            # Skip if inside a patched pipeline retriever (it handles its own logging)
            if _in_pipeline_retriever():
                self._retriever_starts[str(run_id)] = {'skip': True}
                return
            # Skip patched pipeline retrievers (they handle their own logging)
            patched_retrievers = ['ContextualCompressionRetriever', 'MultiQueryRetriever', 'EnsembleRetriever']
            retriever_name = ''
            if serialized:
                retriever_name = serialized.get('name', serialized.get('id', [''])[-1] if serialized.get('id') else '')
            # Also check kwargs for retriever class name
            if not retriever_name and 'tags' in kwargs:
                retriever_name = str(kwargs.get('tags', []))
            if any(r in str(retriever_name) for r in patched_retrievers):
                self._retriever_starts[str(run_id)] = {'skip': True}
                return
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
            """Called when retrieval finishes."""
            # Skip if inside a patched pipeline retriever (it handles its own logging)
            if _in_pipeline_retriever():
                return
            run_id_str = str(run_id)
            retriever_data = self._retriever_starts.pop(run_id_str, {
                "start_time": time.time(),
                "query": "",
            })
            # Skip if this retriever was marked to skip (patched pipeline retriever)
            if retriever_data.get('skip'):
                return
            # Skip if query is pending from a pipeline (already logged by patched function)
            query = retriever_data.get("query", "")
            if query in _get_pending_pipeline_queries():
                _get_pending_pipeline_queries().discard(query)
                return
            duration_ms = (time.time() - retriever_data["start_time"]) * 1000

            results = []
            for i, doc in enumerate(documents):
                metadata = getattr(doc, 'metadata', {})
                source = metadata.get('source', metadata.get('file_path', ''))
                abs_path = os.path.abspath(source) if source else ''
                filename = os.path.basename(source) if source else ''

                # Extract character indices if available
                start_char_idx = metadata.get('start_index')
                end_char_idx = None
                if start_char_idx is not None and hasattr(doc, 'page_content'):
                    end_char_idx = start_char_idx + len(doc.page_content)

                result_data = {
                    "chunk_id": metadata.get('chunk_id', f"{filename}_{i}"),
                    "score": metadata.get('score', 0),
                    "text": doc.page_content[:500] if hasattr(doc, 'page_content') else str(doc)[:500],
                    "doc_id": filename,
                    "page_number": metadata.get('page', metadata.get('page_label')),
                    "file_path": abs_path,
                }

                if start_char_idx is not None:
                    result_data["start_char_idx"] = start_char_idx
                if end_char_idx is not None:
                    result_data["end_char_idx"] = end_char_idx

                results.append(result_data)

            self.store.log_retrieval(
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
            """Called when retrieval errors."""
            if _in_pipeline_retriever():
                return
            self._retriever_starts.pop(str(run_id), None)

    return SourcemapRLangChainHandler()


# ============================================================================
# PATCH HELPERS
# ============================================================================

class DocumentLoaderPatcher:
    """Helper class for patching document loaders."""
    
    def __init__(self, store: TraceStore, register_framework, original_handlers: Dict):
        self.store = store
        self.register_framework = register_framework
        self.original_handlers = original_handlers
        self.logged_sources = set()
        self._loading_lock = threading.local()
    
    def log_documents(self, result, loader_name="unknown"):
        """Log documents from loader results."""
        if not result:
            return
        self.register_framework()
        
        docs_by_source = {}
        for doc in result:
            source = doc.metadata.get('source', 'unknown')
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)
        
        for source, docs in docs_by_source.items():
            if source in self.logged_sources:
                continue
            self.logged_sources.add(source)
            
            abs_path = os.path.abspath(source) if source != 'unknown' else source
            filename = os.path.basename(source) if source != 'unknown' else 'unknown'
            full_text = "\n\n--- PAGE BREAK ---\n\n".join([d.page_content for d in docs])
            
            self.store.log_document(
                doc_id=filename,
                filename=filename,
                file_path=abs_path,
                text_length=len(full_text),
                num_pages=len(docs)
            )
            
            self.store.log_parsed(
                doc_id=filename,
                filename=filename,
                text=full_text
            )
            print(f"[SourcemapR] Document loaded: {filename} ({len(docs)} pages, path: {abs_path})")
    
    def patch_loader(self, loader_class, method_name: str = "load"):
        """Patch a document loader class."""
        try:
            original = getattr(loader_class, method_name)
            
            def patched(self_loader, *args, **kwargs):
                result = original(self_loader, *args, **kwargs)
                loader_name = self_loader.__class__.__name__
                self.log_documents(result, loader_name)
                return result
            
            setattr(loader_class, method_name, patched)
            key = f"{loader_class.__name__}.{method_name}"
            self.original_handlers[key] = original
            return True
        except (ImportError, AttributeError):
            return False
    
    def patch_lazy_loader(self, loader_class, method_name: str = "lazy_load"):
        """Patch a lazy loader (generator-based)."""
        try:
            if not hasattr(loader_class, method_name):
                return False
            original = getattr(loader_class, method_name)
            
            def patched(self_loader, *args, **kwargs):
                result = list(original(self_loader, *args, **kwargs))
                loader_name = self_loader.__class__.__name__
                self.log_documents(result, loader_name)
                for doc in result:
                    yield doc
            
            setattr(loader_class, method_name, patched)
            key = f"{loader_class.__name__}.{method_name}"
            self.original_handlers[key] = original
            return True
        except (ImportError, AttributeError):
            return False
    
    def patch_base_loader(self):
        """Patch BaseLoader to catch all loaders."""
        try:
            from langchain_core.document_loaders import BaseLoader
            
            if hasattr(BaseLoader.load, '_sourcemapr_patched'):
                return False
            
            original = BaseLoader.load
            
            def patched(self_loader, *args, **kwargs):
                # Prevent recursion
                if not hasattr(self._loading_lock, 'active'):
                    self._loading_lock.active = False
                if self._loading_lock.active:
                    return original(self_loader, *args, **kwargs)
                
                self._loading_lock.active = True
                try:
                    result = original(self_loader, *args, **kwargs)
                    loader_name = self_loader.__class__.__name__
                    self.log_documents(result, loader_name)
                    return result
                finally:
                    self._loading_lock.active = False
            
            patched._sourcemapr_patched = True
            BaseLoader.load = patched
            self.original_handlers['BaseLoader.load'] = original
            print("[SourcemapR] Patched BaseLoader (all document loaders)")
            return True
        except ImportError:
            return False


# ============================================================================
# MAIN PROVIDER
# ============================================================================

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
        """Install instrumentation hooks."""
        if self._instrumented:
            return True
        
        if not self.is_available():
            return False
        
        try:
            self._setup_callbacks()
            self._patch_document_loaders()
            self._patch_text_splitters()
            self._patch_vector_store_retriever()
            # Advanced retriever patches
            self._patch_contextual_compression_retriever()
            self._patch_multi_query_retriever()
            self._patch_ensemble_retriever()
            self._instrumented = True
            print("[SourcemapR] LangChain provider enabled")
            return True
        except Exception as e:
            print(f"[SourcemapR] LangChain provider error: {e}")
            return False
    
    def get_callback_handler(self):
        """Get the callback handler for use in LangChain chains."""
        return self._callback_handler
    
    # ========================================================================
    # CALLBACK SETUP
    # ========================================================================
    
    def _setup_callbacks(self):
        """Set up LangChain callback handler."""
        # Skip LLM logging if OpenAI provider is available (to avoid duplicates)
        skip_llm = self._check_openai_available()
        self._callback_handler = _create_callback_handler(self.store, skip_llm_logging=skip_llm)
        if skip_llm:
            print("[SourcemapR] LangChain: Skipping LLM logging (OpenAI provider active)")

    def _check_openai_available(self) -> bool:
        """Check if OpenAI is available and will be instrumented."""
        try:
            import openai
            return hasattr(openai, 'OpenAI')
        except ImportError:
            return False
    
    # ========================================================================
    # MONKEY PATCHING
    # ========================================================================
    
    def _patch_document_loaders(self):
        """Patch document loaders to track document loading."""
        patcher = DocumentLoaderPatcher(
            self.store,
            self._register_framework,
            self._original_handlers
        )
        
        # Patch specific loaders
        try:
            from langchain_community.document_loaders import (
                PyPDFLoader, DirectoryLoader, TextLoader, UnstructuredFileLoader
            )
            patcher.patch_loader(PyPDFLoader, "load")
            patcher.patch_lazy_loader(PyPDFLoader, "lazy_load")
            patcher.patch_loader(DirectoryLoader, "load")
            patcher.patch_loader(TextLoader, "load")
            patcher.patch_loader(UnstructuredFileLoader, "load")
        except ImportError:
            pass
        
        # Patch base loader to catch all others (including HTML loaders)
        patcher.patch_base_loader()
    
    def _patch_vector_store_retriever(self):
        """Patch VectorStoreRetriever to inject scores into document metadata."""
        try:
            from langchain_core.vectorstores import VectorStoreRetriever

            if hasattr(VectorStoreRetriever._get_relevant_documents, '_sourcemapr_patched'):
                return

            original_get_docs = VectorStoreRetriever._get_relevant_documents

            def patched_get_docs(self_retriever, query, *, run_manager=None):
                # Try to get documents with scores
                vectorstore = self_retriever.vectorstore
                k = self_retriever.search_kwargs.get('k', 4)

                try:
                    # Use similarity_search_with_score if available
                    if hasattr(vectorstore, 'similarity_search_with_score'):
                        docs_and_scores = vectorstore.similarity_search_with_score(
                            query, k=k, **{kk: vv for kk, vv in self_retriever.search_kwargs.items() if kk != 'k'}
                        )
                        # Inject scores into metadata
                        docs = []
                        for doc, score in docs_and_scores:
                            if not doc.metadata:
                                doc.metadata = {}
                            doc.metadata['score'] = float(score)
                            docs.append(doc)
                        return docs
                except Exception:
                    pass

                # Fallback to original method
                return original_get_docs(self_retriever, query, run_manager=run_manager)

            patched_get_docs._sourcemapr_patched = True
            VectorStoreRetriever._get_relevant_documents = patched_get_docs
            self._original_handlers['VectorStoreRetriever._get_relevant_documents'] = original_get_docs
            print("[SourcemapR] Patched VectorStoreRetriever (scores will be captured)")
        except ImportError:
            pass

    def _patch_contextual_compression_retriever(self):
        """Patch ContextualCompressionRetriever to track reranking/compression stages."""
        try:
            from langchain.retrievers import ContextualCompressionRetriever
            import uuid

            if hasattr(ContextualCompressionRetriever._get_relevant_documents, '_sourcemapr_patched'):
                return

            original_get_docs = ContextualCompressionRetriever._get_relevant_documents

            def patched_get_docs(self_retriever, query, *, run_manager=None):
                import time
                start_time = time.time()
                pipeline_id = str(uuid.uuid4())[:12]
                stage_order = 1

                # Set context to skip callback logging (we handle it here)
                _set_pipeline_context(True)

                try:
                    # Stage 1: Base retrieval
                    base_start = time.time()
                    base_docs = self_retriever.base_retriever.get_relevant_documents(query)
                    base_duration = (time.time() - base_start) * 1000

                    base_chunks = []
                    for i, doc in enumerate(base_docs):
                        source = doc.metadata.get('source', 'unknown')
                        base_chunks.append({
                            'chunk_id': doc.metadata.get('chunk_id', f"chunk_{i}"),
                            'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                            'text': doc.page_content[:500],
                            'input_rank': i + 1,
                            'output_rank': i + 1,
                            'input_score': doc.metadata.get('score', 0),
                            'output_score': doc.metadata.get('score', 0),
                            'source': 'base_retriever',
                            'status': 'kept',
                        })

                    # Log base retrieval stage
                    self.store._send_queue.put({
                        'type': 'pipeline_stage',
                        'data': {
                            'stage_id': f"{pipeline_id}_retrieval",
                            'pipeline_id': pipeline_id,
                            'stage_type': 'retrieval',
                            'stage_name': self_retriever.base_retriever.__class__.__name__,
                            'stage_order': stage_order,
                            'input_count': 0,
                            'output_count': len(base_docs),
                            'duration_ms': base_duration,
                            'metadata': {'query': query},
                            'chunks': base_chunks,
                        }
                    })
                    stage_order += 1

                    # Stage 2: Compression/Reranking
                    compress_start = time.time()
                    compressed_docs = self_retriever.base_compressor.compress_documents(base_docs, query)
                    compress_duration = (time.time() - compress_start) * 1000

                    # Track which chunks survived and their new scores/ranks
                    compressed_chunks = []
                    survived_ids = set()
                    for i, doc in enumerate(compressed_docs):
                        chunk_id = doc.metadata.get('chunk_id', f"chunk_{i}")
                        survived_ids.add(chunk_id)
                        source = doc.metadata.get('source', 'unknown')
                        compressed_chunks.append({
                            'chunk_id': chunk_id,
                            'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                            'text': doc.page_content[:500],
                            'input_rank': next((j+1 for j, c in enumerate(base_chunks) if c['chunk_id'] == chunk_id), None),
                            'output_rank': i + 1,
                            'input_score': next((c['input_score'] for c in base_chunks if c['chunk_id'] == chunk_id), 0),
                            'output_score': doc.metadata.get('relevance_score', doc.metadata.get('score', 0)),
                            'source': 'compressor',
                            'status': 'kept',
                        })

                    # Mark filtered chunks
                    for chunk in base_chunks:
                        if chunk['chunk_id'] not in survived_ids:
                            compressed_chunks.append({
                                **chunk,
                                'output_rank': None,
                                'status': 'filtered',
                            })

                    # Log compression stage
                    compressor_name = self_retriever.base_compressor.__class__.__name__
                    self.store._send_queue.put({
                        'type': 'pipeline_stage',
                        'data': {
                            'stage_id': f"{pipeline_id}_compression",
                            'pipeline_id': pipeline_id,
                            'stage_type': 'reranking' if 'rerank' in compressor_name.lower() else 'compression',
                            'stage_name': compressor_name,
                            'stage_order': stage_order,
                            'input_count': len(base_docs),
                            'output_count': len(compressed_docs),
                            'duration_ms': compress_duration,
                            'metadata': {'compression_ratio': len(compressed_docs) / max(len(base_docs), 1)},
                            'chunks': compressed_chunks,
                        }
                    })

                    total_duration = (time.time() - start_time) * 1000

                    # Generate retrieval_id to link retrieval and pipeline
                    retrieval_id = f"ret_{pipeline_id}"

                    # Send pipeline record (links stages together and to retrieval)
                    self.store._send_queue.put({
                        'type': 'pipeline',
                        'data': {
                            'pipeline_id': pipeline_id,
                            'query': query,
                            'total_duration_ms': total_duration,
                            'num_stages': stage_order,
                            'retrieval_id': retrieval_id,
                        }
                    })

                    # Build final results for retrieval event
                    final_results = []
                    for i, doc in enumerate(compressed_docs):
                        metadata = getattr(doc, 'metadata', {})
                        source = metadata.get('source', 'unknown')
                        final_results.append({
                            'chunk_id': metadata.get('chunk_id', f"chunk_{i}"),
                            'score': metadata.get('relevance_score', metadata.get('score', 0)),
                            'text': doc.page_content[:500] if hasattr(doc, 'page_content') else '',
                            'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                            'page_number': metadata.get('page', metadata.get('page_label')),
                        })

                    # Mark query as pending so callback skips it
                    _get_pending_pipeline_queries().add(query)

                    # Send retrieval event with final compressed results
                    self.store.log_retrieval(
                        query=query,
                        results=final_results,
                        duration_ms=total_duration,
                        retrieval_id=retrieval_id,
                    )

                    print(f"[SourcemapR] ContextualCompression: {len(base_docs)} → {len(compressed_docs)} docs ({total_duration:.0f}ms)")

                    return list(compressed_docs)
                finally:
                    # Always reset the pipeline context
                    _set_pipeline_context(False)

            patched_get_docs._sourcemapr_patched = True
            ContextualCompressionRetriever._get_relevant_documents = patched_get_docs
            self._original_handlers['ContextualCompressionRetriever._get_relevant_documents'] = original_get_docs
            print("[SourcemapR] Patched ContextualCompressionRetriever (reranking tracked)")
        except ImportError:
            pass

    def _patch_multi_query_retriever(self):
        """Patch MultiQueryRetriever to track query expansion stages."""
        try:
            from langchain.retrievers.multi_query import MultiQueryRetriever
            import uuid

            if hasattr(MultiQueryRetriever._get_relevant_documents, '_sourcemapr_patched'):
                return

            original_get_docs = MultiQueryRetriever._get_relevant_documents

            def patched_get_docs(self_retriever, query, *, run_manager=None):
                import time
                start_time = time.time()
                pipeline_id = str(uuid.uuid4())[:12]

                # Generate query variants
                expand_start = time.time()
                queries = self_retriever.generate_queries(query, run_manager)
                expand_duration = (time.time() - expand_start) * 1000

                # Log query expansion stage
                self.store._send_queue.put({
                    'type': 'pipeline_stage',
                    'data': {
                        'stage_id': f"{pipeline_id}_expansion",
                        'pipeline_id': pipeline_id,
                        'stage_type': 'query_expansion',
                        'stage_name': 'MultiQueryRetriever',
                        'stage_order': 1,
                        'input_count': 1,
                        'output_count': len(queries),
                        'duration_ms': expand_duration,
                        'metadata': {
                            'original_query': query,
                            'generated_queries': queries,
                        },
                        'chunks': [],
                    }
                })

                # Retrieve for each query
                retrieve_start = time.time()
                all_docs = []
                docs_by_query = {}
                for i, q in enumerate(queries):
                    docs = self_retriever.retriever.get_relevant_documents(q)
                    docs_by_query[q] = docs
                    all_docs.extend(docs)
                retrieve_duration = (time.time() - retrieve_start) * 1000

                # Deduplicate
                unique_docs = self_retriever.unique_union(all_docs)

                # Track chunks from each query
                retrieval_chunks = []
                seen_chunks = set()
                for q, docs in docs_by_query.items():
                    for i, doc in enumerate(docs):
                        source = doc.metadata.get('source', 'unknown')
                        chunk_id = doc.metadata.get('chunk_id', f"{source}_{hash(doc.page_content) % 10000}")
                        if chunk_id not in seen_chunks:
                            seen_chunks.add(chunk_id)
                            retrieval_chunks.append({
                                'chunk_id': chunk_id,
                                'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                                'text': doc.page_content[:500],
                                'input_rank': i + 1,
                                'output_rank': None,  # Set after dedup
                                'input_score': doc.metadata.get('score', 0),
                                'output_score': doc.metadata.get('score', 0),
                                'source': f"query_{queries.index(q)+1}",
                                'status': 'kept',
                            })

                # Update output ranks for kept chunks
                for i, doc in enumerate(unique_docs):
                    chunk_id = doc.metadata.get('chunk_id', f"{doc.metadata.get('source', 'unknown')}_{hash(doc.page_content) % 10000}")
                    for chunk in retrieval_chunks:
                        if chunk['chunk_id'] == chunk_id and chunk['output_rank'] is None:
                            chunk['output_rank'] = i + 1
                            break

                # Log retrieval stage
                self.store._send_queue.put({
                    'type': 'pipeline_stage',
                    'data': {
                        'stage_id': f"{pipeline_id}_retrieval",
                        'pipeline_id': pipeline_id,
                        'stage_type': 'retrieval',
                        'stage_name': 'MultiQueryRetrieval',
                        'stage_order': 2,
                        'input_count': len(queries),
                        'output_count': len(unique_docs),
                        'duration_ms': retrieve_duration,
                        'metadata': {
                            'total_retrieved': len(all_docs),
                            'after_dedup': len(unique_docs),
                            'dedup_ratio': len(unique_docs) / max(len(all_docs), 1),
                        },
                        'chunks': retrieval_chunks,
                    }
                })

                total_duration = (time.time() - start_time) * 1000

                # Generate retrieval_id to link retrieval and pipeline
                retrieval_id = f"ret_{pipeline_id}"

                # Send pipeline record
                self.store._send_queue.put({
                    'type': 'pipeline',
                    'data': {
                        'pipeline_id': pipeline_id,
                        'query': query,
                        'total_duration_ms': total_duration,
                        'num_stages': 2,
                        'retrieval_id': retrieval_id,
                    }
                })

                # Build final results for retrieval event
                final_results = []
                for i, doc in enumerate(unique_docs):
                    metadata = getattr(doc, 'metadata', {})
                    source = metadata.get('source', 'unknown')
                    final_results.append({
                        'chunk_id': metadata.get('chunk_id', f"chunk_{i}"),
                        'score': metadata.get('score', 0),
                        'text': doc.page_content[:500] if hasattr(doc, 'page_content') else '',
                        'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                        'page_number': metadata.get('page', metadata.get('page_label')),
                    })

                # Send retrieval event
                self.store.log_retrieval(
                    query=query,
                    results=final_results,
                    duration_ms=total_duration,
                    retrieval_id=retrieval_id,
                )

                print(f"[SourcemapR] MultiQuery: {len(queries)} queries → {len(all_docs)} docs → {len(unique_docs)} unique ({total_duration:.0f}ms)")

                return unique_docs

            patched_get_docs._sourcemapr_patched = True
            MultiQueryRetriever._get_relevant_documents = patched_get_docs
            self._original_handlers['MultiQueryRetriever._get_relevant_documents'] = original_get_docs
            print("[SourcemapR] Patched MultiQueryRetriever (query expansion tracked)")
        except ImportError:
            pass

    def _patch_ensemble_retriever(self):
        """Patch EnsembleRetriever to track hybrid search stages."""
        try:
            from langchain.retrievers import EnsembleRetriever
            import uuid

            if hasattr(EnsembleRetriever._get_relevant_documents, '_sourcemapr_patched'):
                return

            original_get_docs = EnsembleRetriever._get_relevant_documents

            def patched_get_docs(self_retriever, query, *, run_manager=None):
                import time
                start_time = time.time()
                pipeline_id = str(uuid.uuid4())[:12]

                # Get docs from each retriever
                all_chunks = []
                retriever_results = []
                for i, retriever in enumerate(self_retriever.retrievers):
                    ret_start = time.time()
                    docs = retriever.get_relevant_documents(query)
                    ret_duration = (time.time() - ret_start) * 1000
                    retriever_name = retriever.__class__.__name__
                    weight = self_retriever.weights[i] if self_retriever.weights else 1.0 / len(self_retriever.retrievers)

                    retriever_results.append({
                        'name': retriever_name,
                        'docs': docs,
                        'duration_ms': ret_duration,
                        'weight': weight,
                    })

                    for j, doc in enumerate(docs):
                        source = doc.metadata.get('source', 'unknown')
                        chunk_id = doc.metadata.get('chunk_id', f"{source}_{hash(doc.page_content) % 10000}")
                        all_chunks.append({
                            'chunk_id': chunk_id,
                            'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                            'text': doc.page_content[:500],
                            'input_rank': j + 1,
                            'output_rank': None,
                            'input_score': doc.metadata.get('score', 0),
                            'output_score': None,
                            'source': retriever_name,
                            'status': 'kept',
                        })

                # Log individual retriever stages
                for i, result in enumerate(retriever_results):
                    self.store._send_queue.put({
                        'type': 'pipeline_stage',
                        'data': {
                            'stage_id': f"{pipeline_id}_retriever_{i}",
                            'pipeline_id': pipeline_id,
                            'stage_type': 'retrieval',
                            'stage_name': result['name'],
                            'stage_order': i + 1,
                            'input_count': 0,
                            'output_count': len(result['docs']),
                            'duration_ms': result['duration_ms'],
                            'metadata': {'weight': result['weight']},
                            'chunks': [c for c in all_chunks if c['source'] == result['name']],
                        }
                    })

                # Call original to get merged results
                merge_start = time.time()
                result_docs = original_get_docs(self_retriever, query, run_manager=run_manager)
                merge_duration = (time.time() - merge_start) * 1000

                # Update output ranks and scores
                for i, doc in enumerate(result_docs):
                    chunk_id = doc.metadata.get('chunk_id', f"{doc.metadata.get('source', 'unknown')}_{hash(doc.page_content) % 10000}")
                    for chunk in all_chunks:
                        if chunk['chunk_id'] == chunk_id and chunk['output_rank'] is None:
                            chunk['output_rank'] = i + 1
                            chunk['output_score'] = doc.metadata.get('score', chunk['input_score'])
                            break

                # Log merge stage
                self.store._send_queue.put({
                    'type': 'pipeline_stage',
                    'data': {
                        'stage_id': f"{pipeline_id}_merge",
                        'pipeline_id': pipeline_id,
                        'stage_type': 'merge',
                        'stage_name': 'EnsembleMerge',
                        'stage_order': len(retriever_results) + 1,
                        'input_count': sum(len(r['docs']) for r in retriever_results),
                        'output_count': len(result_docs),
                        'duration_ms': merge_duration,
                        'metadata': {
                            'weights': [r['weight'] for r in retriever_results],
                            'retriever_names': [r['name'] for r in retriever_results],
                        },
                        'chunks': all_chunks,
                    }
                })

                total_duration = (time.time() - start_time) * 1000
                total_input = sum(len(r['docs']) for r in retriever_results)

                # Generate retrieval_id to link retrieval and pipeline
                retrieval_id = f"ret_{pipeline_id}"

                # Send pipeline record
                self.store._send_queue.put({
                    'type': 'pipeline',
                    'data': {
                        'pipeline_id': pipeline_id,
                        'query': query,
                        'total_duration_ms': total_duration,
                        'num_stages': len(retriever_results) + 1,  # retrievers + merge
                        'retrieval_id': retrieval_id,
                    }
                })

                # Build final results for retrieval event
                final_results = []
                for i, doc in enumerate(result_docs):
                    metadata = getattr(doc, 'metadata', {})
                    source = metadata.get('source', 'unknown')
                    final_results.append({
                        'chunk_id': metadata.get('chunk_id', f"chunk_{i}"),
                        'score': metadata.get('score', 0),
                        'text': doc.page_content[:500] if hasattr(doc, 'page_content') else '',
                        'doc_id': os.path.basename(source) if source != 'unknown' else 'unknown',
                        'page_number': metadata.get('page', metadata.get('page_label')),
                    })

                # Send retrieval event
                self.store.log_retrieval(
                    query=query,
                    results=final_results,
                    duration_ms=total_duration,
                    retrieval_id=retrieval_id,
                )

                print(f"[SourcemapR] Ensemble: {len(self_retriever.retrievers)} retrievers → {total_input} docs → {len(result_docs)} merged ({total_duration:.0f}ms)")

                return result_docs

            patched_get_docs._sourcemapr_patched = True
            EnsembleRetriever._get_relevant_documents = patched_get_docs
            self._original_handlers['EnsembleRetriever._get_relevant_documents'] = original_get_docs
            print("[SourcemapR] Patched EnsembleRetriever (hybrid search tracked)")
        except ImportError:
            pass

    def _patch_text_splitters(self):
        """Patch text splitters to track chunking."""
        try:
            from langchain_text_splitters.base import TextSplitter
            
            if hasattr(TextSplitter.split_documents, '_sourcemapr_patched'):
                return
            
            original = TextSplitter.split_documents
            
            def patched_split(self_splitter, documents, *args, **kwargs):
                result = original(self_splitter, documents, *args, **kwargs)
                splitter_name = self_splitter.__class__.__name__
                
                chunks_by_source = {}
                for i, doc in enumerate(result):
                    metadata = doc.metadata or {}
                    source = metadata.get('source', '')
                    abs_path = os.path.abspath(source) if source else ''
                    filename = os.path.basename(source) if source else ''
                    
                    # Extract character indices
                    start_char_idx = metadata.get('start_index')
                    end_char_idx = None
                    if start_char_idx is not None:
                        end_char_idx = start_char_idx + len(doc.page_content)
                    
                    # Determine page number
                    page_from_meta = metadata.get('page')
                    if page_from_meta is not None:
                        page_number = page_from_meta + 1 if isinstance(page_from_meta, int) else page_from_meta
                    else:
                        page_number = 1
                    
                    chunk_metadata = dict(metadata)
                    chunk_metadata['file_path'] = abs_path
                    
                    # Collect chunks by source
                    if filename:
                        if filename not in chunks_by_source:
                            chunks_by_source[filename] = {
                                'file_path': abs_path,
                                'chunks': []
                            }
                        chunks_by_source[filename]['chunks'].append({
                            'index': i,
                            'text': doc.page_content,
                            'page_number': page_number,
                            'start_char_idx': start_char_idx
                        })
                    
                    self.store.log_chunk(
                        chunk_id=f"{filename}_{i}",
                        doc_id=filename,
                        index=i,
                        text=doc.page_content,
                        page_number=page_number,
                        start_char_idx=start_char_idx,
                        end_char_idx=end_char_idx,
                        metadata=chunk_metadata
                    )
                
                # Build parsed text for HTML files
                for filename, data in chunks_by_source.items():
                    file_path = data['file_path']
                    file_ext = file_path.lower().split('.')[-1] if file_path else ''
                    
                    if file_ext in ('htm', 'html', 'xhtml') and data['chunks']:
                        sorted_chunks = sorted(data['chunks'], key=lambda x: x.get('start_char_idx') or x['index'])
                        
                        pages_content = {}
                        for chunk in sorted_chunks:
                            page_num = chunk.get('page_number') or 1
                            if page_num not in pages_content:
                                pages_content[page_num] = []
                            pages_content[page_num].append(chunk['text'])
                        
                        if len(pages_content) > 1:
                            parsed_parts = []
                            for page_num in sorted(pages_content.keys()):
                                parsed_parts.append('\n\n'.join(pages_content[page_num]))
                            parsed_text = '\n\n--- PAGE BREAK ---\n\n'.join(parsed_parts)
                        else:
                            parsed_text = '\n\n'.join([c['text'] for c in sorted_chunks])
                        
                        self.store.log_parsed(
                            doc_id=filename,
                            filename=filename,
                            text=parsed_text
                        )
                        print(f"[SourcemapR] Built parsed text for HTML: {filename} ({len(data['chunks'])} chunks)")
                
                print(f"[SourcemapR] {splitter_name}: {len(result)} chunks created")
                return result
            
            patched_split._sourcemapr_patched = True
            TextSplitter.split_documents = patched_split
            self._original_handlers['langchain_text_splitters.base.TextSplitter.split_documents'] = original
            print("[SourcemapR] Patched TextSplitter base class (all splitters)")
        except ImportError:
            pass
    
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
            except Exception:
                pass
        
        self._original_handlers.clear()
        self._instrumented = False
