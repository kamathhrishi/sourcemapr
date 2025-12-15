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

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize or reset the database')
    init_parser.add_argument(
        '--reset',
        action='store_true',
        help='Delete existing database and create fresh'
    )

    # Version command
    subparsers.add_parser('version', help='Show version information')

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
        cmd_clear(args.yes)
    elif args.command == 'init':
        cmd_init(args.reset)
    elif args.command == 'version':
        from sourcemapr import __version__
        print(f"SourcemapR v{__version__}")
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


def cmd_clear(skip_confirm: bool = False):
    """Clear all trace data."""
    if not skip_confirm:
        response = input("This will delete all traces, documents, and data. Continue? [y/N] ")
        if response.lower() not in ('y', 'yes'):
            print("Cancelled")
            return

    try:
        import requests
        response = requests.post('http://localhost:5000/api/clear', timeout=5)
        if response.status_code == 200:
            print("All data cleared")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.ConnectionError:
        # Server not running, clear database directly
        print("Server not running. Clearing database directly...")
        try:
            from sourcemapr.server import database as db
            db.clear_all_data()
            print("All data cleared")
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


if __name__ == '__main__':
    main()
