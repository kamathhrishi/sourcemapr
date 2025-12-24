"""
SourcemapR - RAG Observability Platform - FastAPI Server
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from urllib.parse import unquote
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import database functions
from sourcemapr.server import database as db

app = FastAPI(title="SourcemapR - RAG Observability Platform")

# Mount static files
static_path = Path(__file__).parent / "static"
dist_path = static_path / "dist"

# Mount React build assets if they exist
if dist_path.exists():
    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

# Mount legacy static files
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    db.init_db()


@app.middleware("http")
async def ensure_db_middleware(request: Request, call_next):
    """Ensure database tables exist before processing requests."""
    # Only check for API routes that need the database
    if request.url.path.startswith("/api/"):
        db.ensure_tables_exist()
    return await call_next(request)


# ========== Pydantic Models ==========

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AssignmentRequest(BaseModel):
    trace_ids: Optional[List[str]] = None
    doc_ids: Optional[List[str]] = None
    retrieval_ids: Optional[List[int]] = None
    llm_ids: Optional[List[int]] = None


# ========== Dashboard ==========

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard (React SPA or legacy template)."""
    # Try React build first
    react_path = Path(__file__).parent / "static" / "dist" / "index.html"
    if react_path.exists():
        return react_path.read_text()
    # Fallback to legacy template
    template_path = Path(__file__).parent / "templates" / "index.html"
    return template_path.read_text()


# Catch-all route for React Router (SPA client-side routing)
@app.get("/experiment/{path:path}", response_class=HTMLResponse)
async def spa_catch_all(path: str):
    """Serve the React SPA for client-side routing."""
    react_path = Path(__file__).parent / "static" / "dist" / "index.html"
    if react_path.exists():
        return react_path.read_text()
    # Fallback to legacy template
    template_path = Path(__file__).parent / "templates" / "index.html"
    return template_path.read_text()


# ========== Experiment Endpoints ==========

@app.get("/api/experiments")
async def list_experiments():
    """Get all experiments."""
    return db.get_experiments()


@app.post("/api/experiments")
async def create_experiment(exp: ExperimentCreate):
    """Create a new experiment."""
    return db.create_experiment(exp.name, exp.description)


@app.get("/api/experiments/{exp_id}")
async def get_experiment(exp_id: int):
    """Get a specific experiment."""
    exp = db.get_experiment(exp_id)
    if not exp:
        return {"error": "Experiment not found"}
    return exp


@app.put("/api/experiments/{exp_id}")
async def update_experiment(exp_id: int, exp: ExperimentUpdate):
    """Update an experiment."""
    result = db.update_experiment(exp_id, exp.name, exp.description)
    if not result:
        return {"error": "Experiment not found"}
    return result


@app.delete("/api/experiments/{exp_id}")
async def delete_experiment(exp_id: int):
    """Delete an experiment."""
    success = db.delete_experiment(exp_id)
    if not success:
        return {"error": "Experiment not found"}
    return {"status": "deleted"}


@app.post("/api/experiments/{exp_id}/assign")
async def assign_to_experiment(exp_id: int, req: AssignmentRequest):
    """Assign traces/docs to an experiment."""
    count = db.assign_to_experiment(
        exp_id,
        trace_ids=req.trace_ids,
        doc_ids=req.doc_ids,
        retrieval_ids=req.retrieval_ids,
        llm_ids=req.llm_ids
    )
    return {"status": "assigned", "count": count}


@app.post("/api/experiments/{exp_id}/unassign")
async def unassign_from_experiment(exp_id: int, req: AssignmentRequest):
    """Remove items from an experiment."""
    count = db.unassign_from_experiment(
        trace_ids=req.trace_ids,
        doc_ids=req.doc_ids,
        retrieval_ids=req.retrieval_ids,
        llm_ids=req.llm_ids
    )
    return {"status": "unassigned", "count": count}


# ========== Trace Data Ingestion ==========

@app.post("/api/traces")
async def receive_trace(request: Request):
    """Receive trace data from the observability library."""
    data = await request.json()
    event_type = data.get('type')

    # Handle batch events (multiple items in one request)
    if event_type == 'batch':
        items = data.get('items', [])
        print(f"[SourcemapR] Received batch: {len(items)} items")
        _process_batch(items)
        return {"status": "ok", "processed": len(items)}

    # Debug logging for non-batch
    print(f"[SourcemapR] Received event: {event_type}")
    _process_event(data)
    return {"status": "ok"}


