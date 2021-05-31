"""QtPyNetwork is small abstraction layer for sending and receiving messages (JSON dicts) using TCP sockets.
Messages can be encrypted with Fernet key.

There are two servers available - QBalancedServer and QThreadedServer. First one has constant amount of threads.
When new client connects, server checks which worker has the least amount of active sockets and passes socket
descriptor to this thread. QThreadedServer creates new thread for each connected device.

QThreadedClient is socket client, that keeps socket in separate thread.

Features:
- Fernet encrypted communication
- every message write and read call is executed inside thread
- signals for each event - connected, disconnected, error, etc.
- a different encryption key can be assigned for each client
- methods for setting custom JSON encoder and decoder

Important:
- messages must be dicts
- encryption key must be Fernet key
- to disable encryption, set b"" as key
- servers can be subclassed, but handlers should not be
"""

__version__ = "0.4.3"
