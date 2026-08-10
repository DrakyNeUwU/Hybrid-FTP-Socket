# 6. Filesystem Security

All client paths are resolved and validated against the FTP root before use.
`realpath` prevents `..` traversal and symlink escape. Directory listing,
metadata, creation, deletion, and rename operations all use the same boundary.

Uploads are binary-safe and use temporary `.part` files followed by atomic
replacement. Cancellation and failure remove temporary data. Per-path locking
serializes related writes while allowing unrelated paths to proceed concurrently.
Tests cover traversal, symlink handling, metadata, atomic lifecycle, and
cleanup.
