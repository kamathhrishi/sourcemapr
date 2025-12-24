"""
SourcemapR CLI - Command line interface for the observability platform.
"""

import argparse
import sys
import os
import signal
import time
from pathlib import Path

# PID file location
PID_FILE = Path.home() / '.sourcemapr' / 'server.pid'


def get_pid():
    """Get the PID of running server, or None if not running."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process is actually running
            os.kill(pid, 0)  # Doesn't kill, just checks
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            # PID file exists but process isn't running
            PID_FILE.unlink(missing_ok=True)
    return None


def write_pid():
    """Write current PID to file."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def remove_pid():
    """Remove PID file."""
    PID_FILE.unlink(missing_ok=True)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='sourcemapr',
        description='SourcemapR - RAG Observability Platform'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Server command
    server_parser = subparsers.add_parser('server', help='Start the observability server')
    server_parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    server_parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )
    server_parser.add_argument(
        '--background', '-b',
        action='store_true',
        help='Run server in background'
    )

    # Stop command
    subparsers.add_parser('stop', help='Stop the running server')

    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart the server')
    restart_parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    restart_parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )

    # Status command
    subparsers.add_parser('status', help='Check if server is running')

    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear all trace data')
    clear_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    clear_parser.add_argument(
        '--reset',
        action='store_true',
        help='Full reset: also delete experiments and reset frameworks'
    )

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize or reset the database')
    init_parser.add_argument(
        '--reset',
        action='store_true',
        help='Delete existing database and create fresh'
    )

    # Version command
    subparsers.add_parser('version', help='Show version information')

    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Seed database with demo data for showcasing')
    demo_parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing data before seeding demo'
    )

    args = parser.parse_args()

    if args.command == 'server':
        cmd_server(args.host, args.port, args.background)
    elif args.command == 'stop':
        cmd_stop()
    elif args.command == 'restart':
        cmd_restart(args.host, args.port)
    elif args.command == 'status':
        cmd_status()
    elif args.command == 'clear':
        cmd_clear(args.yes, args.reset)
    elif args.command == 'init':
        cmd_init(args.reset)
    elif args.command == 'version':
        from sourcemapr import __version__
        print(f"SourcemapR v{__version__}")
    elif args.command == 'demo':
        cmd_demo(args.clear)
    else:
        parser.print_help()
        sys.exit(1)


def cmd_server(host: str = '0.0.0.0', port: int = 5000, background: bool = False):
    """Start the SourcemapR server."""
    pid = get_pid()
    if pid:
        print(f"Server already running (PID: {pid})")
        print("Use 'sourcemapr stop' to stop it first, or 'sourcemapr restart' to restart")
        sys.exit(1)

    if background:
        # Fork to background
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Server started in background (PID: {pid})")
                print(f"Dashboard: http://localhost:{port}")
                sys.exit(0)
        except OSError as e:
            print(f"Failed to fork: {e}")
            sys.exit(1)

        # Child process continues
        os.setsid()  # Create new session

    # Write PID file
    write_pid()

    # Set up cleanup on exit
    def cleanup(signum=None, frame=None):
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    try:
        from sourcemapr.server.app import run_server as start_server
        start_server(host=host, port=port)
    except ImportError as e:
        print(f"Error: Could not import server module: {e}")
        print("Make sure all dependencies are installed: pip install sourcemapr")
        remove_pid()
        sys.exit(1)
    except Exception as e:
        print(f"Server error: {e}")
        remove_pid()
        sys.exit(1)
    finally:
        remove_pid()


