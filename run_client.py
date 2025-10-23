# run_client.py

"""
Starts the PyChat TCP Client.
"""

import argparse
from pychat.client import ChatClient

def main():
    parser = argparse.ArgumentParser(description="PyChat TCP Client")
    parser.add_argument(
        'host',
        help="Server host address/IP to connect to."
    )
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=12000,
        help="Server port number (default: 12000)"
    )
    parser.add_argument(
        '-u', '--username',
        required=True,
        help="Your username for the chat."
    )
    args = parser.parse_args()

    client = ChatClient(host=args.host, port=args.port, username=args.username)
    client.run() # Connects and starts the input loop

if __name__ == "__main__":
    main()
