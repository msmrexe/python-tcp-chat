# pychat/network_utils.py

"""
Provides utility functions for sending and receiving
length-prefixed messages over sockets.
"""

import struct
import socket

# Define message type constants
MSG_TYPE_TEXT = b'\x01'
MSG_TYPE_FILE = b'\x02'
MSG_TYPE_JOIN = b'\x03'
MSG_TYPE_LEAVE = b'\x04'
MSG_TYPE_ERROR = b'\x05'
MSG_TYPE_COMMAND = b'\x06' # For commands like /users

# Header format: 4-byte unsigned integer (network byte order)
HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def send_msg(sock: socket.socket, msg_type: bytes, payload: bytes):
    """ Packs message type and payload, adds header, and sends."""
    try:
        message = msg_type + payload
        header = struct.pack(HEADER_FORMAT, len(message))
        sock.sendall(header + message)
    except (BrokenPipeError, OSError) as e:
        print(f"[Network Error] Failed to send message: {e}")
        raise ConnectionError("Failed to send message") from e


def recvall(sock: socket.socket, n: int) -> bytes | None:
    """ Helper function to receive exactly n bytes from a socket."""
    data = bytearray()
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None # Connection closed
            data.extend(packet)
        except (ConnectionResetError, OSError) as e:
             print(f"[Network Error] Connection lost during recvall: {e}")
             return None
    return bytes(data)

def recv_msg(sock: socket.socket) -> tuple[bytes, bytes] | None:
    """ Receives a length-prefixed message (header + type + payload)."""
    # Read the header
    header_data = recvall(sock, HEADER_SIZE)
    if not header_data:
        return None # Connection likely closed

    try:
        msg_len = struct.unpack(HEADER_FORMAT, header_data)[0]
    except struct.error:
        print("[Network Error] Invalid message header received.")
        return None # Invalid header

    # Read the message content (type + payload)
    message_data = recvall(sock, msg_len)
    if not message_data:
        return None # Connection likely closed during payload recv

    # Separate message type and payload
    msg_type = message_data[0:1]
    payload = message_data[1:]

    return msg_type, payload
