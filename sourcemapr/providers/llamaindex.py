"""
LlamaIndex provider for SourcemapR.

Instruments LlamaIndex components:
- SimpleDirectoryReader (document loading via monkey patching)
- FlatReader (document loading via monkey patching)
- NodeParser (chunking via monkey patching)
- VectorStoreIndex (indexing via monkey patching)
- Query callbacks (retrieval + LLM via callbacks)
- HuggingFaceEmbedding (embeddings via monkey patching)
"""

import time
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any

from sourcemapr.providers.base import BaseProvider
from sourcemapr.store import TraceStore


# ============================================================================
# CALLBACK HANDLER
# ============================================================================

def _create_callback_handler(store: TraceStore, skip_llm_logging: bool = False):
    """Create LlamaIndex callback handler.

    Args:
        store: TraceStore instance
        skip_llm_logging: If True, skip LLM call logging (use when OpenAI provider is also active)
    """
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType, EventPayload

    class SourcemapRCallbackHandler(BaseCallbackHandler):
        """Callback handler for LlamaIndex query and LLM events."""

        def __init__(self):
            super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
            self.store = store
            self._query_data: Dict[str, Dict] = {}
            self._llm_data: Dict[str, Dict] = {}
            self._skip_llm_logging = skip_llm_logging
        
        def on_event_start(self, event_type: CBEventType, payload: Optional[Dict] = None,
                          event_id: str = "", parent_id: str = "", **kwargs):
            """Called when an event starts."""
            if event_type == CBEventType.QUERY:
                query_str = ""
                if payload and EventPayload.QUERY_STR in payload:
                    query_str = str(payload[EventPayload.QUERY_STR])

                # Pre-generate retrieval_id and add to queue for LLM call to pick up
                import uuid
                retrieval_id = str(uuid.uuid4())[:12]
                with self.store._retrieval_lock:
                    self.store._retrieval_id_queue.append(retrieval_id)

                self._query_data[event_id] = {
                    "start_time": time.time(),
                    "query_str": query_str,
                    "retrieval_id": retrieval_id  # Store for use in _handle_query_end
                }
                print(f"[SourcemapR] Query started: {query_str[:50]}...")
            
            elif event_type == CBEventType.LLM:
                if self._skip_llm_logging:
                    return event_id
                messages = []
                prompt = ""
                model = "unknown"
                temperature = None
                max_tokens = None

                if payload:
                    messages = payload.get(EventPayload.MESSAGES, [])
                    prompt = payload.get(EventPayload.PROMPT, "")
                    serialized = payload.get(EventPayload.SERIALIZED, {})
                    model = serialized.get('model', serialized.get('model_name', 'unknown'))
                    temperature = serialized.get('temperature')
                    max_tokens = serialized.get('max_tokens')

                self._llm_data[event_id] = {
                    "start_time": time.time(),
                    "messages": messages,
                    "prompt": prompt,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                print(f"[SourcemapR] LLM call started: {model}")
            
            return event_id
        
        def on_event_end(self, event_type: CBEventType, payload: Optional[Dict] = None,
                         event_id: str = "", **kwargs):
            """Called when an event ends."""
            if event_type == CBEventType.QUERY:
                self._handle_query_end(event_id, payload)
            elif event_type == CBEventType.LLM:
                if not self._skip_llm_logging:
                    self._handle_llm_end(event_id, payload)
        
        def _handle_query_end(self, event_id: str, payload: Optional[Dict]):
            """Handle query completion."""
            query_data = self._query_data.pop(event_id, {"start_time": time.time(), "query_str": "", "retrieval_id": None})
            start_time = query_data["start_time"]
            query_str = query_data["query_str"]
            retrieval_id = query_data.get("retrieval_id")  # Pre-generated in on_event_start
            duration_ms = (time.time() - start_time) * 1000

            source_nodes = []
            response_text = ""

            if payload and EventPayload.RESPONSE in payload:
                response_obj = payload[EventPayload.RESPONSE]
                source_nodes = getattr(response_obj, 'source_nodes', [])
                response_text = str(response_obj) if response_obj else ""

            print(f"[SourcemapR] Query completed: '{query_str[:30]}...' with {len(source_nodes)} sources")

            results = []
            for i, n in enumerate(source_nodes):
                node = getattr(n, 'node', n)
                metadata = getattr(node, 'metadata', {}) if node else {}
                results.append({
                    "chunk_id": node.node_id if hasattr(node, 'node_id') else str(i),
                    "score": getattr(n, 'score', 0),
                    "text": node.text[:500] if hasattr(node, 'text') else str(n)[:500],
                    "doc_id": metadata.get('file_name', ''),
                    "page_number": metadata.get('page_label'),
                    "file_path": metadata.get('file_path', ''),
                })

            self.store.log_retrieval(
                query=query_str,
                results=results,
                duration_ms=duration_ms,
                response=response_text,
                retrieval_id=retrieval_id  # Use pre-generated ID
            )
        
        def _handle_llm_end(self, event_id: str, payload: Optional[Dict]):
            """Handle LLM completion."""
            llm_data = self._llm_data.pop(event_id, {
                "start_time": time.time(),
                "messages": [],
                "prompt": "",
                "model": "unknown",
                "temperature": None,
                "max_tokens": None,
            })
            duration_ms = (time.time() - llm_data["start_time"]) * 1000
            
            response_text = ""
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            
            if payload:
                response_obj = payload.get(EventPayload.RESPONSE)
                if response_obj:
                    if hasattr(response_obj, 'text'):
                        response_text = response_obj.text
                    elif hasattr(response_obj, 'message'):
                        msg = response_obj.message
                        response_text = getattr(msg, 'content', str(msg))
                    else:
                        response_text = str(response_obj)
                    
                    # Extract token usage
                    if hasattr(response_obj, 'raw') and response_obj.raw:
                        raw = response_obj.raw
                        if hasattr(raw, 'usage') and raw.usage:
                            prompt_tokens = getattr(raw.usage, 'prompt_tokens', None)
                            completion_tokens = getattr(raw.usage, 'completion_tokens', None)
                            total_tokens = getattr(raw.usage, 'total_tokens', None)
            
            # Format messages
            messages_formatted = []
            for msg in llm_data.get("messages", []):
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    role_val = msg.role
                    if hasattr(role_val, 'value'):
                        role_val = role_val.value
                    messages_formatted.append({
                        'role': str(role_val),
                        'content': msg.content if isinstance(msg.content, str) else str(msg.content)
                    })
                elif isinstance(msg, dict):
                    messages_formatted.append(msg)
            
            self.store.log_llm(
                model=llm_data.get("model", "unknown"),
                duration_ms=duration_ms,
                messages=messages_formatted if messages_formatted else None,
                prompt=llm_data.get("prompt") if not messages_formatted else None,
                response=response_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                temperature=llm_data.get("temperature"),
                max_tokens=llm_data.get("max_tokens"),
                provider="llamaindex"
            )
            print(f"[SourcemapR] LLM call logged: {llm_data.get('model', 'unknown')} ({duration_ms:.0f}ms)")
        
        def start_trace(self, trace_id: Optional[str] = None) -> str:
            import uuid
            return trace_id or str(uuid.uuid4())
        
        def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict] = None) -> None:
            pass
    
    return SourcemapRCallbackHandler()


