"""Server-side filesystem operations with path-traversal protection.

All filesystem operations in FTP handlers must use this module. It validates
paths against the FTP root and provides path resolution, listings, directory
management, metadata, deletion, and renaming helpers.
"""

import os
import stat
import time


# ============================================================
# VALIDATE PATH — prevent path traversal
# ============================================================

def validate_path(base_dir: str, target_path: str) -> bool:
    """
    Return whether ``target_path`` is inside the FTP-root ``base_dir``.

    Both paths are resolved with ``realpath`` so symlink escapes and ``..``
    traversal are detected. Appending ``os.sep`` to the root prevents a path
    such as ``/srv/ftp_backup`` from being mistaken for a child of ``/srv/ftp``.

    Args:
        base_dir: FTP root directory (sandbox boundary).
        target_path: Path to validate.

    Returns:
        True when the target is inside or equal to ``base_dir``.
    """
    # Resolve symlinks and ``..`` components.
    real_base = os.path.realpath(base_dir)
    real_target = os.path.realpath(target_path)

    # Allow the FTP root itself.
    if real_target == real_base:
        return True

    # Require a child path; the separator avoids /ftp versus /ftp_backup.
    return real_target.startswith(real_base + os.sep)


# ============================================================
# RESOLVE PATH — safely convert relative paths to absolute paths
# ============================================================

def resolve_path(base_dir: str, cwd: str, relative_path: str) -> str:
    """
    Resolve a client path safely to an absolute path within the FTP root.

    FTP-style absolute paths are relative to ``base_dir``; relative paths are
    resolved from ``cwd``. The result is normalized and validated before use.

    Args:
        base_dir: FTP root directory.
        cwd: Current session directory (absolute path).
        relative_path: Client path, relative or FTP-style absolute.

    Returns:
        Validated absolute path.

    Raises:
        PermissionError: If the path escapes the sandbox.
    """
    if not relative_path:
        # Commands without a path (for example LIST) use the current directory.
        resolved_cwd = os.path.realpath(cwd)
        if not validate_path(base_dir, resolved_cwd):
            raise PermissionError("Current directory is outside the FTP root.")
        return resolved_cwd

    # FTP clients use Unix-style paths even on Windows, where ``/docs`` is not
    # considered absolute by os.path.isabs().
    is_absolute = os.path.isabs(relative_path) or relative_path.startswith("/")

    if is_absolute:
        # An FTP absolute path is rooted at ``base_dir``.
        stripped = relative_path.lstrip("/\\")
        resolved = os.path.join(base_dir, stripped)
    else:
        # A relative path is rooted at ``cwd``.
        resolved = os.path.join(cwd, relative_path)

    # Resolve symlink + normalize
    resolved = os.path.realpath(resolved)

    # The final path must remain inside the sandbox.
    if not validate_path(base_dir, resolved):
        raise PermissionError(
            f"Access denied: path '{relative_path}' is outside the FTP root directory."
        )

    return resolved


# ============================================================
# LIST DIRECTORY
# ============================================================

def list_directory(path: str, base_dir: str | None = None) -> list:
    """
    Return detailed metadata for files and directories in ``path``.

    ``os.scandir`` provides entry metadata efficiently. Directories sort before
    files, and each group is sorted case-insensitively by name. This supports
    the FTP LIST command.

    Args:
        path: Validated directory path to list.

    Returns:
        Dictionaries with name, size, type, permissions, and modified fields.

    Raises:
        NotADirectoryError: If path is not a directory.
        FileNotFoundError: If path does not exist.
    """
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise NotADirectoryError(f"Not a directory: '{path}'")
        raise FileNotFoundError(f"Directory not found: '{path}'")

    entries = []

    # scandir returns metadata-bearing DirEntry values efficiently.
    with os.scandir(path) as scanner:
        for entry in scanner:
            try:
                if base_dir is not None and not validate_path(base_dir, entry.path):
                    # Do not expose metadata outside the root through a symlink.
                    continue
                entry_stat = entry.stat()

                entries.append({
                    "name": entry.name,
                    "size": entry_stat.st_size if entry.is_file() else 0,
                    "type": "dir" if entry.is_dir() else "file",
                    "permissions": _format_permissions(entry_stat.st_mode),
                    "modified": _format_mtime(entry_stat.st_mtime),
                })
            except (PermissionError, OSError):
                # Skip unreadable entries while listing the remaining entries.
                continue

    # Directories first, then names case-insensitively.
    entries.sort(key=lambda e: (e["type"] != "dir", e["name"].lower()))

    return entries


def list_names(path: str, base_dir: str | None = None) -> list:
    """
    Return names only, without metadata, for the FTP NLST command.

    Args:
        path: Validated directory path.

    Returns:
        Alphabetically sorted entry names.
    """
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise NotADirectoryError(f"Not a directory: '{path}'")
        raise FileNotFoundError(f"Directory not found: '{path}'")

    with os.scandir(path) as scanner:
        names = [
            entry.name
            for entry in scanner
            if base_dir is None or validate_path(base_dir, entry.path)
        ]
    names.sort(key=str.lower)
    return names


# ============================================================
# CREATE / REMOVE DIRECTORIES
# ============================================================

