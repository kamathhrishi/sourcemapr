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
                framework TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add framework column if it doesn't exist (migration for existing databases)
        try:
            cursor.execute("ALTER TABLE experiments ADD COLUMN framework TEXT")
        except:
            pass  # Column already exists

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
                start_char_idx INTEGER,
                end_char_idx INTEGER,
                metadata TEXT,
                trace_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Add start_char_idx and end_char_idx columns if they don't exist (migration)
        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN start_char_idx INTEGER")
        except:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN end_char_idx INTEGER")
        except:
            pass  # Column already exists

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
                retrieval_id TEXT,
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
                retrieval_id TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Pipelines table - tracks complete RAG pipeline executions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipelines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id TEXT UNIQUE NOT NULL,
                experiment_id INTEGER,
                query TEXT,
                total_duration_ms REAL,
                num_stages INTEGER DEFAULT 0,
                retrieval_id TEXT,
                llm_call_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL
            )
        """)

        # Pipeline stages table - each stage in the pipeline
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id TEXT UNIQUE NOT NULL,
                pipeline_id TEXT,
                stage_type TEXT,
                stage_name TEXT,
                stage_order INTEGER,
                input_count INTEGER DEFAULT 0,
                output_count INTEGER DEFAULT 0,
                duration_ms REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id) ON DELETE CASCADE
            )
        """)

        # Stage chunks table - tracks chunks at each stage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stage_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id TEXT,
                chunk_id TEXT,
                doc_id TEXT,
                text TEXT,
                input_rank INTEGER,
                output_rank INTEGER,
                input_score REAL,
                output_score REAL,
                source TEXT,
                status TEXT DEFAULT 'kept',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES pipeline_stages(stage_id) ON DELETE CASCADE
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retrievals_retrieval_id ON retrievals(retrieval_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_calls_retrieval_id ON llm_calls(retrieval_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pipelines_experiment ON pipelines(experiment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_stages_pipeline ON pipeline_stages(pipeline_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage_chunks_stage ON stage_chunks(stage_id)")

        # Migration: Add retrieval_id column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE retrievals ADD COLUMN retrieval_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE llm_calls ADD COLUMN retrieval_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

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


def get_or_create_experiment_by_name(name: str, frameworks: List[str] = None) -> int:
    """Get experiment ID by name, creating it if it doesn't exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, framework FROM experiments WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            # Update framework if provided - REPLACE don't combine
            if frameworks:
                new_framework = ','.join(sorted(set(frameworks)))
                existing = row['framework'] or ''
                if new_framework != existing:
                    cursor.execute(
                        "UPDATE experiments SET framework = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_framework, row['id'])
                    )
                    conn.commit()
            return row['id']
        # Create new experiment with framework
        framework_str = ','.join(sorted(set(frameworks))) if frameworks else None
        cursor.execute(
            "INSERT INTO experiments (name, framework) VALUES (?, ?)",
            (name, framework_str)
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
    frameworks = trace_data.get('frameworks')

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if trace_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(trace_data['experiment_name'], frameworks)
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
    frameworks = doc_data.get('frameworks')

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if doc_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(doc_data['experiment_name'], frameworks)
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
    frameworks = chunk_data.get('frameworks')

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if chunk_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(chunk_data['experiment_name'], frameworks)
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, experiment_id, index_num, text, text_length, page_number, start_char_idx, end_char_idx, metadata, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk_data.get('chunk_id'),
            chunk_data.get('doc_id'),
            experiment_id,
            chunk_data.get('index'),
            chunk_data.get('text'),
            chunk_data.get('text_length'),
            chunk_data.get('page_number'),
            chunk_data.get('start_char_idx'),
            chunk_data.get('end_char_idx'),
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
    frameworks = ret_data.get('frameworks')

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if ret_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(ret_data['experiment_name'], frameworks)
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retrievals
            (experiment_id, query, results, num_results, duration_ms, trace_id, retrieval_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            ret_data.get('query'),
            json.dumps(ret_data.get('results', [])),
            ret_data.get('num_results'),
            ret_data.get('duration_ms'),
            ret_data.get('trace_id'),
            ret_data.get('retrieval_id'),
            json.dumps(ret_data)
        ))
        conn.commit()


def store_llm_call(data: Dict) -> None:
    """Store an LLM call record."""
    llm_data = data.get('data', {})
    frameworks = llm_data.get('frameworks')

    # Get experiment_id BEFORE opening connection to avoid nested connections
    if llm_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(llm_data['experiment_name'], frameworks)
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO llm_calls
            (experiment_id, model, duration_ms, input_type, messages, prompt, response,
             prompt_tokens, completion_tokens, total_tokens, temperature,
             status, error, trace_id, retrieval_id, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            llm_data.get('retrieval_id'),
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


def get_chunks(doc_id: str = None, experiment_id: int = None, include_text: bool = True, limit: int = None) -> Dict[str, Dict]:
    """Get chunks, optionally filtered by doc or experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        limit_clause = f" LIMIT {limit}" if limit else ""
        if doc_id:
            cursor.execute(
                f"SELECT * FROM chunks WHERE doc_id = ? ORDER BY index_num{limit_clause}",
                (doc_id,)
            )
        elif experiment_id:
            cursor.execute(
                f"SELECT * FROM chunks WHERE experiment_id = ? ORDER BY created_at DESC{limit_clause}",
                (experiment_id,)
            )
        else:
            cursor.execute(f"SELECT * FROM chunks ORDER BY created_at DESC{limit_clause}")
        result = {}
        for row in cursor.fetchall():
            data = json.loads(row['data']) if row['data'] else dict(row)
            data['experiment_id'] = row['experiment_id']
            # Include character indices for precise chunk positioning (if available)
            if row['start_char_idx'] is not None:
                data['start_char_idx'] = row['start_char_idx']
            if row['end_char_idx'] is not None:
                data['end_char_idx'] = row['end_char_idx']
            if row['page_number'] is not None:
                data['page_number'] = row['page_number']
            if row['index_num'] is not None:
                data['index'] = row['index_num']
            # Optionally truncate text for lightweight responses
            if not include_text and 'text' in data:
                data['text'] = data['text'][:200] + '...' if len(data.get('text', '')) > 200 else data.get('text', '')
            result[row['chunk_id']] = data
        return result


def get_parsed_doc(doc_id: str) -> Dict:
    """Get parsed document for a specific doc_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parsed_docs WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        if row:
            data = json.loads(row['data']) if row['data'] else dict(row)
            return data
        return None


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
            # Parse data JSON if it exists
            if row['data']:
                try:
                    data = json.loads(row['data'])
                except (json.JSONDecodeError, TypeError):
                    data = {}
            else:
                data = {}
            
            # Ensure we have all required fields from the row
            data['id'] = row['id']
            data['experiment_id'] = row['experiment_id']
            
            # Parse results from the results column if not in data JSON
            if 'results' not in data or not isinstance(data.get('results'), list):
                if row['results']:
                    try:
                        data['results'] = json.loads(row['results'])
                    except (json.JSONDecodeError, TypeError):
                        data['results'] = []
                else:
                    data['results'] = []
            
            # Ensure results is always a list
            if not isinstance(data.get('results'), list):
                data['results'] = []
            
            # Ensure num_results matches actual results length if not set
            if 'num_results' not in data or data.get('num_results') is None:
                data['num_results'] = len(data['results'])
            
            # Include other fields from row if not in data
            if 'query' not in data and row['query']:
                data['query'] = row['query']
            if 'duration_ms' not in data and row['duration_ms'] is not None:
                data['duration_ms'] = row['duration_ms']
            if 'trace_id' not in data and row['trace_id']:
                data['trace_id'] = row['trace_id']
            if 'retrieval_id' not in data and row['retrieval_id']:
                data['retrieval_id'] = row['retrieval_id']
            
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
            # Parse data JSON if it exists
            if row['data']:
                try:
                    data = json.loads(row['data'])
                except (json.JSONDecodeError, TypeError):
                    data = {}
            else:
                data = {}
            
            # Ensure we have all required fields from the row
            data['id'] = row['id']
            data['experiment_id'] = row['experiment_id']
            
            # Parse messages from the messages column if not in data JSON
            if 'messages' not in data or not isinstance(data.get('messages'), list):
                if row['messages']:
                    try:
                        data['messages'] = json.loads(row['messages'])
                    except (json.JSONDecodeError, TypeError):
                        data['messages'] = None
                else:
                    data['messages'] = None
            
            # Include other fields from row if not in data
            if 'model' not in data and row['model']:
                data['model'] = row['model']
            if 'prompt' not in data and row['prompt']:
                data['prompt'] = row['prompt']
            if 'response' not in data and row['response']:
                data['response'] = row['response']
            if 'duration_ms' not in data and row['duration_ms'] is not None:
                data['duration_ms'] = row['duration_ms']
            if 'input_type' not in data and row['input_type']:
                data['input_type'] = row['input_type']
            if 'status' not in data and row['status']:
                data['status'] = row['status']
            if 'trace_id' not in data and row['trace_id']:
                data['trace_id'] = row['trace_id']
            if 'retrieval_id' not in data and row['retrieval_id']:
                data['retrieval_id'] = row['retrieval_id']
            
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
        cursor.execute("DELETE FROM stage_chunks")
        cursor.execute("DELETE FROM pipeline_stages")
        cursor.execute("DELETE FROM pipelines")
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


def reset_all_data() -> None:
    """Reset ALL data including experiments. Complete database wipe."""
    global _default_experiment_id_cache
    _default_experiment_id_cache = None  # Reset cache

    # Ensure tables exist first
    ensure_tables_exist()

    with get_db() as conn:
        cursor = conn.cursor()
        # Clear all data tables
        cursor.execute("DELETE FROM traces")
        cursor.execute("DELETE FROM spans")
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM parsed_docs")
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM retrievals")
        cursor.execute("DELETE FROM llm_calls")
        cursor.execute("DELETE FROM stage_chunks")
        cursor.execute("DELETE FROM pipeline_stages")
        cursor.execute("DELETE FROM pipelines")
        # Also clear experiments (except Default)
        cursor.execute("DELETE FROM experiments WHERE name != 'Default'")
        # Reset Default experiment's framework
        cursor.execute("UPDATE experiments SET framework = NULL WHERE name = 'Default'")
        conn.commit()


# ========== Batch Operations ==========

def store_chunks_batch(chunks: list) -> None:
    """Store multiple chunks in a single transaction."""
    if not chunks:
        return

    # Group by experiment to minimize experiment lookups
    by_experiment = {}
    frameworks_by_experiment = {}
    for chunk in chunks:
        chunk_data = chunk.get('data', {})
        exp_name = chunk_data.get('experiment_name', 'Default')
        if exp_name not in by_experiment:
            by_experiment[exp_name] = []
            frameworks_by_experiment[exp_name] = set()
        by_experiment[exp_name].append(chunk_data)
        # Collect frameworks for this experiment
        if chunk_data.get('frameworks'):
            for fw in chunk_data['frameworks']:
                frameworks_by_experiment[exp_name].add(fw)

    with get_db() as conn:
        cursor = conn.cursor()
        for exp_name, chunk_list in by_experiment.items():
            frameworks = list(frameworks_by_experiment.get(exp_name, set()))
            framework_str = ','.join(sorted(frameworks)) if frameworks else None

            # Get experiment_id once per group
            cursor.execute("SELECT id, framework FROM experiments WHERE name = ?", (exp_name,))
            row = cursor.fetchone()
            if row:
                experiment_id = row['id']
                # Update framework if needed - REPLACE don't combine
                if frameworks and framework_str != (row['framework'] or ''):
                    cursor.execute(
                        "UPDATE experiments SET framework = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (framework_str, experiment_id)
                    )
            else:
                cursor.execute(
                    "INSERT INTO experiments (name, framework) VALUES (?, ?)",
                    (exp_name, framework_str)
                )
                experiment_id = cursor.lastrowid

            # Bulk insert all chunks for this experiment
            cursor.executemany("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, doc_id, experiment_id, index_num, text, text_length, page_number, start_char_idx, end_char_idx, metadata, trace_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    c.get('chunk_id'),
                    c.get('doc_id'),
                    experiment_id,
                    c.get('index'),
                    c.get('text'),
                    c.get('text_length'),
                    c.get('page_number'),
                    c.get('start_char_idx'),
                    c.get('end_char_idx'),
                    json.dumps(c.get('metadata', {})),
                    c.get('trace_id'),
                    json.dumps(c)
                ) for c in chunk_list
            ])
        conn.commit()


def store_documents_batch(documents: list) -> None:
    """Store multiple documents in a single transaction."""
    if not documents:
        return

    by_experiment = {}
    frameworks_by_experiment = {}
    for doc in documents:
        doc_data = doc.get('data', {})
        exp_name = doc_data.get('experiment_name', 'Default')
        if exp_name not in by_experiment:
            by_experiment[exp_name] = []
            frameworks_by_experiment[exp_name] = set()
        by_experiment[exp_name].append(doc_data)
        # Collect frameworks for this experiment
        if doc_data.get('frameworks'):
            for fw in doc_data['frameworks']:
                frameworks_by_experiment[exp_name].add(fw)

    with get_db() as conn:
        cursor = conn.cursor()
        for exp_name, doc_list in by_experiment.items():
            frameworks = list(frameworks_by_experiment.get(exp_name, set()))
            framework_str = ','.join(sorted(frameworks)) if frameworks else None

            cursor.execute("SELECT id, framework FROM experiments WHERE name = ?", (exp_name,))
            row = cursor.fetchone()
            if row:
                experiment_id = row['id']
                # Update framework if needed - REPLACE don't combine
                if frameworks and framework_str != (row['framework'] or ''):
                    cursor.execute(
                        "UPDATE experiments SET framework = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (framework_str, experiment_id)
                    )
            else:
                cursor.execute("INSERT INTO experiments (name, framework) VALUES (?, ?)", (exp_name, framework_str))
                experiment_id = cursor.lastrowid

            cursor.executemany("""
                INSERT OR REPLACE INTO documents
                (doc_id, experiment_id, filename, file_path, num_pages, text_length, trace_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    d.get('doc_id'),
                    experiment_id,
                    d.get('filename'),
                    d.get('file_path'),
                    d.get('num_pages'),
                    d.get('text_length'),
                    d.get('trace_id'),
                    json.dumps(d)
                ) for d in doc_list
            ])
        conn.commit()


def store_parsed_batch(parsed_docs: list) -> None:
    """Store multiple parsed documents in a single transaction."""
    if not parsed_docs:
        return

    # Extract data from each item
    doc_list = [doc.get('data', {}) for doc in parsed_docs]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO parsed_docs
            (doc_id, filename, text, text_length, trace_id, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (
                d.get('doc_id'),
                d.get('filename'),
                d.get('text'),
                len(d.get('text', '')) if d.get('text') else 0,
                d.get('trace_id'),
                json.dumps(d)
            ) for d in doc_list
        ])
        conn.commit()


# ========== Pipeline Functions ==========

def store_pipeline(data: Dict) -> None:
    """Store a pipeline record."""
    pipeline_data = data.get('data', {})
    frameworks = pipeline_data.get('frameworks')

    # Get experiment_id
    if pipeline_data.get('experiment_name'):
        experiment_id = get_or_create_experiment_by_name(pipeline_data['experiment_name'], frameworks)
    else:
        experiment_id = get_default_experiment_id()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pipelines
            (pipeline_id, experiment_id, query, total_duration_ms, num_stages, retrieval_id, llm_call_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pipeline_data.get('pipeline_id'),
            experiment_id,
            pipeline_data.get('query'),
            pipeline_data.get('total_duration_ms'),
            pipeline_data.get('num_stages', 0),
            pipeline_data.get('retrieval_id'),
            pipeline_data.get('llm_call_id'),
        ))
        conn.commit()


