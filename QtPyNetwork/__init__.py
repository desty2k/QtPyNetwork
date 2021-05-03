"""There are two servers available - QBalancedServer and QThreadedServer. First one has constant amount of threads.
When new client connects, server checks which worker has the least amount of active sockets and passes socket
descriptor to this thread. QThreadedServer creates new thread for each connected device.

QThreadedClient is socket client, that keeps socket in separate thread.

Features:
    - Fernet encrypted communication
    - slots executed inside threads
    - signals for each event - connected, disconnected, error, etc.

Important:
    - messages must be dicts
    - encryption key must be Fernet key
    - to disable encryption, set b"" as key
    - servers can be subclassed, but handlers should not
"""

__version__ = "0.4"
