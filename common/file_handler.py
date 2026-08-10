import os
import hashlib
 
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
