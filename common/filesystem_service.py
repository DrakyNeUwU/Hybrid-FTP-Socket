"""Safe, thread-aware filesystem API shared by Roles A, B, and C."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
import shutil
import tempfile
import threading
import uuid
from collections.abc import Iterable, Iterator

from common.dir_manager import (
    delete_file,
    get_entry_info,
    list_directory,
    list_names,
    make_directory,
    remove_directory,
    rename_entry,
    resolve_path,
    validate_path,
)
from common.file_handler import compute_hash, get_file_size, read_file_chunks


class FilesystemOperationError(Exception):
    """Structured error which Role A can map directly to an FTP reply."""

    def __init__(self, operation: str, reply_code: int, message: str) -> None:
        super().__init__(message)
        self.operation = operation
        self.reply_code = reply_code
        self.message = message


class TransferCancelledError(FilesystemOperationError):
    """Raised when ABOR cancels a filesystem transfer."""

    def __init__(self, operation: str = "transfer") -> None:
        super().__init__(operation, 426, "Transfer aborted.")


@dataclass(frozen=True)
class UploadResult:
    """Result returned after a completed upload is committed."""

    path: str
    bytes_written: int

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)


class PathLockRegistry:
    """Provide per-path locks without serializing unrelated files."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, tuple[threading.RLock, int]] = {}

    @staticmethod
    def _key(path: str) -> str:
        return os.path.normcase(os.path.realpath(path))

    @contextmanager
    def acquire(self, *paths: str) -> Iterator[None]:
        keys = sorted({self._key(path) for path in paths})
        locks: list[threading.RLock] = []

        with self._guard:
            for key in keys:
                lock, users = self._locks.get(key, (threading.RLock(), 0))
                self._locks[key] = (lock, users + 1)
                locks.append(lock)

        for lock in locks:
            lock.acquire()
        try:
            yield
        finally:
            for lock in reversed(locks):
                lock.release()
            with self._guard:
                for key in keys:
                    lock, users = self._locks[key]
                    if users == 1:
                        del self._locks[key]
                    else:
                        self._locks[key] = (lock, users - 1)


