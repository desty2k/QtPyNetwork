QtPyNetwork
===========

|Build Status| |Docs Status|  |PyPI Downloads|

QtPyNetwork is a small abstraction layer for sending and receiving messages using TCP sockets.

`Check out the complete documentation. <https://desty2k.github.io/QtPyNetwork/readme.html>`__

Server
------

Each server has its own balancer.

Servers:
~~~~~~~~

- TCPServer - listen for TCP connections

Balancers:
~~~~~~~~~~

- NoBalancer - sockets are stored in main thread
- ThreadBalancer - each socket lives in its own thread, which is created dynamically
- ThreadPoolBalancer - constant amount of threads, new sockets are created in threads with least load


Client
------

- TCPClient
- ThreadedTCPClient


Usage
-----

See examples directory for client and server code samples.

TCP Client
~~~~~~~~~~



.. code-block:: python

    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QObject, Slot, QCoreApplication, qInstallMessageHandler

    import sys
    import logging

    from QtPyNetwork.client import TCPClient

    IP = "127.0.0.1"
    PORT = 12500


    class Main(QObject):

        def __init__(self):
            super(Main, self).__init__(None)
            self.logger = logging.getLogger(self.__class__.__name__)

            self.client = TCPClient()
            self.client.message.connect(self.on_message)
            self.client.connected.connect(self.on_connected)
            self.client.failed_to_connect.connect(self.on_failed_to_connect)
            self.client.disconnected.connect(self.close)

        @Slot()
        def start(self):
            self.client.start(IP, PORT)

        @Slot(str, int)
        def on_connected(self, ip: str, port: int):
            self.logger.info(f"Connected to {ip}:{port}")
            self.client.write(b"Kick me plz")

        @Slot(bytes)
        def on_message(self, data: bytes):
            self.logger.info(f"Received: {data}")

        @Slot()
        def on_failed_to_connect(self):
            self.logger.error("Failed to connect")

        @Slot()
        def close(self):
            self.client.close()
            QApplication.instance().quit()


    if __name__ == '__main__':
        logging.basicConfig(
            level=logging.NOTSET,
            format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()])
        logging.getLogger().debug("Logger enabled")

        app = QCoreApplication(sys.argv)
        main = Main()
        main.start()
        sys.exit(app.exec_())



TCPServer + ThreadPoolBalancer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QObject, Slot, QCoreApplication

    import sys
    import logging
    import traceback

    from QtPyNetwork.server import TCPServer
    from QtPyNetwork.balancer import ThreadPoolBalancer
    from QtPyNetwork.models import Client

    IP = "127.0.0.1"
    PORT = 12500


    class Main(QObject):

        def __init__(self):
            super(Main, self).__init__(None)
            self.logger = logging.getLogger(self.__class__.__name__)
            # declare server using ThreadPoolBalancer
            self.server = TCPServer(ThreadPoolBalancer(threads=8))
            # connect signals
            self.server.connected.connect(lambda client, ip, port: client.write(b"Some important data"))
            self.server.disconnected.connect(self.on_disconnected)
            self.server.message.connect(self.on_message)

        @Slot()
        def setup(self):
            # start server
            self.server.start(IP, PORT)

        @Slot(Client, bytes)
        def on_message(self, client: Client, message: bytes):
            # this code will be run everyu time client sends data
            self.logger.info("Received {}: {}".format(client.id(), message))
            if message.decode() == "Kick me plz":
                client.disconnect()

        @Slot(Client)
        def on_disconnected(self, client: Client):
            # do some actions when client disconnects form server
            self.logger.info("Disconnected: {}; Connected: {}".format(client.id(), client.is_connected()))
            self.close()

        @Slot()
        def close(self):
            self.server.close()
            while self.server.is_running():
                self.server.wait()
            QApplication.instance().quit()

.. |Docs Status| image:: https://github.com/desty2k/QtPyNetwork/workflows/docs/badge.svg
   :target: https://desty2k.github.io/QtPyNetwork/
.. |Build Status| image:: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml/badge.svg
   :target: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml
.. |PyPI Downloads| image:: https://img.shields.io/pypi/dm/qtpynetwork
   :target: https://pypi.org/project/QtPyNetwork/
