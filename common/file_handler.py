import os
import hashlib
import tempfile
 
DEFAULT_CHUNK_SIZE = 1024

def read_file_chunks(path: str, chunk_size: int = DEFAULT_CHUNK_SIZE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def read_file_bytes(path: str) -> bytes:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "rb") as f:
        return f.read()

read_file = read_file_bytes

def write_file(path: str, data: bytes) -> int:
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(path, "wb") as f:
        return f.write(data)

def write_file_from_chunks(path: str, chunks) -> int:
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    total_written = 0
    with open(path, "wb") as f:
        for chunk in chunks:
            written = f.write(chunk)
            total_written += written
    return total_written


def write_file_from_chunks_atomic(path: str, chunks) -> int:
    """Write a client download atomically while preserving an existing target."""
    parent_dir = os.path.dirname(path) or "."
    os.makedirs(parent_dir, exist_ok=True)
    basename = os.path.basename(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{basename}.",
            suffix=".part",
            dir=parent_dir,
            delete=False,
        ) as output:
            temporary_path = output.name
            total_written = 0
            for chunk in chunks:
                total_written += output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        return total_written
    finally:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError:
                pass

def append_to_file(path: str, data: bytes) -> int:
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(path, "ab") as f:
        return f.write(data)

def compute_hash(path: str, algorithm: str = "sha256") -> str:
    supported = ("md5", "sha256")
    if algorithm not in supported:
        raise ValueError(
            f"Unsupported hash algorithm: '{algorithm}'. Supported: {supported}"
        )
    h = hashlib.new(algorithm)
    for chunk in read_file_chunks(path):
        h.update(chunk)

    return h.hexdigest()

def get_file_size(path: str) -> int:
    return os.path.getsize(path)

def file_exists(path: str) -> bool:
    return os.path.isfile(path)

def delete_file(path: str) -> bool:
    if file_exists(path):
        os.remove(path)
        return True
    return False

def list_directory(path: str = ".") -> list[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")
    return os.listdir(path)
