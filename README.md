# Python TCP Chat Application

This project is a multi-client TCP chat application written in Python for a Computer Networking course. It allows multiple users to connect to a central server and exchange text messages and binary files in real-time. The application is built using the built-in `socket` and `threading` modules and features a custom network protocol for message framing and file transfer.

## Features

* **Group Chat:** Multiple clients can connect to a central server and broadcast messages to everyone.
* **File Transfer:** Supports sending and receiving any type of binary file between clients, facilitated by the server.
* **Custom Protocol:** Uses a simple `[4-byte length header] + [1-byte type] + [payload]` protocol to handle message framing and differentiation between text and files.
* **Threading:** The server uses a thread per client for concurrent handling. The client uses a separate thread for receiving messages to keep the UI responsive.
* **Basic Commands:** Includes commands like `/users`, `/send <filepath>`, `/help`, and `/quit`.
* **User Experience:** Provides timestamps, clear sender information, prompts for saving received files with original names, and basic error handling.
* **Modular Package:** Code is organized into a `pychat` package for better structure and maintainability.

## Project Structure

```
python-tcp-chat/
├── .gitignore
├── LICENSE
├── README.md                   # This documentation
├── run_client.py               # Run this for the client
├── run_server.py               # Run this for the server
└── pychat/
    ├── __init__.py             # Makes 'pychat' a package
    ├── network_utils.py        # Low-level send/recv logic and protocol
    ├── server.py               # ChatServer class implementation
    └── client.py               # ChatClient class implementation
```

## How It Works

### 1. Network Protocol
Communication relies on sending length-prefixed messages over TCP sockets.
* **Header:** Every message starts with a 4-byte unsigned integer (packed using `struct.pack("!I")`) indicating the total size of the *following* data (Type + Payload).
* **Type:** A single byte indicating the message type (e.g., `\x01` for Text, `\x02` for File).
* **Payload:** The actual content.
    * **Text:** `username::message_text` (UTF-8 encoded)
    * **File:** `username::filename::file_binary_data`
    * **Join/Leave:** `username` or status message (UTF-8 encoded)

The `network_utils.py` module handles packing/unpacking these messages (`send_msg`, `recv_msg`).

### 2. Server (`server.py`)
* The `ChatServer` binds to a host and port and listens for incoming connections.
* For each accepted connection, it spawns a dedicated `_handle_client` thread.
* The `_handle_client` thread first receives a `JOIN` message to register the client's username.
* It then enters a loop, using `recv_msg` to wait for incoming messages from that client.
* Based on the message type, it either:
    * Processes a command (like `/users`).
    * Broadcasts a `TEXT` or `FILE` message to all *other* connected clients using the `_broadcast` method.
* It uses a `threading.Lock` to safely manage the shared dictionary of connected clients.
* If a client disconnects or sends `/quit`, the server removes them and broadcasts a `LEAVE` message.

### 3. Client (`client.py`)
* The `ChatClient` connects to the server's host and port.
* It sends its username in a `JOIN` message.
* It starts a background thread (`_receive_messages`) dedicated to receiving data from the server using `recv_msg`.
* The main thread runs an `start_input_loop` that takes user input from the command line.
* User input is parsed:
    * Commands (`/quit`, `/send`, `/help`, `/users`) are handled locally or sent to the server.
    * Regular text is sent as a `TEXT` message using `send_text`.
    * Files specified with `/send <filepath>` are read, packaged into a `FILE` message payload (`filename::binary_data`), and sent using `send_file`.
* The `_receive_messages` thread handles incoming messages:
    * Prints `TEXT`, `JOIN`, `LEAVE`, and `ERROR` messages with timestamps and formatting.
    * When a `FILE` message arrives, it extracts the filename and binary data, saves the file to the `received_files/` directory, and notifies the user.

## How to Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/msmrexe/python-tcp-chat.git
    cd python-tcp-chat
    ```
2.  **Run the Server:**
    Open a terminal and run:
    ```bash
    python run_server.py
    # Optional: specify host/port
    # python run_server.py --host 127.0.0.1 --port 12345
    ```
    The server will start listening for connections.

3.  **Run Clients:**
    Open one or more *new* terminals and run the client script, providing the server's IP address (use `127.0.0.1` if running on the same machine) and your desired username.
    ```bash
    # Connect client 1
    python run_client.py 127.0.0.1 -u Alice
    
    # Connect client 2 in another terminal
    python run_client.py 127.0.0.1 -u Bob
    # Optional: specify port if the server uses a different one
    # python run_client.py 192.168.1.100 -p 12345 -u Charlie
    ```

4.  **Chat and Send Files:**
    * Type messages and press Enter to send.
    * Use `/send <path/to/your/file.ext>` to send a file (e.g., `/send my_document.pdf` or `/send images/cat.jpg`).
    * Use `/users` to see who is online.
    * Use `/help` for commands.
    * Use `/quit` to disconnect. Received files will appear in a `received_files` sub-directory where you ran the client script.

---

## Author

Feel free to connect or reach out if you have any questions!

* **Maryam Rezaee**
* **GitHub:** [@msmrexe](https://github.com/msmrexe)
* **Email:** [ms.maryamrezaee@gmail.com](mailto:ms.maryamrezaee@gmail.com)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.