# ============================================================================
# PATCH HELPERS
# ============================================================================

def _extract_doc_metadata(documents):
    """Extract filename and file path mappings from documents."""
    source_filenames = []
    source_file_paths = {}
    doc_id_to_filename = {}
    
    for doc in documents:
        if hasattr(doc, 'metadata') and doc.metadata:
            filename = doc.metadata.get('file_name') or doc.metadata.get('filename')
            file_path = doc.metadata.get('file_path', '')
            if filename:
                source_filenames.append(filename)
                if file_path:
                    source_file_paths[filename] = file_path
                # Map various IDs to filename
                if hasattr(doc, 'doc_id') and doc.doc_id:
                    doc_id_to_filename[doc.doc_id] = filename
                if hasattr(doc, 'id_') and doc.id_:
                    doc_id_to_filename[doc.id_] = filename
                if hasattr(doc, 'ref_doc_id') and doc.ref_doc_id:
                    doc_id_to_filename[doc.ref_doc_id] = filename
    
    default_filename = source_filenames[0] if len(source_filenames) == 1 else None
    return source_filenames, source_file_paths, doc_id_to_filename, default_filename


def _get_node_doc_id(node, doc_id_to_filename, default_filename, current_doc_filename):
    """Get document ID for a node using multiple fallback strategies."""
    metadata = node.metadata or {}
    doc_id = metadata.get('file_name') or metadata.get('filename')
    
    if not doc_id and hasattr(node, 'ref_doc_id') and node.ref_doc_id:
        doc_id = doc_id_to_filename.get(node.ref_doc_id)
    
    if not doc_id and hasattr(node, 'source_node') and node.source_node:
        src = node.source_node
        if hasattr(src, 'metadata'):
            doc_id = src.metadata.get('file_name') or src.metadata.get('filename')
    
    if not doc_id:
        doc_id = default_filename or ''
    
    if not doc_id:
        doc_id = current_doc_filename or ''
    
    if not doc_id:
        doc_id = node.ref_doc_id or ''
    
    return doc_id


