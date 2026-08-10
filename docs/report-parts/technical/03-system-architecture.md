# 3. System Architecture

The client and server use TCP for control. A client handler parses CRLF-framed
commands, owns a per-client session, and calls the filesystem and transfer
boundaries. The filesystem service resolves every client path within the FTP
root and uses atomic temporary-file cleanup. UDP transfers use RDT START, DATA,
ACK, FIN, and ABORT packets.

The architecture keeps ownership clear: the command layer owns replies and
session state, the RDT layer owns transfer protocol state, and the filesystem
layer owns paths, file handles, locks, and temporary files.
