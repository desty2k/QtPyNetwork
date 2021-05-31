Changelog
=========

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

- 0.4:
    - Fix large messages not being received
    - Add method to set encryption key for client
    - Add method to set custom JSON encoder and decoder
    - Remove default JSON encoder and decoder
    - Remove messages logging
    - Clean the code

- 0.3:
    - Clean the code
    - Automatically remove clients and threads on disconnection
    - Update functions names

- 0.2:
    - Update imports for Device model
    - Add logger name kwarg

- 0.1:
    - Initial version
    - Create repo