def make_directory(base_dir: str, path: str) -> str:
    """
    Create a directory after validating that it is inside the FTP sandbox.

    Args:
        base_dir: FTP root directory.
        path: Directory path resolved by resolve_path.

    Returns:
        Absolute path of the created directory.

    Raises:
        PermissionError: If the path is outside the sandbox.
        FileExistsError: If the directory already exists.
    """
    if not validate_path(base_dir, os.path.dirname(path)):
        raise PermissionError(
            f"Access denied: cannot create directory outside FTP root."
        )

    if os.path.exists(path):
        raise FileExistsError(f"Directory already exists: '{path}'")

    os.makedirs(path)
    return os.path.realpath(path)


def remove_directory(base_dir: str, path: str) -> None:
    """
    Remove an empty directory after validating it is inside the FTP sandbox.

    This intentionally follows RFC 959: RMD removes empty directories only.

    Args:
        base_dir: FTP root directory.
        path: Resolved directory path to remove.

    Raises:
        PermissionError: If outside the sandbox or equal to the FTP root.
        FileNotFoundError: If the directory does not exist.
        NotADirectoryError: If path is a file.
        OSError: If the directory is not empty.
    """
    if not validate_path(base_dir, path):
        raise PermissionError(
            f"Access denied: cannot remove directory outside FTP root."
        )

    # Never remove the FTP root itself.
    if os.path.realpath(path) == os.path.realpath(base_dir):
        raise PermissionError("Cannot remove the FTP root directory.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: '{path}'")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"Not a directory: '{path}'")

    # os.rmdir() raises OSError when the directory is not empty.
    os.rmdir(path)


# ============================================================
# FILE INFORMATION — used by STAT, MDTM, SIZE, DELE, RNFR/RNTO
# ============================================================

def get_entry_info(path: str, base_dir: str | None = None) -> dict:
    """
    Return metadata for one file or directory.

    Args:
        path: Validated path.

    Returns:
        dict: {name, size, type, permissions, modified}
    """
    if base_dir is not None and not validate_path(base_dir, path):
        raise PermissionError("Access denied: path outside FTP root.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: '{path}'")

    s = os.stat(path)
    return {
        "name": os.path.basename(path),
        "size": s.st_size,
        "type": "dir" if os.path.isdir(path) else "file",
        "permissions": _format_permissions(s.st_mode),
        "modified": _format_mtime(s.st_mtime),
    }


def delete_file(base_dir: str, path: str) -> None:
    """
    Delete one file after validating it is inside the FTP sandbox.

    Args:
        base_dir: FTP root directory.
        path: Resolved file path to delete.

    Raises:
        PermissionError: If the path is outside the sandbox.
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If path is a directory; use RMD instead.
    """
    if not validate_path(base_dir, path):
        raise PermissionError("Access denied: path outside FTP root.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: '{path}'")

    if os.path.isdir(path):
        raise IsADirectoryError(
            f"'{path}' is a directory. Use RMD to remove directories."
        )

    os.remove(path)


def rename_entry(base_dir: str, old_path: str, new_path: str) -> None:
    """
    Rename a file or directory for the RNFR/RNTO command pair.

    Both paths must remain in the sandbox, the source must exist, and the
    destination must not exist to prevent accidental replacement.

    Args:
        base_dir: FTP root directory.
        old_path: Resolved source path.
        new_path: Resolved destination path.

    Raises:
        PermissionError: If either path is outside the sandbox.
        FileNotFoundError: If old_path does not exist.
        FileExistsError: If new_path already exists.
    """
    if not validate_path(base_dir, old_path):
        raise PermissionError("Access denied: source path outside FTP root.")
    if not validate_path(base_dir, new_path):
        raise PermissionError("Access denied: destination path outside FTP root.")

    if not os.path.exists(old_path):
        raise FileNotFoundError(f"Source not found: '{old_path}'")
    if os.path.exists(new_path):
        raise FileExistsError(f"Destination already exists: '{new_path}'")

    os.rename(old_path, new_path)


# ============================================================
# HELPER FUNCTIONS — private functions (the _ prefix means internal use)
# ============================================================

def _format_permissions(mode: int) -> str:
    """
    Convert a mode such as ``0o755`` to an rwx string such as ``rwxr-xr-x``.
    """
    perms = ""
    perms += "r" if mode & stat.S_IRUSR else "-"
    perms += "w" if mode & stat.S_IWUSR else "-"
    perms += "x" if mode & stat.S_IXUSR else "-"
    perms += "r" if mode & stat.S_IRGRP else "-"
    perms += "w" if mode & stat.S_IWGRP else "-"
    perms += "x" if mode & stat.S_IXGRP else "-"
    perms += "r" if mode & stat.S_IROTH else "-"
    perms += "w" if mode & stat.S_IWOTH else "-"
    perms += "x" if mode & stat.S_IXOTH else "-"
    return perms


def _format_mtime(timestamp: float) -> str:
    """
    Convert a Unix timestamp to the FTP MDTM format, YYYYMMDDhhmmss.

    Args:
        timestamp: Unix timestamp from os.stat().st_mtime.

    Returns:
        A 14-character YYYYMMDDhhmmss string.
    """
    return time.strftime("%Y%m%d%H%M%S", time.localtime(timestamp))
