# run_server.py

"""
Starts the PyChat TCP Server.
"""

import argparse
from pychat.server import ChatServer

def main():
    parser = argparse.ArgumentParser(description="PyChat TCP Server")
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help="Host address to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=12000,
        help="Port number to listen on (default: 12000)"
    )
    parser.add_argument(
        '-m', '--max-clients',
        type=int,
        default=10,
        help="Maximum number of concurrent clients (default: 10)"
    )
    args = parser.parse_args()

    server = ChatServer(host=args.host, port=args.port, max_clients=args.max_clients)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down server...")
    finally:
        # Perform any cleanup if needed (though socket closing is handled)
        print("Server shutdown complete.")

if __name__ == "__main__":
    main()
