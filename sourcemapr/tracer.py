"""
Auto-instrumentation for LlamaIndex and OpenAI.

Hooks into LlamaIndex and OpenAI to automatically trace all operations.
Uses LlamaIndex's official callback system for reliable query tracking.
"""

import time
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from sourcemapr.store import TraceStore

# Global tracer instance
_tracer: Optional['LlamaIndexTracer'] = None


class LlamaIndexTracer:
    """
    Automatic tracer for LlamaIndex operations.
    """

    def __init__(self, endpoint: Optional[str] = None, project_name: str = "default"):
        self.store = TraceStore(endpoint=endpoint)
        self.project_name = project_name
        self._original_handlers = {}
        self._instrumented = False
        self._callback_handler = None

    def instrument(self):
        """Install hooks into LlamaIndex."""
        if self._instrumented:
            return

        try:
            self._instrument_llama_index()
            self._instrumented = True
            print(f"[SourcemapR] Tracing enabled -> {self.store.endpoint or 'local'}")
        except Exception as e:
            print(f"[SourcemapR] Warning: {e}")
            import traceback
            traceback.print_exc()

    def _instrument_llama_index(self):
        """Hook into LlamaIndex components via monkey-patching and callbacks."""
        global _tracer

        # Register callback handler for query tracking
        try:
            from llama_index.core.callbacks import CallbackManager
            from llama_index.core.callbacks.base import BaseCallbackHandler
            from llama_index.core import Settings
            from llama_index.core.callbacks.schema import CBEventType, EventPayload
            import uuid

            class SourcemapRCallbackHandler(BaseCallbackHandler):
                def __init__(self, store: TraceStore):
                    super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
                    self.store = store
                    self._query_data: Dict[str, Dict] = {}
                    self._llm_data: Dict[str, Dict] = {}

                def on_event_start(self, event_type: CBEventType, payload: Optional[Dict] = None,
                                   event_id: str = "", parent_id: str = "", **kwargs):
                    if event_type == CBEventType.QUERY:
                        query_str = ""
                        if payload and EventPayload.QUERY_STR in payload:
                            query_str = str(payload[EventPayload.QUERY_STR])
                        self._query_data[event_id] = {
                            "start_time": time.time(),
                            "query_str": query_str
                        }
                        print(f"[SourcemapR] Query started: {query_str[:50]}...")

                    elif event_type == CBEventType.LLM:
                        messages = []
                        prompt = ""
                        model = "unknown"
                        temperature = None
                        max_tokens = None
                        additional_kwargs = {}

                        if payload:
                            messages = payload.get(EventPayload.MESSAGES, [])
                            prompt = payload.get(EventPayload.PROMPT, "")
                            serialized = payload.get(EventPayload.SERIALIZED, {})
                            model = serialized.get('model', serialized.get('model_name', 'unknown'))
                            temperature = serialized.get('temperature')
                            max_tokens = serialized.get('max_tokens')
                            additional_kwargs = serialized.get('additional_kwargs', {})

                            if hasattr(EventPayload, 'TEMPLATE_ARGS'):
                                template_vars = payload.get(EventPayload.TEMPLATE_ARGS, {})
                                if template_vars:
                                    additional_kwargs['template_vars'] = template_vars

                        self._llm_data[event_id] = {
                            "start_time": time.time(),
                            "messages": messages,
                            "prompt": prompt,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "additional_kwargs": additional_kwargs
                        }
                        print(f"[SourcemapR] LLM call started: {model}")

                    return event_id

                def on_event_end(self, event_type: CBEventType, payload: Optional[Dict] = None,
                                 event_id: str = "", **kwargs):
                    if event_type == CBEventType.QUERY:
                        query_data = self._query_data.pop(event_id, {"start_time": time.time(), "query_str": ""})
                        start_time = query_data["start_time"]
                        query_str = query_data["query_str"]
                        duration_ms = (time.time() - start_time) * 1000

                        source_nodes = []
                        if payload and EventPayload.RESPONSE in payload:
                            response = payload[EventPayload.RESPONSE]
                            source_nodes = getattr(response, 'source_nodes', [])

                        response_text = ""
                        if payload and EventPayload.RESPONSE in payload:
                            response_obj = payload[EventPayload.RESPONSE]
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
                            response=response_text
                        )

                    elif event_type == CBEventType.LLM:
                        llm_data = self._llm_data.pop(event_id, {
                            "start_time": time.time(),
                            "messages": [],
                            "prompt": "",
                            "model": "unknown",
                            "temperature": None,
                            "max_tokens": None,
                            "additional_kwargs": {}
                        })
                        start_time = llm_data["start_time"]
                        duration_ms = (time.time() - start_time) * 1000

                        response_text = ""
                        prompt_tokens = None
                        completion_tokens = None
                        total_tokens = None
                        finish_reason = None
                        raw_response = None

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

                                if hasattr(response_obj, 'raw'):
                                    raw = response_obj.raw
                                    try:
                                        if hasattr(raw, 'model_dump'):
                                            raw_response = raw.model_dump()
                                        elif hasattr(raw, 'to_dict'):
                                            raw_response = raw.to_dict()
                                        elif hasattr(raw, '__dict__'):
                                            raw_response = {k: str(v) for k, v in raw.__dict__.items() if not k.startswith('_')}
                                    except:
                                        raw_response = str(raw)

                                    if hasattr(raw, 'usage') and raw.usage:
                                        prompt_tokens = getattr(raw.usage, 'prompt_tokens', None)
                                        completion_tokens = getattr(raw.usage, 'completion_tokens', None)
                                        total_tokens = getattr(raw.usage, 'total_tokens', None)
                                    elif isinstance(raw, dict):
                                        usage = raw.get('usage', {})
                                        prompt_tokens = usage.get('prompt_tokens')
                                        completion_tokens = usage.get('completion_tokens')
                                        total_tokens = usage.get('total_tokens')

                                    if hasattr(raw, 'choices') and raw.choices:
                                        finish_reason = getattr(raw.choices[0], 'finish_reason', None)

                                if hasattr(response_obj, 'additional_kwargs'):
                                    add_kwargs = response_obj.additional_kwargs
                                    if 'prompt_tokens' in add_kwargs:
                                        prompt_tokens = add_kwargs['prompt_tokens']
                                    if 'completion_tokens' in add_kwargs:
                                        completion_tokens = add_kwargs['completion_tokens']
                                    if 'total_tokens' in add_kwargs:
                                        total_tokens = add_kwargs['total_tokens']

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
                            else:
                                messages_formatted.append({'role': 'unknown', 'content': str(msg)})

                        raw_request = {
                            'model': llm_data.get("model", "unknown"),
                            'messages': messages_formatted,
                            'temperature': llm_data.get("temperature"),
                            'max_tokens': llm_data.get("max_tokens"),
                        }
                        if llm_data.get("additional_kwargs"):
                            raw_request['additional_kwargs'] = llm_data["additional_kwargs"]
                        if not messages_formatted and llm_data.get("prompt"):
                            raw_request['prompt'] = llm_data["prompt"]

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
                            finish_reason=finish_reason,
                            raw_request=raw_request,
                            raw_response=raw_response,
                            provider="llamaindex"
                        )
                        print(f"[SourcemapR] LLM call logged: {llm_data.get('model', 'unknown')} ({duration_ms:.0f}ms)")

                def start_trace(self, trace_id: Optional[str] = None) -> str:
                    import uuid
                    return trace_id or str(uuid.uuid4())

                def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict] = None) -> None:
                    pass

            self._callback_handler = SourcemapRCallbackHandler(self.store)

            if Settings.callback_manager is None:
                Settings.callback_manager = CallbackManager([self._callback_handler])
            else:
                Settings.callback_manager.add_handler(self._callback_handler)

            print("[SourcemapR] Registered callback handler")

        except Exception as e:
            print(f"[SourcemapR] Warning: Could not register callback: {e}")
            import traceback
            traceback.print_exc()

        # Patch SimpleDirectoryReader.load_data
        try:
            from llama_index.core import SimpleDirectoryReader
            original_load = SimpleDirectoryReader.load_data

            def patched_load(self_reader, *args, **kwargs):
                span = _tracer.store.start_span("load_documents", kind="document")
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

                    _tracer.store.end_span(span, attributes={
                        "num_files": len(docs_by_file),
                        "num_pages": len(result),
                        "input_dir": str(getattr(self_reader, 'input_dir', 'unknown'))
                    })

                    for filename, file_data in docs_by_file.items():
                        full_text = "\n\n--- PAGE BREAK ---\n\n".join(
                            [p.text for p in file_data['pages']]
                        )

                        _tracer.store.log_document(
                            doc_id=filename,
                            filename=filename,
                            file_path=file_data['file_path'],
                            text_length=len(full_text),
                            num_pages=len(file_data['pages'])
                        )

                        _tracer.store.log_parsed(
                            doc_id=filename,
                            filename=filename,
                            text=full_text
                        )

                    return result
                except Exception as e:
                    _tracer.store.end_span(span, status="error")
                    raise

            SimpleDirectoryReader.load_data = patched_load
            self._original_handlers['SimpleDirectoryReader.load_data'] = original_load
        except ImportError:
            pass

        # Patch SentenceSplitter
        try:
            from llama_index.core.node_parser import SentenceSplitter
            original_parse = SentenceSplitter.get_nodes_from_documents

            def patched_parse(self_parser, documents, *args, **kwargs):
                span = _tracer.store.start_span("chunk_documents", kind="chunking")
                try:
                    result = original_parse(self_parser, documents, *args, **kwargs)
                    _tracer.store.end_span(span, attributes={
                        "num_nodes": len(result),
                        "chunk_size": getattr(self_parser, 'chunk_size', 0),
                    })
                    for i, node in enumerate(result):
                        metadata = node.metadata or {}
                        doc_id = metadata.get('file_name', node.ref_doc_id or '')
                        page_label = metadata.get('page_label')
                        start_idx = node.start_char_idx
                        end_idx = node.end_char_idx

                        _tracer.store.log_chunk(
                            chunk_id=node.node_id,
                            doc_id=doc_id,
                            index=i,
                            text=node.text,
                            page_number=int(page_label) if page_label else None,
                            start_char_idx=start_idx,
                            end_char_idx=end_idx,
                            metadata=metadata
                        )
                    return result
                except Exception as e:
                    _tracer.store.end_span(span, status="error")
                    raise

            SentenceSplitter.get_nodes_from_documents = patched_parse
            self._original_handlers['SentenceSplitter.get_nodes_from_documents'] = original_parse
        except ImportError:
            pass

        # Patch VectorStoreIndex.from_documents
        try:
            from llama_index.core import VectorStoreIndex
            original_from_docs = VectorStoreIndex.from_documents.__func__

            @classmethod
            def patched_from_docs(cls, documents, *args, **kwargs):
                span = _tracer.store.start_span("create_index", kind="indexing")
                try:
                    result = original_from_docs(cls, documents, *args, **kwargs)
                    _tracer.store.end_span(span, attributes={
                        "num_documents": len(documents)
                    })
                    return result
                except Exception as e:
                    _tracer.store.end_span(span, status="error")
                    raise

            VectorStoreIndex.from_documents = patched_from_docs
            self._original_handlers['VectorStoreIndex.from_documents'] = original_from_docs
        except ImportError:
            pass

        # Patch embedding
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            original_embed = HuggingFaceEmbedding._get_text_embedding

            def patched_embed(self_emb, text, *args, **kwargs):
                start = time.time()
                result = original_embed(self_emb, text, *args, **kwargs)
                duration = (time.time() - start) * 1000
                _tracer.store.log_embedding(
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

        # Patch OpenAI client
        self._instrument_openai()

    def _instrument_openai(self):
        """Hook into OpenAI client to capture all API calls."""
        try:
            import openai
            if hasattr(openai, 'OpenAI'):
                self._patch_openai_v1()
            else:
                self._patch_openai_v0()
        except ImportError:
            pass

    def _patch_openai_v1(self):
        """Patch OpenAI v1.x client."""
        try:
            from openai.resources.chat import completions as chat_completions

            original_chat_create = chat_completions.Completions.create

            def patched_chat_create(self_client, *args, **kwargs):
                start = time.time()
                messages = kwargs.get('messages', [])
                model = kwargs.get('model', 'unknown')
                temperature = kwargs.get('temperature')
                max_tokens = kwargs.get('max_tokens')
                stop = kwargs.get('stop')

                try:
                    result = original_chat_create(self_client, *args, **kwargs)
                    duration = (time.time() - start) * 1000

                    response_text = ""
                    finish_reason = None
                    tool_calls_data = None

                    if hasattr(result, 'choices') and result.choices:
                        choice = result.choices[0]
                        if hasattr(choice, 'message'):
                            msg = choice.message
                            response_text = getattr(msg, 'content', '') or ''
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_calls_data = [
                                    {
                                        'id': tc.id,
                                        'type': tc.type,
                                        'function': {
                                            'name': tc.function.name,
                                            'arguments': tc.function.arguments
                                        }
                                    } for tc in msg.tool_calls
                                ]
                        finish_reason = getattr(choice, 'finish_reason', None)

                    usage = getattr(result, 'usage', None)
                    prompt_tokens = getattr(usage, 'prompt_tokens', None) if usage else None
                    completion_tokens = getattr(usage, 'completion_tokens', None) if usage else None
                    total_tokens = getattr(usage, 'total_tokens', None) if usage else None

                    _tracer.store.log_llm(
                        model=model,
                        duration_ms=duration,
                        messages=[{'role': m.get('role', ''), 'content': m.get('content', '')} for m in messages],
                        response=response_text,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop=stop if isinstance(stop, list) else [stop] if stop else None,
                        tool_calls=tool_calls_data,
                        finish_reason=finish_reason,
                        provider="openai",
                        api_type="chat"
                    )

                    return result

                except Exception as e:
                    duration = (time.time() - start) * 1000
                    _tracer.store.log_llm(
                        model=model,
                        duration_ms=duration,
                        messages=[{'role': m.get('role', ''), 'content': m.get('content', '')} for m in messages],
                        error=str(e),
                        provider="openai",
                        api_type="chat"
                    )
                    raise

            chat_completions.Completions.create = patched_chat_create
            self._original_handlers['openai.chat.completions.create'] = original_chat_create

        except Exception as e:
            print(f"[SourcemapR] Warning: Could not patch OpenAI v1: {e}")

    def _patch_openai_v0(self):
        """Patch OpenAI v0.x (legacy) client."""
        try:
            import openai

            if hasattr(openai, 'ChatCompletion'):
                original_chat = openai.ChatCompletion.create

                def patched_chat(*args, **kwargs):
                    start = time.time()
                    messages = kwargs.get('messages', [])
                    model = kwargs.get('model', 'unknown')

                    try:
                        result = original_chat(*args, **kwargs)
                        duration = (time.time() - start) * 1000

                        response_text = result['choices'][0]['message']['content'] if result.get('choices') else ''
                        usage = result.get('usage', {})

                        _tracer.store.log_llm(
                            model=model,
                            duration_ms=duration,
                            messages=messages,
                            response=response_text,
                            prompt_tokens=usage.get('prompt_tokens'),
                            completion_tokens=usage.get('completion_tokens'),
                            total_tokens=usage.get('total_tokens'),
                            temperature=kwargs.get('temperature'),
                            max_tokens=kwargs.get('max_tokens'),
                            provider="openai",
                            api_type="chat"
                        )

                        return result
                    except Exception as e:
                        duration = (time.time() - start) * 1000
                        _tracer.store.log_llm(
                            model=model,
                            duration_ms=duration,
                            messages=messages,
                            error=str(e),
                            provider="openai",
                            api_type="chat"
                        )
                        raise

                openai.ChatCompletion.create = patched_chat
                self._original_handlers['openai.ChatCompletion.create'] = original_chat

        except Exception as e:
            print(f"[SourcemapR] Warning: Could not patch OpenAI v0: {e}")

    def uninstrument(self):
        """Remove hooks."""
        self._instrumented = False

    @contextmanager
    def trace(self, name: str = ""):
        """Context manager for manual tracing."""
        self.store.start_trace(name)
        try:
            yield
        finally:
            self.store.end_trace()

    def stop(self):
        """Stop the tracer."""
        self.store.stop()


def init_tracing(
    endpoint: Optional[str] = None,
    project_name: str = "default"
) -> LlamaIndexTracer:
    """
    Initialize tracing for LlamaIndex.

    Args:
        endpoint: URL of the SourcemapR server (e.g., "http://localhost:5000")
        project_name: Name for this project

    Example:
        >>> from sourcemapr import init_tracing
        >>> init_tracing(endpoint="http://localhost:5000")
    """
    global _tracer
    if _tracer is None:
        _tracer = LlamaIndexTracer(endpoint=endpoint, project_name=project_name)
        _tracer.instrument()
    return _tracer


def stop_tracing():
    """Stop tracing and flush pending data."""
    global _tracer
    if _tracer:
        _tracer.stop()
        _tracer = None


def get_tracer() -> Optional[LlamaIndexTracer]:
    """Get the current tracer instance."""
    return _tracer
