Changelog
=========

- 0.7.0:
    - Complete code rewrite
    - Split servers into servers and balancers
    - Add abstract classes for servers, balancers and clients
    - Add new balancer: NoBalancer
    - Fix bug with closing unconneccted client
    - Create separate buffer class for reading and writing data
    - Rename Device to Client
    - Emit Exception via signal instead of string
    - Update examples

- 0.6.1:
    - Fix ``setSocketDescriptor`` failing on Python 3.10
    - Get ``long_description`` for PyPi by reading ``README.rst``
    - Remove unused depedency ``cryptography``

- 0.6.0:
    - Use private classes where possible
    - Add `\_\_all__` variable to modules
    - Add issues and docs links to PyPI
    - Change development status to stable
    - Update readme
    - Fix mistakes in docs

- 0.5.3:
    - Update docs
    - Add docs workflow

- 0.5.2:
    - Update description for PyPI
    - Update PyPI classifiers and keywords
    - Fix bandit error (No such file or directory) in safety job

- 0.5.1:
    - Make all variables protected in Device class
    - Add positional argument `server` for Device model
    - Add getters for Device model: ip, port, etc.
    - Update write and kick methods for Device class, remove signals
    - Update readme and examples (replace get_id() with id())

- 0.5.0:
    - Add `kick` method for Device
    - Emit Device instead of device_id on signals: connected, disconnected, message, error
    - Remove JSON encoding
    - Remove Fernet encryption
    - Send `bytes` instead of `dict`
    - Use `joined_lower` for function names

- 0.4.4:
    - Fix tox build workflow
    - Fix generating changelog

- 0.4.3:
    - Add build and deploy workflows
    - Add tox config
    - Add argsparser

- 0.4.2:
    - Add write method for device model
    - Remove logger from device model

- 0.4.1:
    - Fix messages being added to buffer even if they were received in full
    - Add method for creating worker threads in QBalancedServer
    - Add info about project to readme
    - Restore old key after clearing custom encryption key

- 0.4.0:
    - Fix large messages not being received
    - Add method to set encryption key for client
    - Add method to set custom JSON encoder and decoder
    - Remove default JSON encoder and decoder
    - Remove messages logging
    - Clean the code

- 0.3.0:
    - Clean the code
    - Automatically remove clients and threads on disconnection
    - Update functions names

- 0.2.0:
    - Update imports for Device model
    - Add logger name kwarg

- 0.1.0:
    - Initial version
    - Create repo
