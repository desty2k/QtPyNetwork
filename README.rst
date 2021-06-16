QtPyNetwork
===========

|Build Status|  |PyPI Downloads|

QtPyNetwork is a small abstraction layer for sending and receiving messages using TCP sockets.

There are two servers available:

- QBalancedServer:
- QThreadedServer

The first one has constant amount of threads.
When new client connects, server checks which worker has the least amount of active sockets and passes socket
descriptor to this thread. QThreadedServer creates new thread for each connected device.

QThreadedClient is socket client, that keeps socket in separate thread.

Features
--------

- every message write and read call is executed inside thread
- signals for each event - connected, disconnected, error, etc.


Usage
-----

See examples directory for client and server code samples.

Server
~~~~~~

You can use both composition and inheritance to use server.

Composition
^^^^^^^^^^^

.. code-block:: python

    from qtpy.QtCore import QObject, Slot, QCoreApplication

    import sys
    import logging

    from QtPyNetwork.server import QBalancedServer
    from QtPyNetwork.models import Device

    IP, PORT = "127.0.0.1", 12500


    class Main(QObject):

        def __init__(self):
            super(Main, self).__init__(None)
            self.logger = logging.getLogger(self.__class__.__name__)

        @Slot()
        def start():
            self.srv = QBalancedServer()
            self.srv.connected.connect(self.on_connected)
            self.srv.disconnected.connect(self.on_disconnected)
            self.srv.message.connect(self.on_message)
            self.srv.start(IP, PORT)

        @Slot(Device)
        def on_connected(device: Device):
            self.logger.info("New device connected: {}".format(device.id()))

        @Slot(Device, bytes)
        def on_message(self, device: Device, message: bytes):
            self.logger.info("Received from {}: {}".format(device.id(), message))

        @Slot(Device)
        def on_disconnected(self, device: Device):
            self.logger.info("Device {} disconnected".format(device.id()))
            self.close()

    if __name__ == '__main__':
        logging.basicConfig(level=logging.NOTSET)
        app = QCoreApplication(sys.argv)
        main = Main()
        main.start()
        sys.exit(app.exec_())


Inheritance
^^^^^^^^^^^

.. code-block:: python

    from qtpy.QtCore import QObject, Slot, QCoreApplication

    import sys
    import logging

    from QtPyNetwork.server import QBalancedServer
    from QtPyNetwork.models import Device

    IP, PORT = "127.0.0.1", 12500


    class Main(QBalancedServer):

        def __init__(self):
            super(Main, self).__init__(None)
            self.logger = logging.getLogger(self.__class__.__name__)

        @Slot(Device)
        def on_connected(device: Device):
            self.logger.info("New device connected: {}".format(device.id()))

        @Slot(Device, bytes)
        def on_message(self, device: Device, message: bytes):
            self.logger.info("Received from {}: {}".format(device.id(), message))

        @Slot(Device)
        def on_disconnected(self, device: Device):
            self.logger.info("Device {} disconnected".format(device.id()))
            self.close()

    if __name__ == '__main__':
        logging.basicConfig(level=logging.NOTSET)
        app = QCoreApplication(sys.argv)
        main = Main()
        main.start(IP, PORT)
        sys.exit(app.exec_())


.. |Build Status| image:: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml/badge.svg
   :target: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml
.. |PyPI Downloads| image:: https://img.shields.io/pypi/dm/qtpynetwork
   :target: https://pypi.org/project/QtPyNetwork/
