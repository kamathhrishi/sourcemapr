"""
SQLite Database Layer for SourcemapR - RAG Observability Platform.
Provides persistent storage for experiments, traces, documents, and all observability data.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

DB_PATH = Path(__file__).parent / "observability.db"


def init_db():
    """Initialize database with schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT UNIQUE NOT NULL,
                experiment_id INTEGER,
                name TEXT,
                start_time TEXT,
                end_time TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Spans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                span_id TEXT UNIQUE NOT NULL,
                trace_id TEXT,
                parent_id TEXT,
                name TEXT,
                kind TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_ms REAL,
                status TEXT,
                attributes TEXT,
                events TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                experiment_id INTEGER,
                filename TEXT,
                file_path TEXT,
                num_pages INTEGER,
                text_length INTEGER,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Parsed documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsed_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                filename TEXT,
                text TEXT,
                text_length INTEGER,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                doc_id TEXT,
                experiment_id INTEGER,
                index_num INTEGER,
                text TEXT,
                text_length INTEGER,
                page_number INTEGER,
                metadata TEXT,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT,
                model TEXT,
                dimensions INTEGER,
                duration_ms REAL,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Retrievals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retrievals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                query TEXT,
                results TEXT,
                num_results INTEGER,
                duration_ms REAL,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # LLM calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                model TEXT,
                duration_ms REAL,
                input_type TEXT,
                messages TEXT,
                prompt TEXT,
                response TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                temperature REAL,
                status TEXT,
                error TEXT,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_experiment ON traces(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_experiment ON documents(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_experiment ON chunks(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retrievals_experiment ON retrievals(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_experiment ON llm_calls(experiment_id)")

        conn.commit()


@contextmanager
def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_tables_exist():
    """Ensure all tables exist, recreating them if needed."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if traces table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traces'")
        if not cursor.fetchone():
            print("[SourcemapR] Database tables missing, reinitializing...")
            init_db()
            return True
    return False


# ========== Experiment CRUD ==========

def create_experiment(name: str, description: str = None) -> Dict:
    """Create a new experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experiments (name, description) VALUES (?, ?)",
            (name, description)
        )
        conn.commit()
        exp_id = cursor.lastrowid
        return get_experiment(exp_id)


def get_or_create_experiment_by_name(name: str) -> int:
    """Get experiment ID by name, creating it if it doesn't exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM experiments WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row['id']
        # Create new experiment
        cursor.execute(
            "INSERT INTO experiments (name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return cursor.lastrowid


# Cache for default experiment ID to avoid nested connections
_default_experiment_id_cache: Optional[int] = None


def get_default_experiment_id() -> int:
    """Get or create the Default experiment and return its ID. Uses caching to avoid nested connections."""
    global _default_experiment_id_cache
    if _default_experiment_id_cache is not None:
        return _default_experiment_id_cache
    _default_experiment_id_cache = get_or_create_experiment_by_name("Default")
    return _default_experiment_id_cache


def get_experiments() -> List[Dict]:
    """Get all experiments with counts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                e.*,
                (SELECT COUNT(*) FROM traces WHERE experiment_id = e.id) as trace_count,
                (SELECT COUNT(*) FROM documents WHERE experiment_id = e.id) as doc_count,
                (SELECT COUNT(*) FROM retrievals WHERE experiment_id = e.id) as retrieval_count,
                (SELECT COUNT(*) FROM llm_calls WHERE experiment_id = e.id) as llm_count
            FROM experiments e
            ORDER BY e.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_experiment(exp_id: int) -> Optional[Dict]:
    """Get a single experiment by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                e.*,
                (SELECT COUNT(*) FROM traces WHERE experiment_id = e.id) as trace_count,
                (SELECT COUNT(*) FROM documents WHERE experiment_id = e.id) as doc_count,
                (SELECT COUNT(*) FROM retrievals WHERE experiment_id = e.id) as retrieval_count,
                (SELECT COUNT(*) FROM llm_calls WHERE experiment_id = e.id) as llm_count
            FROM experiments e
            WHERE e.id = ?
        """, (exp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_experiment(exp_id: int, name: str = None, description: str = None) -> Optional[Dict]:
    """Update an experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(exp_id)
            cursor.execute(
                f"UPDATE experiments SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()

        return get_experiment(exp_id)


def delete_experiment(exp_id: int) -> bool:
    """Delete an experiment. Associated data becomes unassigned."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experiments WHERE id = ?", (exp_id,))
        conn.commit()
        return cursor.rowcount > 0


# ========== Assignment Functions ==========

def assign_to_experiment(exp_id: int, trace_ids: List[str] = None, doc_ids: List[str] = None,
                         retrieval_ids: List[int] = None, llm_ids: List[int] = None) -> int:
    """Assign items to an experiment. Returns count of updated items."""
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()

        if trace_ids:
            placeholders = ','.join('?' * len(trace_ids))
            cursor.execute(
                f"UPDATE traces SET experiment_id = ? WHERE trace_id IN ({placeholders})",
                [exp_id] + trace_ids
            )
            count += cursor.rowcount

        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            cursor.execute(
                f"UPDATE documents SET experiment_id = ? WHERE doc_id IN ({placeholders})",
                [exp_id] + doc_ids
            )
            count += cursor.rowcount
            # Also update chunks for these docs
            cursor.execute(
                f"UPDATE chunks SET experiment_id = ? WHERE doc_id IN ({placeholders})",
                [exp_id] + doc_ids
            )

        if retrieval_ids:
            placeholders = ','.join('?' * len(retrieval_ids))
            cursor.execute(
                f"UPDATE retrievals SET experiment_id = ? WHERE id IN ({placeholders})",
                [exp_id] + retrieval_ids
            )
            count += cursor.rowcount

        if llm_ids:
            placeholders = ','.join('?' * len(llm_ids))
            cursor.execute(
                f"UPDATE llm_calls SET experiment_id = ? WHERE id IN ({placeholders})",
                [exp_id] + llm_ids
            )
            count += cursor.rowcount

        conn.commit()
    return count


def unassign_from_experiment(trace_ids: List[str] = None, doc_ids: List[str] = None,
                             retrieval_ids: List[int] = None, llm_ids: List[int] = None) -> int:
    """Remove items from their experiment (set to NULL). Returns count."""
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()

        if trace_ids:
            placeholders = ','.join('?' * len(trace_ids))
            cursor.execute(
                f"UPDATE traces SET experiment_id = NULL WHERE trace_id IN ({placeholders})",
                trace_ids
            )
            count += cursor.rowcount

        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            cursor.execute(
                f"UPDATE documents SET experiment_id = NULL WHERE doc_id IN ({placeholders})",
                doc_ids
            )
            count += cursor.rowcount
            cursor.execute(
                f"UPDATE chunks SET experiment_id = NULL WHERE doc_id IN ({placeholders})",
                doc_ids
            )

        if retrieval_ids:
            placeholders = ','.join('?' * len(retrieval_ids))
            cursor.execute(
                f"UPDATE retrievals SET experiment_id = NULL WHERE id IN ({placeholders})",
                retrieval_ids
            )
            count += cursor.rowcount

        if llm_ids:
            placeholders = ','.join('?' * len(llm_ids))
            cursor.execute(
                f"UPDATE llm_calls SET experiment_id = NULL WHERE id IN ({placeholders})",
                llm_ids
            )
            count += cursor.rowcount

        conn.commit()
    return count


# ========== Data Storage Functions ==========

def store_trace(data: Dict) -> None:
    """Store a trace."""
    trace_data = data.get('data', {})

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if trace_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(trace_data['experiment_name'])
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO traces (trace_id, experiment_id, name, start_time, end_time, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trace_data.get('trace_id'),
            experiment_id,
            trace_data.get('name'),
            trace_data.get('start_time'),
            trace_data.get('end_time'),
            json.dumps(trace_data)
        ))
        conn.commit()


def store_span(data: Dict) -> None:
    """Store a span."""
    with get_db() as conn:
        cursor = conn.cursor()
        span_data = data.get('data', {})
        cursor.execute("""
            INSERT OR REPLACE INTO spans
            (span_id, trace_id, parent_id, name, kind, start_time, end_time, duration_ms, status, attributes, events)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            span_data.get('span_id'),
            span_data.get('trace_id'),
            span_data.get('parent_id'),
            span_data.get('name'),
            span_data.get('kind'),
            span_data.get('start_time'),
            span_data.get('end_time'),
            span_data.get('duration_ms'),
            span_data.get('status'),
            json.dumps(span_data.get('attributes', {})),
            json.dumps(span_data.get('events', []))
        ))
        conn.commit()


def store_document(data: Dict) -> None:
    """Store a document."""
    doc_data = data.get('data', {})

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if doc_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(doc_data['experiment_name'])
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, experiment_id, filename, file_path, num_pages, text_length, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_data.get('doc_id'),
            experiment_id,
            doc_data.get('filename'),
            doc_data.get('file_path'),
            doc_data.get('num_pages'),
            doc_data.get('text_length'),
            doc_data.get('trace_id'),
            json.dumps(doc_data)
        ))
        conn.commit()


def store_parsed(data: Dict) -> None:
    """Store parsed document content."""
    with get_db() as conn:
        cursor = conn.cursor()
        parsed_data = data.get('data', {})
        cursor.execute("""
            INSERT OR REPLACE INTO parsed_docs
            (doc_id, filename, text, text_length, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            parsed_data.get('doc_id'),
            parsed_data.get('filename'),
            parsed_data.get('text'),
            parsed_data.get('text_length'),
            parsed_data.get('trace_id'),
            json.dumps(parsed_data)
        ))
        conn.commit()


def store_chunk(data: Dict) -> None:
    """Store a chunk."""
    chunk_data = data.get('data', {})

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if chunk_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(chunk_data['experiment_name'])
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, experiment_id, index_num, text, text_length, page_number, metadata, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk_data.get('chunk_id'),
            chunk_data.get('doc_id'),
            experiment_id,
            chunk_data.get('index'),
            chunk_data.get('text'),
            chunk_data.get('text_length'),
            chunk_data.get('page_number'),
            json.dumps(chunk_data.get('metadata', {})),
            chunk_data.get('trace_id'),
            json.dumps(chunk_data)
        ))
        conn.commit()


