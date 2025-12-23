"""
Trace storage - stores traces locally and sends to SourcemapR platform.
"""

import json
import threading
import queue
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class Span:
    """A single span in a trace."""
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    kind: str = ""  # document, chunk, embedding, retrieval, llm, etc.
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: float = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status
        }


@dataclass
class Trace:
    """A complete trace containing multiple spans."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    spans: List[Span] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "spans": [s.to_dict() for s in self.spans]
        }


class TraceStore:
    """
    Stores traces and sends them to the SourcemapR platform.

    Features:
    - In-memory storage for current session
    - Async sending to platform endpoint
    - Local file backup
    """

    def __init__(self, endpoint: Optional[str] = None, local_path: str = "./traces", experiment: Optional[str] = None):
        self.endpoint = endpoint
        self.local_path = Path(local_path)
        self.local_path.mkdir(exist_ok=True)
        self.experiment = experiment  # Experiment name for auto-assignment
        self.frameworks: set = set()  # Track which frameworks are being used

        # Storage
        self.traces: Dict[str, Trace] = {}
        self.current_trace: Optional[Trace] = None
        self.span_stack: List[Span] = []

        # Queue of retrieval_ids for linking to subsequent LLM calls
        # (retrieval and LLM may run on different threads in some frameworks)
        self._retrieval_id_queue: List[str] = []
        self._retrieval_lock = threading.Lock()

        # Async sending
        self._send_queue: queue.Queue = queue.Queue()
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False

        if endpoint:
            self._start_sender()

    def _start_sender(self):
        """Start background thread for sending traces."""
        self._running = True
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()

    def _sender_loop(self):
        """Background loop to send traces to endpoint with batching."""
        BATCH_SIZE = 200  # Batch up to 200 items at a time for efficiency
        BATCH_TYPES = {'chunk', 'embedding', 'document', 'parsed'}  # Types that can be batched

        batch = []

        def flush_batch():
            nonlocal batch
            if not batch:
                return
            if len(batch) == 1:
                self._send_to_endpoint(batch[0])
            else:
                self._send_batch(batch)
            batch = []

        while True:
            try:
                item = self._send_queue.get(timeout=0.1)  # Shorter timeout for batching
                if item is None:
                    # Flush any remaining batch
                    flush_batch()
                    # Drain remaining items
                    remaining_items = []
                    while not self._send_queue.empty():
                        remaining = self._send_queue.get_nowait()
                        if remaining:
                            remaining_items.append(remaining)
                    if remaining_items:
                        self._send_batch(remaining_items)
                    break

                event_type = item.get('type', 'unknown')

                # Batch certain types together
                if event_type in BATCH_TYPES:
                    batch.append(item)
                    if len(batch) >= BATCH_SIZE:
                        flush_batch()
                else:
                    # Flush batch before sending non-batchable item
                    flush_batch()
                    if event_type == 'retrieval':
                        print(f"[SourcemapR] Sender: sending retrieval...")
                    self._send_to_endpoint(item)
                    if event_type == 'retrieval':
                        print(f"[SourcemapR] Sender: retrieval sent!")

            except queue.Empty:
                # Flush batch on timeout
                flush_batch()
                if not self._running:
                    break
                continue

    def _send_batch(self, items: List[Dict]):
        """Send a batch of items to the endpoint."""
        if not self.endpoint or not items:
            return
        try:
            # Add experiment name and frameworks to all items
            for item in items:
                if 'data' in item:
                    if self.experiment:
                        item['data']['experiment_name'] = self.experiment
                    if self.frameworks:
                        item['data']['frameworks'] = list(self.frameworks)

            response = requests.post(
                f"{self.endpoint}/api/traces",
                json={"type": "batch", "items": items},
                timeout=30.0  # Longer timeout for batches
            )
            if response.status_code != 200:
                print(f"[SourcemapR] Error sending batch of {len(items)}: HTTP {response.status_code}")
        except Exception as e:
            print(f"[SourcemapR] Error sending batch: {e}")

    def _send_to_endpoint(self, data: Dict):
        """Send data to the SourcemapR platform."""
        if not self.endpoint:
            return
        try:
            # Add experiment name and frameworks if set
            if 'data' in data:
                if self.experiment:
                    data['data']['experiment_name'] = self.experiment
                if self.frameworks:
                    data['data']['frameworks'] = list(self.frameworks)
            response = requests.post(
                f"{self.endpoint}/api/traces",
                json=data,
                timeout=5.0
            )
            # Debug logging for troubleshooting
            if response.status_code != 200:
                print(f"[SourcemapR] Error sending {data.get('type')}: HTTP {response.status_code}")
        except Exception as e:
            # Log errors for debugging but don't interrupt user's code
            print(f"[SourcemapR] Error sending {data.get('type')}: {e}")

    def start_trace(self, name: str = "") -> Trace:
        """Start a new trace."""
        trace = Trace(name=name)
        self.traces[trace.trace_id] = trace
        self.current_trace = trace
        self.span_stack = []
        return trace

    def end_trace(self):
        """End the current trace."""
        if self.current_trace:
            self.current_trace.end_time = datetime.now()
            # Send to platform
            self._send_queue.put({"type": "trace", "data": self.current_trace.to_dict()})
            # Save locally
            self._save_local(self.current_trace)
            self.current_trace = None
            self.span_stack = []

    def start_span(self, name: str, kind: str = "", attributes: Dict = None) -> Span:
        """Start a new span."""
        parent_id = self.span_stack[-1].span_id if self.span_stack else None
        span = Span(
            trace_id=self.current_trace.trace_id if self.current_trace else "",
            parent_id=parent_id,
            name=name,
            kind=kind,
            attributes=attributes or {}
        )

        if self.current_trace:
            self.current_trace.spans.append(span)

        self.span_stack.append(span)

        # Send span start event
        self._send_queue.put({"type": "span_start", "data": span.to_dict()})

        return span

    def end_span(self, span: Span = None, status: str = "ok", attributes: Dict = None):
        """End a span."""
        if span is None and self.span_stack:
            span = self.span_stack.pop()
        elif span and span in self.span_stack:
            self.span_stack.remove(span)

        if span:
            span.end_time = datetime.now()
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
            span.status = status
            if attributes:
                span.attributes.update(attributes)

            # Send span end event
            self._send_queue.put({"type": "span_end", "data": span.to_dict()})

    def add_event(self, name: str, attributes: Dict = None):
        """Add an event to the current span."""
        if self.span_stack:
            self.span_stack[-1].events.append({
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "attributes": attributes or {}
            })

    def log_document(self, doc_id: str, filename: str, **kwargs):
        """Log a document being processed."""
        self._send_queue.put({
            "type": "document",
            "data": {
                "doc_id": doc_id,
                "filename": filename,
                "trace_id": self.current_trace.trace_id if self.current_trace else None,
                **kwargs
            }
        })

    def log_parsed(self, doc_id: str, filename: str, text: str, **kwargs):
        """Log parsed document content."""
        self._send_queue.put({
            "type": "parsed",
            "data": {
                "doc_id": doc_id,
                "filename": filename,
                "text": text,  # Full text
                "text_length": len(text),
                "trace_id": self.current_trace.trace_id if self.current_trace else None,
                **kwargs
            }
        })

    def log_chunk(self, chunk_id: str, doc_id: str, index: int, text: str, **kwargs):
        """Log a chunk being created."""
        self._send_queue.put({
            "type": "chunk",
            "data": {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "index": index,
                "text": text[:500],
                "text_length": len(text),
                "trace_id": self.current_trace.trace_id if self.current_trace else None,
                **kwargs
            }
        })

    def log_embedding(self, chunk_id: str, model: str, dim: int, duration_ms: float):
        """Log an embedding being created."""
        self._send_queue.put({
            "type": "embedding",
            "data": {
                "chunk_id": chunk_id,
                "model": model,
                "dimensions": dim,
                "duration_ms": duration_ms,
                "trace_id": self.current_trace.trace_id if self.current_trace else None
            }
        })

    def log_retrieval(self, query: str, results: List[Dict], duration_ms: float, response: str = None, retrieval_id: str = None):
        """Log a retrieval operation."""
        # Use provided retrieval_id or generate a new one
        if retrieval_id is None:
            retrieval_id = str(uuid.uuid4())[:12]
            # Add to queue for the next LLM call to pick up (only if we generated it)
            with self._retrieval_lock:
                self._retrieval_id_queue.append(retrieval_id)

        data = {
            "type": "retrieval",
            "data": {
                "query": query,
                "results": results,
                "num_results": len(results),
                "duration_ms": duration_ms,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "trace_id": self.current_trace.trace_id if self.current_trace else None,
                "retrieval_id": retrieval_id  # Unique ID to link with LLM call
            }
        }
        print(f"[SourcemapR] Sending retrieval: {query[:30]}...")
        self._send_to_endpoint(data)
        print(f"[SourcemapR] Retrieval sent!")

    def log_llm(
        self,
        model: str,
        duration_ms: float,
        prompt: str = None,
        response: str = None,
        messages: List[Dict] = None,
        prompt_tokens: int = None,
        completion_tokens: int = None,
        total_tokens: int = None,
        temperature: float = None,
        max_tokens: int = None,
        stop: List[str] = None,
        function_call: Dict = None,
        tool_calls: List[Dict] = None,
        finish_reason: str = None,
        raw_request: Dict = None,
        raw_response: Dict = None,
        error: str = None,
        **kwargs
    ):
        """Log an LLM call with full details."""
        # Get retrieval_id from queue (if this LLM call follows a retrieval)
        retrieval_id = None
        with self._retrieval_lock:
            if self._retrieval_id_queue:
                retrieval_id = self._retrieval_id_queue.pop(0)

        data = {
            "model": model,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "trace_id": self.current_trace.trace_id if self.current_trace else None,
            "retrieval_id": retrieval_id,  # Link to the preceding retrieval
        }

        # Input - either prompt string or messages array
        if messages:
            data["messages"] = messages
            data["input_type"] = "chat"
        elif prompt:
            data["prompt"] = prompt
            data["input_type"] = "completion"

        # Output
        if response:
            data["response"] = response
        if finish_reason:
            data["finish_reason"] = finish_reason

        # Token usage
        if prompt_tokens is not None:
            data["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            data["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            data["total_tokens"] = total_tokens

        # Parameters
        if temperature is not None:
            data["temperature"] = temperature
        if max_tokens is not None:
            data["max_tokens"] = max_tokens
        if stop:
            data["stop"] = stop

        # Function/tool calls
        if function_call:
            data["function_call"] = function_call
        if tool_calls:
            data["tool_calls"] = tool_calls

        # Raw request/response for debugging
        if raw_request:
            data["raw_request"] = raw_request
        if raw_response:
            data["raw_response"] = raw_response

        # Error info
        if error:
            data["error"] = error
            data["status"] = "error"
        else:
            data["status"] = "success"

        # Any additional kwargs
        data.update(kwargs)

        print(f"[SourcemapR] Sending LLM call: {model}...")
        self._send_to_endpoint({
            "type": "llm",
            "data": data
        })
        print(f"[SourcemapR] LLM call sent!")

    def _save_local(self, trace: Trace):
        """Save trace to local file."""
        filepath = self.local_path / f"{trace.trace_id}.json"
        with open(filepath, 'w') as f:
            json.dump(trace.to_dict(), f, indent=2)

    def get_all_traces(self) -> List[Dict]:
        """Get all traces."""
        return [t.to_dict() for t in self.traces.values()]

    def stop(self):
        """Stop the background sender and flush remaining items."""
        self._running = False

        # Check queue size before stopping
        queue_size = self._send_queue.qsize()
        if queue_size > 0:
            print(f"[SourcemapR] Flushing {queue_size} remaining events...")

        self._send_queue.put(None)
        if self._sender_thread:
            # Wait longer for large queues (60 seconds max)
            timeout = min(60.0, max(10.0, queue_size * 0.05))
            self._sender_thread.join(timeout=timeout)

            # Check if there are still items left
            remaining = self._send_queue.qsize()
            if remaining > 0:
                print(f"[SourcemapR] Warning: {remaining} events may not have been sent (timeout)")