def _process_batch(items: list):
    """Process a batch of events efficiently."""
    # Group items by type for bulk processing
    chunks = []
    documents = []
    parsed = []
    other = []

    for item in items:
        event_type = item.get('type')
        if event_type == 'chunk':
            chunks.append(item)
        elif event_type == 'document':
            documents.append(item)
        elif event_type == 'parsed':
            parsed.append(item)
        else:
            other.append(item)

    # Bulk insert chunks (most common)
    if chunks:
        db.store_chunks_batch(chunks)

    # Bulk insert documents
    if documents:
        db.store_documents_batch(documents)

    # Bulk insert parsed docs
    if parsed:
        db.store_parsed_batch(parsed)

    # Process other items individually
    for item in other:
        _process_event(item)


def _process_event(data: dict):
    """Process a single event."""
    event_type = data.get('type')

    if event_type == 'trace':
        db.store_trace(data)
    elif event_type in ('span_start', 'span_end'):
        db.store_span(data)
    elif event_type == 'document':
        db.store_document(data)
    elif event_type == 'parsed':
        db.store_parsed(data)
    elif event_type == 'chunk':
        db.store_chunk(data)
    elif event_type == 'embedding':
        db.store_embedding(data)
    elif event_type == 'retrieval':
        print(f"[SourcemapR] Retrieval data: {data.get('data', {}).get('query', 'N/A')[:50]}")
        db.store_retrieval(data)
    elif event_type == 'llm':
        print(f"[SourcemapR] LLM call: {data.get('data', {}).get('model', 'N/A')}")
        db.store_llm_call(data)
    elif event_type == 'pipeline':
        db.store_pipeline(data)
    elif event_type == 'pipeline_stage':
        stage_data = data.get('data', {})
        chunks = stage_data.pop('chunks', [])
        db.store_pipeline_stage(data)
        if chunks:
            db.store_stage_chunks_batch(stage_data.get('stage_id'), chunks)
        print(f"[SourcemapR] Pipeline stage: {stage_data.get('stage_name')} ({stage_data.get('input_count', 0)} → {stage_data.get('output_count', 0)})")


# ========== Data Retrieval Endpoints ==========

@app.get("/api/stats")
async def get_stats(experiment_id: Optional[int] = Query(None)):
    """Get summary statistics."""
    return db.get_stats(experiment_id)


@app.get("/api/parsed/{doc_id}")
async def get_parsed_for_doc(doc_id: str):
    """Get parsed document content for a specific document (lazy loading)."""
    parsed = db.get_parsed_doc(doc_id)
    if parsed:
        return parsed
    return {"error": "Not found"}


@app.get("/api/data")
async def get_all_data(experiment_id: Optional[int] = Query(None)):
    """Get all data for the dashboard (lightweight - no parsed text)."""
    traces = db.get_traces(experiment_id)
    spans = db.get_spans()
    # Only get chunk metadata, not full text (for performance)
    chunks = db.get_chunks(experiment_id=experiment_id, include_text=True, limit=500)

    # Get documents that have chunks in this experiment (not filtered by experiment_id)
    # This handles the case where documents were logged in one experiment but chunks in another
    if experiment_id and chunks:
        doc_ids_with_chunks = set(c.get('doc_id') for c in chunks.values() if c.get('doc_id'))
        all_documents = db.get_documents()  # Get all documents
        documents = {k: v for k, v in all_documents.items() if v.get('doc_id') in doc_ids_with_chunks}
    else:
        documents = db.get_documents(experiment_id)

    # Don't load parsed docs here - load lazily per document
    parsed = {}
    embeddings = db.get_embeddings(limit=100)
    retrievals = db.get_retrievals(experiment_id, limit=50)
    llm_calls = db.get_llm_calls(experiment_id, limit=50)
    stats = db.get_stats(experiment_id)
    experiments = db.get_experiments()

    return {
        "traces": traces,
        "spans": spans,
        "documents": documents,
        "parsed": parsed,
        "chunks": chunks,
        "embeddings": embeddings,
        "retrievals": retrievals,
        "llm_calls": llm_calls,
        "stats": stats,
        "experiments": experiments
    }