def store_pipeline_stage(data: Dict) -> None:
    """Store a pipeline stage record."""
    stage_data = data.get('data', {})

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_stages
            (stage_id, pipeline_id, stage_type, stage_name, stage_order, input_count, output_count, duration_ms, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stage_data.get('stage_id'),
            stage_data.get('pipeline_id'),
            stage_data.get('stage_type'),
            stage_data.get('stage_name'),
            stage_data.get('stage_order'),
            stage_data.get('input_count', 0),
            stage_data.get('output_count', 0),
            stage_data.get('duration_ms'),
            json.dumps(stage_data.get('metadata', {})),
        ))
        conn.commit()


def store_stage_chunks_batch(stage_id: str, chunks: List[Dict]) -> None:
    """Store multiple stage chunks in a single transaction."""
    if not chunks:
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO stage_chunks
            (stage_id, chunk_id, doc_id, text, input_rank, output_rank, input_score, output_score, source, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                stage_id,
                c.get('chunk_id'),
                c.get('doc_id'),
                c.get('text', '')[:500],  # Truncate text
                c.get('input_rank'),
                c.get('output_rank'),
                c.get('input_score'),
                c.get('output_score'),
                c.get('source'),
                c.get('status', 'kept'),
            ) for c in chunks
        ])
        conn.commit()