def store_embedding(data: Dict) -> None:
    """Store an embedding record."""
    with get_db() as conn:
        cursor = conn.cursor()
        emb_data = data.get('data', {})
        cursor.execute("""
            INSERT INTO embeddings
            (chunk_id, model, dimensions, duration_ms, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emb_data.get('chunk_id'),
            emb_data.get('model'),
            emb_data.get('dimensions'),
            emb_data.get('duration_ms'),
            emb_data.get('trace_id'),
            json.dumps(emb_data)
        ))
        conn.commit()


def store_retrieval(data: Dict) -> None:
    """Store a retrieval record."""
    ret_data = data.get('data', {})

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if ret_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(ret_data['experiment_name'])
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retrievals
            (experiment_id, query, results, num_results, duration_ms, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            ret_data.get('query'),
            json.dumps(ret_data.get('results', [])),
            ret_data.get('num_results'),
            ret_data.get('duration_ms'),
            ret_data.get('trace_id'),
            json.dumps(ret_data)
        ))
        conn.commit()


def store_llm_call(data: Dict) -> None:
    """Store an LLM call record."""
    llm_data = data.get('data', {})

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if llm_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(llm_data['experiment_name'])
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO llm_calls
            (experiment_id, model, duration_ms, input_type, messages, prompt, response,
             prompt_tokens, completion_tokens, total_tokens, temperature,
             status, error, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            llm_data.get('model'),
            llm_data.get('duration_ms'),
            llm_data.get('input_type'),
            json.dumps(llm_data.get('messages')) if llm_data.get('messages') else None,
            llm_data.get('prompt'),
            llm_data.get('response'),
            llm_data.get('prompt_tokens'),
            llm_data.get('completion_tokens'),
            llm_data.get('total_tokens'),
            llm_data.get('temperature'),
            llm_data.get('status'),
            llm_data.get('error'),
            llm_data.get('trace_id'),
            json.dumps(llm_data)
        ))
        conn.commit()


# ========== Data Retrieval Functions ==========

def get_traces(experiment_id: int = None, limit: int = 100) -> Dict[str, Dict]:
    """Get traces, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if experiment_id:
            cursor.execute(
                "SELECT * FROM traces WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM traces ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        result = {}
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['experiment_id'] = row['experiment_id']
            result[row['trace_id']] = data
        return result


def get_spans(trace_id: str = None, limit: int = 500) -> Dict[str, Dict]:
    """Get spans, optionally filtered by trace."""
    with get_db() as conn:
        cursor = conn.cursor()
        if trace_id:
            cursor.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY created_at DESC LIMIT ?",
                (trace_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM spans ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        result = {}
        for row in cursor.fetchall():
            result[row['span_id']] = {
                'span_id': row['span_id'],
                'trace_id': row['trace_id'],
                'parent_id': row['parent_id'],
                'name': row['name'],
                'kind': row['kind'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'duration_ms': row['duration_ms'],
                'status': row['status'],
                'attributes': json.loads(row['attributes']) if row['attributes'] else {},
                'events': json.loads(row['events']) if row['events'] else []
            }
        return result


def get_documents(experiment_id: int = None) -> Dict[str, Dict]:
    """Get documents, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if experiment_id:
            cursor.execute(
                "SELECT * FROM documents WHERE experiment_id = ? ORDER BY created_at DESC",
                (experiment_id,)
            )
        else:
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        result = {}
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['experiment_id'] = row['experiment_id']
            result[row['doc_id']] = data
        return result


def get_parsed_docs() -> Dict[str, Dict]:
    """Get all parsed documents."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parsed_docs ORDER BY created_at DESC")
        result = {}
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            result[row['doc_id']] = data
        return result


def get_chunks(doc_id: str = None, experiment_id: int = None) -> Dict[str, Dict]:
    """Get chunks, optionally filtered by doc or experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if doc_id:
            cursor.execute(
                "SELECT * FROM chunks WHERE doc_id = ? ORDER BY index_num",
                (doc_id,)
            )
        elif experiment_id:
            cursor.execute(
                "SELECT * FROM chunks WHERE experiment_id = ? ORDER BY created_at DESC",
                (experiment_id,)
            )
        else:
            cursor.execute("SELECT * FROM chunks ORDER BY created_at DESC")
        result = {}
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['experiment_id'] = row['experiment_id']
            result[row['chunk_id']] = data
        return result


def get_embeddings(limit: int = 100) -> List[Dict]:
    """Get recent embeddings."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM embeddings ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        result = []
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            result.append(data)
        return result


def get_retrievals(experiment_id: int = None, limit: int = 100) -> List[Dict]:
    """Get retrievals, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if experiment_id:
            cursor.execute(
                "SELECT * FROM retrievals WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM retrievals ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        result = []
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['id'] = row['id']
            data['experiment_id'] = row['experiment_id']
            # Include created_at as timestamp if not already present
            if 'timestamp' not in data and row['created_at']:
                data['timestamp'] = row['created_at']
            result.append(data)
        return result


def get_llm_calls(experiment_id: int = None, limit: int = 100) -> List[Dict]:
    """Get LLM calls, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if experiment_id:
            cursor.execute(
                "SELECT * FROM llm_calls WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM llm_calls ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        result = []
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['id'] = row['id']
            data['experiment_id'] = row['experiment_id']
            # Include created_at as timestamp if not already present
            if 'timestamp' not in data and row['created_at']:
                data['timestamp'] = row['created_at']
            result.append(data)
        return result


def get_stats(experiment_id: int = None) -> Dict:
    """Get summary statistics, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()

        if experiment_id:
            cursor.execute("SELECT COUNT(*) FROM traces WHERE experiment_id = ?", (experiment_id,))
            trace_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM spans WHERE trace_id IN (SELECT trace_id FROM traces WHERE experiment_id = ?)", (experiment_id,))
            span_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM documents WHERE experiment_id = ?", (experiment_id,))
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM parsed_docs WHERE doc_id IN (SELECT doc_id FROM documents WHERE experiment_id = ?)", (experiment_id,))
            parsed_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chunks WHERE experiment_id = ?", (experiment_id,))
            chunk_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE experiment_id = ?)", (experiment_id,))
            emb_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM retrievals WHERE experiment_id = ?", (experiment_id,))
            ret_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM llm_calls WHERE experiment_id = ?", (experiment_id,))
            llm_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM traces")
            trace_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM spans")
            span_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM parsed_docs")
            parsed_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            emb_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM retrievals")
            ret_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM llm_calls")
            llm_count = cursor.fetchone()[0]

        return {
            "total_traces": trace_count,
            "total_spans": span_count,
            "total_documents": doc_count,
            "total_parsed": parsed_count,
            "total_chunks": chunk_count,
            "total_embeddings": emb_count,
            "total_retrievals": ret_count,
            "total_llm_calls": llm_count
        }


def clear_all_data() -> None:
    """Clear all data from all tables (except experiments)."""
    global _default_experiment_id_cache
    _default_experiment_id_cache = None  # Reset cache

    # Ensure tables exist first
    ensure_tables_exist()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM traces")
        cursor.execute("DELETE FROM spans")
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM parsed_docs")
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM retrievals")
        cursor.execute("DELETE FROM llm_calls")
        conn.commit()


def clear_experiment_data(experiment_id: int) -> None:
    """Clear all data for a specific experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Just unassign from experiment, don't delete
        cursor.execute("UPDATE traces SET experiment_id = NULL WHERE experiment_id = ?", (experiment_id,))
        cursor.execute("UPDATE documents SET experiment_id = NULL WHERE experiment_id = ?", (experiment_id,))
        cursor.execute("UPDATE chunks SET experiment_id = NULL WHERE experiment_id = ?", (experiment_id,))
        cursor.execute("UPDATE retrievals SET experiment_id = NULL WHERE experiment_id = ?", (experiment_id,))
        cursor.execute("UPDATE llm_calls SET experiment_id = NULL WHERE experiment_id = ?", (experiment_id,))
        conn.commit()


# Initialize database on module import
init_db()