def _build_html_parsed_text(chunks_by_doc, source_file_paths, store):
    """Build and store parsed text for HTML files from chunks."""
    for doc_id, chunks in chunks_by_doc.items():
        file_path = source_file_paths.get(doc_id, '')
        file_ext = file_path.lower().split('.')[-1] if file_path else ''
        
        if file_ext in ('htm', 'html', 'xhtml') and chunks:
            sorted_chunks = sorted(chunks, key=lambda x: x['index'])
            
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
            
            store.log_parsed(
                doc_id=doc_id,
                filename=doc_id,
                text=parsed_text
            )
            print(f"[SourcemapR] Built parsed text for HTML: {doc_id} ({len(chunks)} chunks)")


def _extract_page_from_text(text):
    """Extract page number from SEC filing text patterns."""
    if not text:
        return None
    # Pattern 1: Page number at start of chunk (e.g., "49\n\nTesla, Inc.")
    match = re.match(r'^\s*(\d{1,3})\s*\n', text)
    if match:
        return int(match.group(1))
    # Pattern 2: Page number in first line alone
    lines = text.strip().split('\n')
    if lines and lines[0].strip().isdigit():
        num = int(lines[0].strip())
        if 1 <= num <= 500:  # Reasonable page range
            return num
    return None


# ============================================================================
# MAIN PROVIDER
# ============================================================================

