# pychat/server.py

"""
The main TCP Chat Server logic.
"""

import socket
import threading
import logging
from . import network_utils as net

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

class ChatServer:
    def __init__(self, host='0.0.0.0', port=12000, max_clients=10):
        self.host = host
        self.port = port
        self.max_clients = max_clients
        # Store clients as {socket: username}
        self.clients = {}
        # Lock for thread-safe access to clients dict
        self.clients_lock = threading.Lock()
        self.server_socket = None

    def start(self):
        """ Binds the server socket and starts listening."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reusing the address quickly after server restart
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            logging.info(f"Server listening on {self.host}:{self.port}")
            self._accept_connections()
        except OSError as e:
            logging.error(f"Failed to start server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _accept_connections(self):
        """ Main loop to accept incoming client connections."""
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                logging.info(f"Accepted connection from {address}")
                
                # Start a new thread to handle this client
                thread = threading.Thread(target=self._handle_client, args=(client_socket, address), daemon=True)
                thread.start()
            except OSError:
                logging.info("Server socket closed, shutting down accept loop.")
                break # Exit loop if server socket is closed
            except Exception as e:
                logging.error(f"Error accepting connection: {e}")

    def _broadcast(self, msg_type: bytes, payload: bytes, sender_socket: socket.socket = None):
        """ Sends a message to all connected clients except the sender."""
        with self.clients_lock:
            # Create the full message once
            full_message = msg_type + payload
            header = net.struct.pack(net.HEADER_FORMAT, len(full_message))
            message_to_send = header + full_message
            
            for client_sock in self.clients:
                if client_sock != sender_socket:
                    try:
                        client_sock.sendall(message_to_send)
                    except (BrokenPipeError, OSError):
                        # Handle potential errors if a client disconnected abruptly
                        logging.warning(f"Failed to send message to {self.clients.get(client_sock, 'unknown')}. Connection might be closed.")
                        # Consider removing the client here if needed, but handle_client should catch it

    def _send_direct_message(self, sock: socket.socket, msg_type: bytes, payload: bytes):
        """ Sends a message directly to a specific client."""
        try:
            net.send_msg(sock, msg_type, payload)
        except ConnectionError:
             logging.warning(f"Failed to send direct message to {self.clients.get(sock, 'unknown')}.")

    def _remove_client(self, client_socket: socket.socket):
        """ Removes a client from the list and closes the socket."""
        username = "unknown"
        with self.clients_lock:
            if client_socket in self.clients:
                username = self.clients.pop(client_socket)
        try:
            client_socket.close()
        except OSError:
            pass # Socket likely already closed
        return username

    def _handle_client(self, client_socket: socket.socket, address):
        """ Handles communication with a single client."""
        username = None
        try:
            # 1. Get Username
            while True:
                data = net.recv_msg(client_socket)
                if not data: return # Client disconnected
                
                msg_type, payload = data
                if msg_type == net.MSG_TYPE_JOIN and payload:
                    username = payload.decode('utf-8', errors='ignore')
                    # Check for username collision (optional but good)
                    with self.clients_lock:
                        if username in self.clients.values():
                            self._send_direct_message(client_socket, net.MSG_TYPE_ERROR, b"Username already taken.")
                            username = None # Force retry
                            continue # Ask again
                        self.clients[client_socket] = username
                    logging.info(f"{address} identified as '{username}'")
                    self._broadcast(net.MSG_TYPE_JOIN, f"{username} joined the chat.".encode(), client_socket)
                    self._send_direct_message(client_socket, net.MSG_TYPE_TEXT, b"Welcome! Type /help for commands.")
                    break # Username accepted
                else:
                    # Send error or ignore invalid join message
                    self._send_direct_message(client_socket, net.MSG_TYPE_ERROR, b"Invalid JOIN message.")
                    # Consider closing connection here

            # 2. Main Message Loop
            while True:
                data = net.recv_msg(client_socket)
                if not data: break # Client disconnected

                msg_type, payload = data
                
                # Prepend username for broadcasting text/files
                sender_prefix = f"{username}::".encode() # Use :: as separator

                if msg_type == net.MSG_TYPE_TEXT:
                    message_text = payload.decode('utf-8', errors='ignore')
                    logging.info(f"'{username}' sent text: {message_text[:50]}...")
                    # Handle commands
                    if message_text.startswith('/'):
                        self._handle_command(client_socket, username, message_text)
                    else:
                         self._broadcast(net.MSG_TYPE_TEXT, sender_prefix + payload, client_socket)

                elif msg_type == net.MSG_TYPE_FILE:
                     logging.info(f"'{username}' sent a file.")
                     # Broadcast includes username prefix, type, and original payload (filename::data)
                     self._broadcast(net.MSG_TYPE_FILE, sender_prefix + payload, client_socket)

                # Add handling for other message types if needed

        except ConnectionError:
            logging.info(f"Connection lost for {username or address}")
        except Exception as e:
            logging.error(f"Error handling client {username or address}: {e}")
        finally:
            # Cleanup: Remove client, close socket, notify others
            removed_username = self._remove_client(client_socket)
            if removed_username and removed_username != "unknown":
                logging.info(f"'{removed_username}' disconnected.")
                self._broadcast(net.MSG_TYPE_LEAVE, f"{removed_username} left the chat.".encode())

    def _handle_command(self, client_socket: socket.socket, username: str, command: str):
        """ Processes commands received from a client."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == '/quit':
            # Signal client thread to exit by closing socket from server-side
             self._send_direct_message(client_socket, net.MSG_TYPE_COMMAND, b"/quit_ack")
             # Let the finally block handle cleanup
             client_socket.close() # Force recv_msg to return None in client handler

        elif cmd == '/users':
            with self.clients_lock:
                user_list = ", ".join(self.clients.values())
            self._send_direct_message(client_socket, net.MSG_TYPE_TEXT, f"[Server] Online users: {user_list}".encode())

        elif cmd == '/help':
             help_text = "[Server] Commands:\n/users - List online users\n/send <filepath> - Send a file\n/quit - Disconnect"
             self._send_direct_message(client_socket, net.MSG_TYPE_TEXT, help_text.encode())
        else:
             self._send_direct_message(client_socket, net.MSG_TYPE_ERROR, b"Unknown command. Type /help.")
