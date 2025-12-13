"""
SourcemapR CLI - Command line interface for the observability platform.
"""

import argparse
import sys


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

    # Version command
    subparsers.add_parser('version', help='Show version information')

    args = parser.parse_args()

    if args.command == 'server':
        run_server(args.host, args.port)
    elif args.command == 'version':
        from sourcemapr import __version__
        print(f"SourcemapR v{__version__}")
    else:
        parser.print_help()
        sys.exit(1)


def run_server(host: str = '0.0.0.0', port: int = 5000):
    """Start the SourcemapR observability server."""
    try:
        from sourcemapr.server.app import run_server as start_server
        start_server(host=host, port=port)
    except ImportError as e:
        print(f"Error: Could not import server module: {e}")
        print("Make sure all dependencies are installed: pip install sourcemapr")
        sys.exit(1)


if __name__ == '__main__':
    main()
