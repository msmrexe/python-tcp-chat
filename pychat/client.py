# pychat/client.py

"""
The main TCP Chat Client logic.
"""

import socket
import threading
import logging
import os
import time
from datetime import datetime
from . import network_utils as net

# Configure logging for client-side messages
logging.basicConfig(level=logging.INFO, format='%(message)s') # Simpler format for client

class ChatClient:
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.client_socket = None
        self.receive_thread = None
        self.running = True
        # Directory to save received files
        self.download_dir = "received_files"
        os.makedirs(self.download_dir, exist_ok=True)

    def connect(self):
        """ Establishes connection to the server and sends username."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            logging.info(f"Connected to server at {self.host}:{self.port}")
            
            # Send JOIN message with username
            net.send_msg(self.client_socket, net.MSG_TYPE_JOIN, self.username.encode())
            
            # Start the receiving thread
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            return True
            
        except ConnectionRefusedError:
            logging.error("Connection refused. Is the server running?")
            return False
        except OSError as e:
            logging.error(f"Failed to connect: {e}")
            return False
        except ConnectionError as e:
            logging.error(f"Network error during connection: {e}")
            return False

    def _receive_messages(self):
        """ Target function for the thread that receives messages."""
        while self.running:
            try:
                data = net.recv_msg(self.client_socket)
                if not data:
                    logging.info("Disconnected from server.")
                    self.running = False
                    break # Exit thread

                msg_type, payload = data
                timestamp = datetime.now().strftime('%H:%M:%S')

                if msg_type == net.MSG_TYPE_TEXT:
                    # Check for server messages vs user messages
                    if payload.startswith(b"[Server]"):
                        print(f"\n[{timestamp}] {payload.decode('utf-8', errors='ignore')}")
                    else:
                        try:
                            sender, message = payload.split(b"::", 1)
                            print(f"\n[{timestamp}] {sender.decode()}: {message.decode('utf-8', errors='ignore')}")
                        except ValueError: # Handle messages without '::' (e.g., initial welcome)
                             print(f"\n[{timestamp}] [Server]: {payload.decode('utf-8', errors='ignore')}")
                    print(f"{self.username}> ", end="", flush=True) # Re-prompt user

                elif msg_type == net.MSG_TYPE_FILE:
                    try:
                        sender_and_filename, filedata = payload.split(b"::", 1)
                        sender, filename_bytes = sender_and_filename.split(b"::")
                        filename = filename_bytes.decode('utf-8', errors='ignore')
                        print(f"\n[{timestamp}] {sender.decode()} sent a file: '{filename}' ({len(filedata)} bytes)")
                        
                        # Save the file
                        save_path = os.path.join(self.download_dir, filename)
                        try:
                             with open(save_path, "wb") as f:
                                 f.write(filedata)
                             print(f"[File saved to: {save_path}]")
                        except IOError as e:
                             print(f"[Error saving file '{filename}': {e}]")
                             
                    except ValueError:
                        print(f"\n[{timestamp}] [Error]: Received malformed file message.")
                    print(f"{self.username}> ", end="", flush=True) # Re-prompt user

                elif msg_type == net.MSG_TYPE_JOIN:
                    print(f"\n[{timestamp}] {payload.decode('utf-8', errors='ignore')}")
                    print(f"{self.username}> ", end="", flush=True)

                elif msg_type == net.MSG_TYPE_LEAVE:
                    print(f"\n[{timestamp}] {payload.decode('utf-8', errors='ignore')}")
                    print(f"{self.username}> ", end="", flush=True)

                elif msg_type == net.MSG_TYPE_ERROR:
                    print(f"\n[{timestamp}] [Server Error]: {payload.decode('utf-8', errors='ignore')}")
                    print(f"{self.username}> ", end="", flush=True)

                elif msg_type == net.MSG_TYPE_COMMAND:
                    if payload == b"/quit_ack":
                         logging.info("Quit acknowledged by server. Disconnecting.")
                         self.running = False
                         break # Exit thread

            except ConnectionError:
                if self.running: # Avoid duplicate message if already quitting
                    logging.info("Connection to server lost.")
                self.running = False
                break
            except Exception as e:
                if self.running:
                    logging.error(f"Error receiving message: {e}")
                self.running = False
                break
                
        # Attempt graceful socket close when thread exits
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError:
                 pass # Socket might already be closed
        print("Receive thread terminated.") # For debugging

    def send_text(self, message: str):
        """ Sends a text message."""
        try:
            net.send_msg(self.client_socket, net.MSG_TYPE_TEXT, message.encode())
        except ConnectionError:
            logging.error("Cannot send message. Connection lost.")
            self.running = False

    def send_file(self, filepath: str):
        """ Sends a file message."""
        if not os.path.isfile(filepath):
            logging.error(f"File not found: '{filepath}'")
            return
            
        try:
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                filedata = f.read()
                
            # Payload: filename::filedata
            payload = filename.encode() + b"::" + filedata
            net.send_msg(self.client_socket, net.MSG_TYPE_FILE, payload)
            logging.info(f"Sent file '{filename}' ({len(filedata)} bytes)")
            
        except IOError as e:
            logging.error(f"Error reading file '{filepath}': {e}")
        except ConnectionError:
            logging.error("Cannot send file. Connection lost.")
            self.running = False
        except Exception as e:
            logging.error(f"Error sending file: {e}")

    def start_input_loop(self):
        """ Starts the main loop for user input."""
        logging.info("You can start chatting. Type /help for commands.")
        try:
            while self.running:
                message = input(f"{self.username}> ")
                if not self.running: break # Check if receive_thread stopped

                if not message: continue

                if message.lower() == '/quit':
                    self.send_text(message) # Send /quit command to server
                    self.running = False
                    break # Exit input loop

                elif message.lower().startswith('/send '):
                    filepath = message[6:].strip()
                    if filepath:
                        self.send_file(filepath)
                    else:
                        print("Usage: /send <path/to/your/file>")

                elif message.lower() == '/help':
                     print("Commands:\n  /users - List online users\n  /send <filepath> - Send a file\n  /quit - Disconnect")

                elif message.lower() == '/users':
                     self.send_text(message) # Let server handle /users

                else:
                    self.send_text(message)
        except KeyboardInterrupt:
            logging.info("Ctrl+C detected. Disconnecting...")
            if self.running:
                 self.send_text("/quit")
            self.running = False
        finally:
             print("Closing client...")
             # Wait briefly for receive thread to potentially close socket first
             time.sleep(0.5)
             if self.client_socket and self.running is False:
                 try:
                    self.client_socket.close()
                 except OSError:
                     pass
             # Ensure receive thread has finished if still running
             if self.receive_thread and self.receive_thread.is_alive():
                 self.receive_thread.join(timeout=1.0)
             print("Client closed.")

    def run(self):
        """ Connects and starts the input loop."""
        if self.connect():
            self.start_input_loop()