def cmd_stop():
    """Stop the running server."""
    pid = get_pid()
    if not pid:
        print("Server is not running")
        return

    print(f"Stopping server (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for process to stop
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("Server stopped")
                remove_pid()
                return
        # Force kill if still running
        print("Force killing...")
        os.kill(pid, signal.SIGKILL)
        remove_pid()
        print("Server stopped")
    except ProcessLookupError:
        print("Server stopped")
        remove_pid()
    except PermissionError:
        print(f"Permission denied. Try: sudo kill {pid}")
        sys.exit(1)


def cmd_restart(host: str = '0.0.0.0', port: int = 5000):
    """Restart the server."""
    pid = get_pid()
    if pid:
        print(f"Stopping server (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(10):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
        except ProcessLookupError:
            pass
        remove_pid()
        print("Server stopped")
        time.sleep(1)

    print("Starting server...")
    cmd_server(host, port, background=False)


def cmd_status():
    """Check server status."""
    pid = get_pid()
    if pid:
        print(f"Server is running (PID: {pid})")
        print("Dashboard: http://localhost:5000")
    else:
        print("Server is not running")
        print("Start with: sourcemapr server")


def cmd_clear(skip_confirm: bool = False, full_reset: bool = False):
    """Clear all trace data and experiments."""
    if full_reset:
        msg = "This will DELETE ALL data including experiments and frameworks. Continue? [y/N] "
    else:
        msg = "This will delete all traces, documents, data, AND experiments. Continue? [y/N] "

    if not skip_confirm:
        response = input(msg)
        if response.lower() not in ('y', 'yes'):
            print("Cancelled")
            return

    # Clear database directly (more reliable than API)
    print("Clearing database...")
    try:
        from sourcemapr.server import database as db
        if full_reset:
            db.reset_all_data()
            print("All data and experiments cleared (full reset)")
        else:
            # Clear all data including experiments (but keep Default experiment)
            db.clear_all_data()
            # Also delete all experiments except Default
            from sourcemapr.server.database import get_db
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM experiments WHERE name != 'Default'")
                conn.commit()
            print("All data and experiments cleared (Default experiment preserved)")
    except Exception as e:
        print(f"Error clearing data: {e}")
        sys.exit(1)


def cmd_init(reset: bool = False):
    """Initialize or reset the database."""
    from sourcemapr.server import database as db

    if reset:
        if db.DB_PATH.exists():
            response = input(f"Delete existing database at {db.DB_PATH}? [y/N] ")
            if response.lower() not in ('y', 'yes'):
                print("Cancelled")
                return
            db.DB_PATH.unlink()
            print("Existing database deleted")

    print(f"Initializing database at {db.DB_PATH}...")
    db.init_db()
    print("Database initialized successfully")


def cmd_demo(clear_first: bool = False):
    """Seed database with demo data for showcasing the dashboard."""
    from sourcemapr.server import database as db

    if clear_first:
        print("Clearing existing data...")
        db.clear_all_data()

    print("Seeding demo data...")
    _seed_demo_data()
    print("\nDemo data ready!")
    print("Start server with: sourcemapr server")
    print("Then visit: http://localhost:5000")


def _seed_demo_data():
    """Internal function to seed demo data."""
    import json
    import uuid
    from datetime import datetime, timedelta
    from sourcemapr.server.database import (
        init_db,
        get_or_create_experiment_by_name,
        store_document,
        store_parsed,
        store_chunk,
        store_retrieval,
        store_llm_call,
    )

    def generate_id():
        return str(uuid.uuid4())[:8]

    init_db()

    experiment_name = "Demo - Attention Paper"
    experiment_id = get_or_create_experiment_by_name(experiment_name, ["llamaindex"])
    print(f"  Created experiment: {experiment_name}")

    trace_id = generate_id()
    base_time = datetime.now()

    # Sample documents
    documents = [
        {"doc_id": f"doc_{generate_id()}", "filename": "attention_paper.pdf",
         "file_path": "./data/attention_paper.pdf", "num_pages": 15, "text_length": 45000},
        {"doc_id": f"doc_{generate_id()}", "filename": "llama2_paper.pdf",
         "file_path": "./data/llama2_paper.pdf", "num_pages": 77, "text_length": 180000},
        {"doc_id": f"doc_{generate_id()}", "filename": "rag_paper.pdf",
         "file_path": "./data/rag_paper.pdf", "num_pages": 12, "text_length": 32000},
    ]

    # Sample chunks with realistic text
    chunk_texts = {
        "attention_paper.pdf": [
            ("The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism.", 1),
            ("We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.", 1),
            ("An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors.", 3),
            ("We call our particular attention 'Scaled Dot-Product Attention'. The input consists of queries and keys of dimension dk, and values of dimension dv.", 3),
            ("Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.", 4),
        ],
        "llama2_paper.pdf": [
            ("We develop and release Llama 2, a collection of pretrained and fine-tuned large language models ranging in scale from 7 billion to 70 billion parameters.", 1),
            ("Llama 2 is pretrained using an optimized auto-regressive transformer with grouped-query attention (GQA) and a context length of 4096 tokens.", 3),
            ("To create Llama 2-Chat, we use Reinforcement Learning from Human Feedback (RLHF) to align the model with human preferences.", 5),
        ],
        "rag_paper.pdf": [
            ("We explore a general-purpose fine-tuning recipe for retrieval-augmented generation (RAG) — models which combine pre-trained parametric and non-parametric memory.", 1),
            ("RAG models combine the parametric memory of a pre-trained seq2seq transformer with a non-parametric memory via a neural retriever.", 2),
        ],
    }

    all_chunks = []
    for doc in documents:
        store_document({"data": {**doc, "trace_id": trace_id, "experiment_name": experiment_name, "frameworks": ["llamaindex"]}})

        chunks = chunk_texts.get(doc["filename"], [])
        parsed_text = "\n\n".join([c[0] for c in chunks])
        store_parsed({"data": {"doc_id": doc["doc_id"], "filename": doc["filename"], "text": parsed_text, "text_length": len(parsed_text), "trace_id": trace_id}})

        char_idx = 0
        for i, (text, page) in enumerate(chunks):
            chunk_id = f"chunk_{generate_id()}"
            chunk_data = {
                "chunk_id": chunk_id, "doc_id": doc["doc_id"], "index": i, "text": text,
                "text_length": len(text), "page_number": page, "start_char_idx": char_idx,
                "end_char_idx": char_idx + len(text), "metadata": {"source": doc["filename"]},
                "trace_id": trace_id, "experiment_name": experiment_name, "frameworks": ["llamaindex"],
            }
            store_chunk({"data": chunk_data})
            all_chunks.append({**chunk_data, "filename": doc["filename"]})
            char_idx += len(text) + 2

    print(f"  Added {len(documents)} documents, {len(all_chunks)} chunks")

    # Sample queries
    queries = [
        ("What is the attention mechanism in transformers?", [0, 2, 3],
         "The attention mechanism maps a query and key-value pairs to an output. The Transformer uses 'Scaled Dot-Product Attention' where dot products are computed between queries and keys, scaled, and passed through softmax."),
        ("How was Llama 2 trained?", [5, 6, 7],
         "Llama 2 was pretrained using an optimized auto-regressive transformer with grouped-query attention and 4096 token context. It was then fine-tuned using RLHF to create Llama 2-Chat."),
        ("What is retrieval augmented generation?", [8, 9],
         "RAG combines pre-trained parametric memory (seq2seq transformer) with non-parametric memory via a neural retriever, allowing models to access external knowledge during generation."),
    ]

    for i, (query, chunk_indices, response) in enumerate(queries):
        results = [{"chunk_id": all_chunks[j]["chunk_id"], "text": all_chunks[j]["text"],
                    "score": round(0.92 - (k * 0.05), 2), "page": all_chunks[j]["page_number"],
                    "source": all_chunks[j]["filename"]} for k, j in enumerate(chunk_indices) if j < len(all_chunks)]

        store_retrieval({"data": {"query": query, "results": results, "num_results": len(results),
                                  "duration_ms": 150 + i * 20, "trace_id": trace_id,
                                  "experiment_name": experiment_name, "frameworks": ["llamaindex"]}})

        context = "\n".join([r["text"] for r in results])
        messages = [{"role": "system", "content": "Answer based on the provided context."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}]
        store_llm_call({"data": {"model": "gpt-4o-mini", "input_type": "messages", "messages": messages,
                                 "response": response, "prompt_tokens": 200 + i * 50, "completion_tokens": 80,
                                 "total_tokens": 280 + i * 50, "temperature": 0.7, "duration_ms": 800 + i * 100,
                                 "status": "success", "trace_id": trace_id, "experiment_name": experiment_name,
                                 "frameworks": ["llamaindex"]}})

    print(f"  Added {len(queries)} queries with retrievals and LLM calls")


if __name__ == '__main__':
    main()
