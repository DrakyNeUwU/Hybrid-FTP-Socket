# 9. Client CLI and Logging

The CLI displays server connection status, directory listings, human-readable
file sizes, and real upload/download progress. RDT callbacks report committed
or acknowledged bytes and the total size when available.

Server logs record timestamps, client IP, redacted commands, replies, session
and transfer IDs, transfer mode, byte count, and result. Passwords and file
contents are never logged. Curated CLI/server logs and SHA-256 values are kept
under `docs/evidence/`.
