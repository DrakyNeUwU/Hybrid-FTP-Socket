# 8. Concurrency and Integration

The TCP server uses one handler thread per client and protects the active-session
registry with a lock. Each session has independent command and transfer state.
No global client lock is held while waiting for UDP acknowledgements.

Transfer cancellation shares an event across command, RDT, and filesystem
layers. ABOR and disconnect wake or close the data socket, stop the worker,
remove temporary upload data, clear session state, and return the correct FTP
reply. End-to-end tests cover concurrent PASV clients, ABOR, and disconnect.