class LlamaIndexProvider(BaseProvider):
    """LlamaIndex instrumentation provider."""
    
    name = "llamaindex"
    # Class variable to track current document context for chunk linking
    _current_doc_filename = None
    
    def __init__(self, store: TraceStore):
        super().__init__(store)
        self._callback_handler = None
    
    def is_available(self) -> bool:
        try:
            import llama_index.core
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
            self._patch_directory_reader()
            self._patch_flat_reader()
            self._patch_sentence_splitter()
            self._patch_vector_store_index()
            self._patch_embeddings()
            self._instrumented = True
            print("[SourcemapR] LlamaIndex provider enabled")
            return True
        except Exception as e:
            print(f"[SourcemapR] LlamaIndex provider error: {e}")
            return False
    
    # ========================================================================
    # CALLBACK SETUP
    # ========================================================================
    
    def _setup_callbacks(self):
        """Set up LlamaIndex callback handler."""
        from llama_index.core.callbacks import CallbackManager
        from llama_index.core import Settings

        # Skip LLM logging if OpenAI provider is available (to avoid duplicates)
        skip_llm = self._check_openai_available()
        self._callback_handler = _create_callback_handler(self.store, skip_llm_logging=skip_llm)
        if skip_llm:
            print("[SourcemapR] LlamaIndex: Skipping LLM logging (OpenAI provider active)")

        if Settings.callback_manager is None:
            Settings.callback_manager = CallbackManager([self._callback_handler])
        else:
            Settings.callback_manager.add_handler(self._callback_handler)

        print("[SourcemapR] Registered callback handler")

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
    
    def _patch_directory_reader(self):
        """Patch SimpleDirectoryReader.load_data."""
        try:
            from llama_index.core import SimpleDirectoryReader
            original_load = SimpleDirectoryReader.load_data
            store = self.store
            register_framework = self._register_framework
            
            def patched_load(self_reader, *args, **kwargs):
                register_framework()
                span = store.start_span("load_documents", kind="document")
                try:
                    result = original_load(self_reader, *args, **kwargs)
                    
                    docs_by_file = {}
                    for doc in result:
                        filename = doc.metadata.get('file_name', 'unknown')
                        if filename not in docs_by_file:
                            docs_by_file[filename] = {
                                'file_path': doc.metadata.get('file_path', ''),
                                'pages': []
                            }
                        docs_by_file[filename]['pages'].append(doc)
                    
                    store.end_span(span, attributes={
                        "num_files": len(docs_by_file),
                        "num_pages": len(result),
                    })
                    
                    for filename, file_data in docs_by_file.items():
                        full_text = "\n\n--- PAGE BREAK ---\n\n".join(
                            [p.text for p in file_data['pages']]
                        )
                        
                        store.log_document(
                            doc_id=filename,
                            filename=filename,
                            file_path=file_data['file_path'],
                            text_length=len(full_text),
                            num_pages=len(file_data['pages'])
                        )
                        
                        store.log_parsed(
                            doc_id=filename,
                            filename=filename,
                            text=full_text
                        )
                        
                        print(f"[SourcemapR] Document loaded: {filename} ({len(file_data['pages'])} pages)")
                    
                    return result
                except Exception as e:
                    store.end_span(span, status="error")
                    raise
            
            SimpleDirectoryReader.load_data = patched_load
            self._original_handlers['SimpleDirectoryReader.load_data'] = original_load
        except ImportError:
            pass
    
    def _patch_flat_reader(self):
        """Patch FlatReader.load_data for HTML/text file loading."""
        try:
            from llama_index.readers.file import FlatReader
            original_load = FlatReader.load_data
            store = self.store
            register_framework = self._register_framework
            
            def patched_load(self_reader, path, *args, **kwargs):
                register_framework()
                span = store.start_span("load_documents", kind="document")
                try:
                    result = original_load(self_reader, path, *args, **kwargs)
                    
                    filepath = Path(path) if not isinstance(path, Path) else path
                    abs_path = os.path.abspath(filepath)
                    filename = filepath.name
                    file_ext = filepath.suffix.lower()
                    
                    store.end_span(span, attributes={
                        "num_files": 1,
                        "num_pages": len(result),
                        "filename": filename,
                    })
                    
                    # Inject file_name metadata into documents for chunk linking
                    for doc in result:
                        if not doc.metadata:
                            doc.metadata = {}
                        doc.metadata['file_name'] = filename
                        doc.metadata['file_path'] = abs_path
                    
                    # Set current document context for chunk linking
                    LlamaIndexProvider._current_doc_filename = filename
                    
                    # For HTML files, don't store raw HTML as parsed text
                    if file_ext in ('.htm', '.html', '.xhtml'):
                        parsed_text = None
                    else:
                        parsed_text = "\n\n--- PAGE BREAK ---\n\n".join([doc.text for doc in result])
                    
                    store.log_document(
                        doc_id=filename,
                        filename=filename,
                        file_path=abs_path,
                        text_length=len(result[0].text) if result else 0,
                        num_pages=len(result)
                    )
                    
                    if parsed_text:
                        store.log_parsed(
                            doc_id=filename,
                            filename=filename,
                            text=parsed_text
                        )
                    
                    print(f"[SourcemapR] FlatReader loaded: {filename} ({len(result)} docs, path: {abs_path})")
                    return result
                except Exception as e:
                    store.end_span(span, status="error")
                    raise
            
            FlatReader.load_data = patched_load
            self._original_handlers['FlatReader.load_data'] = original_load
        except ImportError:
            pass
    
    def _patch_sentence_splitter(self):
        """Patch NodeParser base class to catch all node parsers."""
        try:
            from llama_index.core.node_parser.interface import NodeParser
            store = self.store
            
            if hasattr(NodeParser.get_nodes_from_documents, '_sourcemapr_patched'):
                return
            
            original_parse = NodeParser.get_nodes_from_documents
            
            def patched_parse(self_parser, documents, *args, **kwargs):
                parser_name = self_parser.__class__.__name__
                span = store.start_span("chunk_documents", kind="chunking")
                try:
                    source_filenames, source_file_paths, doc_id_to_filename, default_filename = _extract_doc_metadata(documents)
                    
                    result = original_parse(self_parser, documents, *args, **kwargs)
                    store.end_span(span, attributes={
                        "num_nodes": len(result),
                        "parser": parser_name,
                        "chunk_size": getattr(self_parser, 'chunk_size', 0),
                    })
                    
                    chunks_by_doc = {}
                    
                    for i, node in enumerate(result):
                        doc_id = _get_node_doc_id(
                            node, doc_id_to_filename, default_filename,
                            LlamaIndexProvider._current_doc_filename
                        )
                        
                        metadata = node.metadata or {}
                        page_number = int(metadata.get('page_label')) if metadata.get('page_label') else None
                        
                        if doc_id:
                            if doc_id not in chunks_by_doc:
                                chunks_by_doc[doc_id] = []
                            chunks_by_doc[doc_id].append({
                                'index': i,
                                'text': node.text,
                                'page_number': page_number
                            })
                        
                        store.log_chunk(
                            chunk_id=node.node_id,
                            doc_id=doc_id,
                            index=i,
                            text=node.text,
                            page_number=page_number,
                            start_char_idx=getattr(node, 'start_char_idx', None),
                            end_char_idx=getattr(node, 'end_char_idx', None),
                            metadata=metadata
                        )
                    
                    _build_html_parsed_text(chunks_by_doc, source_file_paths, store)
                    
                    print(f"[SourcemapR] {parser_name}: {len(result)} chunks created")
                    return result
                except Exception as e:
                    store.end_span(span, status="error")
                    raise
            
            patched_parse._sourcemapr_patched = True
            NodeParser.get_nodes_from_documents = patched_parse
            self._original_handlers['NodeParser.get_nodes_from_documents'] = original_parse
            print("[SourcemapR] Patched NodeParser base class (all splitters)")
        except ImportError:
            pass
        
        # Also patch get_base_nodes_and_mappings for UnstructuredElementNodeParser
        self._patch_unstructured_element_parser()
    
    def _patch_unstructured_element_parser(self):
        """Patch UnstructuredElementNodeParser.get_base_nodes_and_mappings."""
        try:
            from llama_index.core.node_parser import UnstructuredElementNodeParser
            
            if not hasattr(UnstructuredElementNodeParser, 'get_base_nodes_and_mappings'):
                return
            
            if hasattr(UnstructuredElementNodeParser.get_base_nodes_and_mappings, '_sourcemapr_patched'):
                return
            
            original_get_base = UnstructuredElementNodeParser.get_base_nodes_and_mappings
            store = self.store
            
            def patched_get_base(self_parser, nodes, *args, **kwargs):
                # Extract filename from source nodes for linking
                source_filename = None
                for node in nodes:
                    if hasattr(node, 'metadata') and node.metadata:
                        source_filename = node.metadata.get('file_name') or node.metadata.get('filename')
                        if source_filename:
                            break
                
                base_nodes, node_mappings = original_get_base(self_parser, nodes, *args, **kwargs)
                
                # Log the base nodes as chunks with proper doc_id
                for i, node in enumerate(base_nodes):
                    metadata = node.metadata or {}
                    doc_id = metadata.get('file_name') or metadata.get('filename') or source_filename or ''
                    
                    # Determine node type (table vs text)
                    node_type = 'text'
                    if hasattr(node, 'metadata') and node.metadata:
                        if 'table' in str(node.metadata).lower() or 'TableElement' in str(type(node)):
                            node_type = 'table'
                    
                    # Extract page number from metadata or text
                    page_number = None
                    if metadata.get('page_label'):
                        try:
                            page_number = int(metadata.get('page_label'))
                        except (ValueError, TypeError):
                            pass
                    
                    if page_number is None:
                        node_text = node.text if hasattr(node, 'text') else str(node)
                        page_number = _extract_page_from_text(node_text)
                    
                    store.log_chunk(
                        chunk_id=node.node_id if hasattr(node, 'node_id') else f"base_{i}",
                        doc_id=doc_id,
                        index=i,
                        text=node.text if hasattr(node, 'text') else str(node),
                        page_number=page_number,
                        metadata={**metadata, 'node_type': node_type}
                    )
                
                # Store combined text as parsed content
                if base_nodes and source_filename:
                    parsed_text = "\n\n".join([
                        node.text if hasattr(node, 'text') else str(node)
                        for node in base_nodes
                    ])
                    store.log_parsed(
                        doc_id=source_filename,
                        filename=source_filename,
                        text=parsed_text
                    )
                
                print(f"[SourcemapR] UnstructuredElementNodeParser: {len(base_nodes)} base nodes, {len(node_mappings)} table mappings")
                return base_nodes, node_mappings
            
            patched_get_base._sourcemapr_patched = True
            UnstructuredElementNodeParser.get_base_nodes_and_mappings = patched_get_base
            self._original_handlers['UnstructuredElementNodeParser.get_base_nodes_and_mappings'] = original_get_base
            print("[SourcemapR] Patched UnstructuredElementNodeParser.get_base_nodes_and_mappings")
        except ImportError:
            pass
    
    def _patch_vector_store_index(self):
        """Patch VectorStoreIndex.from_documents."""
        try:
            from llama_index.core import VectorStoreIndex
            original_from_docs = VectorStoreIndex.from_documents.__func__
            store = self.store
            
            @classmethod
            def patched_from_docs(cls, documents, *args, **kwargs):
                span = store.start_span("create_index", kind="indexing")
                try:
                    result = original_from_docs(cls, documents, *args, **kwargs)
                    store.end_span(span, attributes={"num_documents": len(documents)})
                    return result
                except Exception as e:
                    store.end_span(span, status="error")
                    raise
            
            VectorStoreIndex.from_documents = patched_from_docs
            self._original_handlers['VectorStoreIndex.from_documents'] = original_from_docs
        except ImportError:
            pass
    
    def _patch_embeddings(self):
        """Patch HuggingFaceEmbedding."""
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            original_embed = HuggingFaceEmbedding._get_text_embedding
            store = self.store
            
            def patched_embed(self_emb, text, *args, **kwargs):
                start = time.time()
                result = original_embed(self_emb, text, *args, **kwargs)
                duration = (time.time() - start) * 1000
                store.log_embedding(
                    chunk_id="",
                    model=getattr(self_emb, 'model_name', 'unknown'),
                    dim=len(result),
                    duration_ms=duration
                )
                return result
            
            HuggingFaceEmbedding._get_text_embedding = patched_embed
            self._original_handlers['HuggingFaceEmbedding._get_text_embedding'] = original_embed
        except ImportError:
            pass
    
    def uninstrument(self) -> None:
        """Restore original methods."""
        for name, original in self._original_handlers.items():
            try:
                parts = name.split('.')
                if len(parts) == 2:
                    cls_name, method_name = parts
                    if cls_name == 'SimpleDirectoryReader':
                        from llama_index.core import SimpleDirectoryReader
                        setattr(SimpleDirectoryReader, method_name, original)
                    elif cls_name == 'SentenceSplitter':
                        from llama_index.core.node_parser import SentenceSplitter
                        setattr(SentenceSplitter, method_name, original)
                    elif cls_name == 'NodeParser':
                        from llama_index.core.node_parser.interface import NodeParser
                        setattr(NodeParser, method_name, original)
                    elif cls_name == 'VectorStoreIndex':
                        from llama_index.core import VectorStoreIndex
                        setattr(VectorStoreIndex, method_name, original)
                    elif cls_name == 'HuggingFaceEmbedding':
                        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                        setattr(HuggingFaceEmbedding, method_name, original)
                    elif cls_name == 'FlatReader':
                        from llama_index.readers.file import FlatReader
                        setattr(FlatReader, method_name, original)
                    elif cls_name == 'UnstructuredElementNodeParser':
                        from llama_index.core.node_parser import UnstructuredElementNodeParser
                        setattr(UnstructuredElementNodeParser, method_name, original)
            except Exception:
                pass
        
        self._original_handlers.clear()
        self._instrumented = False
