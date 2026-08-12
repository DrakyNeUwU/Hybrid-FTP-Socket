# 9. Client CLI and Logging

The CLI displays server connection status, directory listings, human-readable
file sizes, and real upload/download progress. RDT callbacks report committed
or acknowledged bytes and the total size when available.

For `STOR`, `RETR`, `STOU`, and `APPE`, the CLI also prints the actual `150`
reply before RDT work starts and prints `226 Transfer complete` only after the
server's final reply. This is a display change; the TCP/UDP/RDT lifecycle is
unchanged.

Server logs record timestamps, client IP, redacted commands, replies, session
and transfer IDs, transfer mode, byte count, and result. Passwords and file
contents are never logged. Curated CLI/server logs and SHA-256 values are kept
under `docs/evidence/`.