@app.get("/api/traces")
async def get_traces_list(experiment_id: Optional[int] = Query(None)):
    """Get all traces."""
    traces = db.get_traces(experiment_id)
    return list(traces.values())


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace with all its spans."""
    traces = db.get_traces()
    if trace_id not in traces:
        return {"error": "Trace not found"}

    trace = traces[trace_id]
    spans = db.get_spans(trace_id)

    return {
        "trace": trace,
        "spans": list(spans.values())
    }


@app.get("/api/documents")
async def get_documents_list(experiment_id: Optional[int] = Query(None)):
    """Get all documents."""
    documents = db.get_documents(experiment_id)
    return list(documents.values())


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a specific document with its parsed content and chunks."""
    documents = db.get_documents()
    if doc_id not in documents:
        return {"error": "Document not found"}

    doc = documents[doc_id]
    parsed = db.get_parsed_docs().get(doc_id, {})
    chunks = db.get_chunks(doc_id=doc_id)

    return {
        "document": doc,
        "parsed": parsed,
        "chunks": list(chunks.values())
    }


@app.get("/api/parsed")
async def get_parsed():
    """Get all parsed documents."""
    parsed = db.get_parsed_docs()
    return list(parsed.values())


@app.get("/api/chunks")
async def get_chunks_list(experiment_id: Optional[int] = Query(None)):
    """Get all chunks."""
    chunks = db.get_chunks(experiment_id=experiment_id)
    return list(chunks.values())


@app.get("/api/retrievals")
async def get_retrievals_list(experiment_id: Optional[int] = Query(None)):
    """Get recent retrievals."""
    return db.get_retrievals(experiment_id, limit=100)


@app.get("/api/llm")
async def get_llm_calls_list(experiment_id: Optional[int] = Query(None)):
    """Get recent LLM calls."""
    return db.get_llm_calls(experiment_id, limit=100)


# ========== Pipeline Endpoints ==========

@app.get("/api/pipelines")
async def get_pipelines_list(experiment_id: Optional[int] = Query(None)):
    """Get all pipelines for an experiment."""
    return db.get_pipelines(experiment_id, limit=100)


@app.get("/api/pipelines/{pipeline_id}")
async def get_pipeline_detail(pipeline_id: str):
    """Get a specific pipeline with all its stages and chunks."""
    pipeline = db.get_pipeline(pipeline_id)
    if not pipeline:
        return {"error": "Pipeline not found"}
    return pipeline


@app.get("/api/retrievals/{retrieval_id}/pipeline")
async def get_retrieval_pipeline(retrieval_id: str):
    """Get the pipeline associated with a retrieval."""
    pipeline = db.get_pipeline_by_retrieval(retrieval_id)
    if not pipeline:
        return {"error": "No pipeline found for this retrieval"}
    return pipeline


@app.post("/api/clear")
async def clear_data(experiment_id: Optional[int] = Query(None), reset: bool = Query(False)):
    """Clear all data or data for a specific experiment."""
    if experiment_id:
        db.clear_experiment_data(experiment_id)
        return {"status": "cleared", "experiment_id": experiment_id}
    elif reset:
        db.reset_all_data()
        return {"status": "reset", "message": "All data and experiments cleared"}
    else:
        db.clear_all_data()
        return {"status": "cleared"}


# ========== File Serving ==========

@app.get("/api/files/{file_path:path}")
async def get_original_file(file_path: str):
    """Serve original document files (PDFs, etc.)."""
    # Decode the URL-encoded path
    decoded_path = unquote(file_path)
    file = Path(decoded_path)

    if not file.exists():
        return {"error": "File not found"}

    # Security: only allow certain file types and set proper media types
    media_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.htm': 'text/html',
        '.html': 'text/html',
    }

    ext = file.suffix.lower()
    if ext not in media_types:
        return {"error": "File type not allowed"}

    # Read file and return with inline content disposition
    content = file.read_bytes()
    return Response(
        content=content,
        media_type=media_types[ext],
        headers={
            "Content-Disposition": "inline",
            "Content-Length": str(len(content))
        }
    )


def run_server(host: str = "0.0.0.0", port: int = 5000):
    """Run the SourcemapR server."""
    # Ensure database is initialized
    db.init_db()

    print("\n" + "=" * 50)
    print("SourcemapR - RAG Observability Platform")
    print("=" * 50)
    print(f"\nDashboard: http://localhost:{port}")
    print(f"API Docs:  http://localhost:{port}/docs")
    print(f"Database:  {db.DB_PATH}")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
