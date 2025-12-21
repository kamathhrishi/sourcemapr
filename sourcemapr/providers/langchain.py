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


# ============================================================================
# CALLBACK HANDLER
# ============================================================================

def _create_callback_handler(store: TraceStore):
    """Create LangChain callback handler."""
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    
    class SourcemapRLangChainHandler(BaseCallbackHandler):
        """Callback handler for LangChain LLM and retrieval events."""
        
        def __init__(self):
            super().__init__()
            self.store = store
            self._llm_starts: Dict[str, Dict] = {}
            self._retriever_starts: Dict[str, Dict] = {}
        
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
            run_id_str = str(run_id)
            retriever_data = self._retriever_starts.pop(run_id_str, {
                "start_time": time.time(),
                "query": "",
            })
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
        self._callback_handler = _create_callback_handler(self.store)
    
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
