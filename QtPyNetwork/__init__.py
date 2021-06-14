"""QtPyNetwork is a small abstraction layer for sending and receiving messages using TCP sockets.

There are two servers available:

- QBalancedServer:
- QThreadedServer

The first one has constant amount of threads.
When new client connects, server checks which worker has the least amount of active sockets and passes socket
descriptor to this thread. QThreadedServer creates new thread for each connected device.

QThreadedClient is socket client, that keeps socket in separate thread.

Features

- every message write and read call is executed inside thread
- signals for each event - connected, disconnected, error, etc.
"""

__version__ = "0.5.0"