def get_pipelines(experiment_id: int = None, limit: int = 100) -> List[Dict]:
    """Get pipelines, optionally filtered by experiment."""
    with get_db() as conn:
        cursor = conn.cursor()
        if experiment_id:
            cursor.execute(
                "SELECT * FROM pipelines WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM pipelines ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]


def get_pipeline(pipeline_id: str) -> Optional[Dict]:
    """Get a single pipeline with its stages and chunks."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get pipeline
        cursor.execute("SELECT * FROM pipelines WHERE pipeline_id = ?", (pipeline_id,))
        row = cursor.fetchone()
        if not row:
            return None

        pipeline = dict(row)

        # Get stages
        cursor.execute(
            "SELECT * FROM pipeline_stages WHERE pipeline_id = ? ORDER BY stage_order",
            (pipeline_id,)
        )
        stages = []
        for stage_row in cursor.fetchall():
            stage = dict(stage_row)
            stage['metadata'] = json.loads(stage['metadata']) if stage['metadata'] else {}

            # Get chunks for this stage
            cursor.execute(
                "SELECT * FROM stage_chunks WHERE stage_id = ? ORDER BY output_rank, input_rank",
                (stage['stage_id'],)
            )
            stage['chunks'] = [dict(c) for c in cursor.fetchall()]
            stages.append(stage)

        pipeline['stages'] = stages
        return pipeline


def get_pipeline_by_retrieval(retrieval_id: str) -> Optional[Dict]:
    """Get pipeline associated with a retrieval_id."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pipeline_id FROM pipelines WHERE retrieval_id = ?", (retrieval_id,))
        row = cursor.fetchone()
        if row:
            return get_pipeline(row['pipeline_id'])
        return None


# Initialize database on module import
init_db()