class FilesystemService:
    """Root-confined filesystem operations used by TCP and UDP modules."""

    def __init__(self, root_dir: str) -> None:
        self.root_dir = os.path.realpath(root_dir)
        if not os.path.isdir(self.root_dir):
            raise ValueError(f"FTP root is not a directory: '{root_dir}'")
        self._locks = PathLockRegistry()

    def resolve(self, cwd: str, client_path: str = "") -> str:
        return self._call("resolve", resolve_path, self.root_dir, cwd, client_path)

    def display_path(self, path: str) -> str:
        resolved = os.path.realpath(path)
        if not validate_path(self.root_dir, resolved):
            raise FilesystemOperationError("pwd", 550, "Path is outside FTP root.")
        relative = os.path.relpath(resolved, self.root_dir)
        if relative == ".":
            return "/"
        return "/" + relative.replace(os.sep, "/")

    def change_directory(self, cwd: str, client_path: str) -> str:
        path = self.resolve(cwd, client_path)
        if not os.path.isdir(path):
            self._raise_for_path(path, "cwd", directory=True)
        return path

    def parent_directory(self, cwd: str) -> str:
        if os.path.realpath(cwd) == self.root_dir:
            return self.root_dir
        return self.change_directory(cwd, "..")

    def list(self, cwd: str, client_path: str = "") -> list[dict]:
        path = self.resolve(cwd, client_path)
        return self._call("list", list_directory, path, self.root_dir)

    def names(self, cwd: str, client_path: str = "") -> list[str]:
        path = self.resolve(cwd, client_path)
        return self._call("nlst", list_names, path, self.root_dir)

    def stat(self, cwd: str, client_path: str) -> dict:
        path = self.resolve(cwd, client_path)
        return self._call("stat", get_entry_info, path, self.root_dir)

    def size(self, cwd: str, client_path: str) -> int:
        path = self.prepare_retrieve(cwd, client_path)
        return self._call("size", get_file_size, path)

    def modified_time(self, cwd: str, client_path: str) -> str:
        return self.stat(cwd, client_path)["modified"]

    def hash(self, cwd: str, client_path: str, algorithm: str = "sha256") -> str:
        path = self.prepare_retrieve(cwd, client_path)
        return self._call("hash", compute_hash, path, algorithm)

    def make_directory(self, cwd: str, client_path: str) -> str:
        path = self.resolve(cwd, client_path)
        return self._call("mkdir", make_directory, self.root_dir, path)

    def remove_directory(self, cwd: str, client_path: str) -> None:
        path = self.resolve(cwd, client_path)
        with self._locks.acquire(path):
            self._call("rmdir", remove_directory, self.root_dir, path)

    def delete(self, cwd: str, client_path: str) -> None:
        path = self.resolve(cwd, client_path)
        with self._locks.acquire(path):
            self._call("delete", delete_file, self.root_dir, path)

    def rename(self, cwd: str, old_path: str, new_path: str) -> None:
        source = self.resolve(cwd, old_path)
        destination = self.resolve(cwd, new_path)
        with self._locks.acquire(source, destination):
            self._call(
                "rename", rename_entry, self.root_dir, source, destination
            )

    def prepare_retrieve(self, cwd: str, client_path: str) -> str:
        path = self.resolve(cwd, client_path)
        if not os.path.isfile(path):
            self._raise_for_path(path, "retrieve", directory=False)
        return path

    def read_chunks(
        self,
        cwd: str,
        client_path: str,
        chunk_size: int = 1024,
    ) -> Iterator[bytes]:
        path = self.prepare_retrieve(cwd, client_path)
        return read_file_chunks(path, chunk_size)

    def store(
        self,
        cwd: str,
        client_path: str,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None = None,
    ) -> UploadResult:
        path = self.resolve(cwd, client_path)
        return self._atomic_upload(path, chunks, cancel_event, append=False)

    def append(
        self,
        cwd: str,
        client_path: str,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None = None,
    ) -> UploadResult:
        path = self.resolve(cwd, client_path)
        return self._atomic_upload(path, chunks, cancel_event, append=True)

    def store_unique(
        self,
        cwd: str,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None = None,
        prefix: str = "upload_",
    ) -> UploadResult:
        directory = self.resolve(cwd)
        if not os.path.isdir(directory):
            self._raise_for_path(directory, "stou", directory=True)

        with self._locks.acquire(directory):
            while True:
                filename = f"{prefix}{uuid.uuid4().hex}.bin"
                path = os.path.join(directory, filename)
                if not os.path.lexists(path):
                    break
            return self._atomic_upload(path, chunks, cancel_event, append=False)

    def _atomic_upload(
        self,
        path: str,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None,
        append: bool,
    ) -> UploadResult:
        operation = "append" if append else "store"
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            self._raise_for_path(parent, operation, directory=True)

        with self._locks.acquire(path):
            if os.path.isdir(path):
                raise FilesystemOperationError(operation, 550, "Target is a directory.")

            descriptor = -1
            temporary_path = ""
            try:
                descriptor, temporary_path = tempfile.mkstemp(
                    prefix=f".{os.path.basename(path)}.", suffix=".part", dir=parent
                )
                with os.fdopen(descriptor, "wb") as output:
                    descriptor = -1
                    if append and os.path.isfile(path):
                        with open(path, "rb") as current:
                            shutil.copyfileobj(current, output)

                    written = 0
                    for chunk in chunks:
                        self._check_cancel(cancel_event, operation)
                        if not isinstance(chunk, (bytes, bytearray, memoryview)):
                            raise TypeError("Upload chunks must be bytes-like objects.")
                        written += output.write(chunk)
                    self._check_cancel(cancel_event, operation)
                    output.flush()
                    os.fsync(output.fileno())

                os.replace(temporary_path, path)
                temporary_path = ""
                return UploadResult(path=os.path.realpath(path), bytes_written=written)
            except FilesystemOperationError:
                raise
            except (OSError, TypeError, ValueError) as error:
                raise self._translate(operation, error) from error
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                if temporary_path:
                    try:
                        os.remove(temporary_path)
                    except FileNotFoundError:
                        pass

    @staticmethod
    def _check_cancel(
        cancel_event: threading.Event | None, operation: str
    ) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise TransferCancelledError(operation)

    @staticmethod
    def _raise_for_path(path: str, operation: str, directory: bool) -> None:
        if not os.path.exists(path):
            raise FilesystemOperationError(operation, 550, "Path not found.")
        kind = "directory" if directory else "file"
        raise FilesystemOperationError(operation, 550, f"Path is not a {kind}.")

    @classmethod
    def _call(cls, operation: str, function, *args):
        try:
            return function(*args)
        except FilesystemOperationError:
            raise
        except (OSError, TypeError, ValueError) as error:
            raise cls._translate(operation, error) from error

    @staticmethod
    def _translate(operation: str, error: Exception) -> FilesystemOperationError:
        if isinstance(error, ValueError):
            code = 501
        elif isinstance(
            error,
            (
                FileNotFoundError,
                FileExistsError,
                IsADirectoryError,
                NotADirectoryError,
                PermissionError,
            ),
        ):
            code = 550
        else:
            code = 451
        return FilesystemOperationError(operation, code, str(error))
