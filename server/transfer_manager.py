"""Transfer orchestration shared by Roles A, B, and C.

Role A owns command parsing and FTP replies.  Role B supplies an RDT sender or
receiver adapter.  This module owns the transfer lifecycle and delegates all
path/file work to :class:`common.filesystem_service.FilesystemService`.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import threading
from collections.abc import Iterable
from typing import Any, Callable

from common.filesystem_service import (
    FilesystemOperationError,
    FilesystemService,
    TransferCancelledError,
)


@dataclass(frozen=True)
class TransferResult:
    """Structured result that remains compatible with ``if result`` callers."""

    success: bool
    reply_code: int
    bytes_transferred: int = 0
    path: str | None = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


class TransferManager:
    """Coordinate filesystem lifecycle with an injectable RDT adapter.

    The adapter boundary deliberately stays small:

    * receiver: ``receive(data_socket, cancel_event) -> Iterable[bytes]``
    * sender: ``send(chunks, data_socket, endpoint, cancel_event) -> int | bool``

    A callable or an object exposing ``receive``/``send`` is accepted.  This
    lets Role B plug in its production implementation without changing the
    filesystem or command layers.
    """

    def __init__(
        self,
        filesystem: FilesystemService | None = None,
        *,
        sender: Any = None,
        receiver: Any = None,
    ) -> None:
        self.filesystem = filesystem
        self.sender = sender
        self.receiver = receiver

    def upload(
        self,
        session: Any,
        filepath: str,
        *,
        chunks: Iterable[bytes] | None = None,
        data_socket: Any = None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Receive bytes, atomically commit them, and return a structured result."""

        event = self._event_for(session, cancel_event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            if chunks is None:
                chunks = self._receive(data_socket, endpoint, event)
            result = service.store(cwd, client_path, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except TransferCancelledError as error:
            return self._failure(error)
        except FilesystemOperationError as error:
            return self._failure(error)
        except (OSError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def append(
        self,
        session: Any,
        filepath: str,
        *,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Append received chunks through the filesystem service atomically."""

        event = self._event_for(session, cancel_event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            result = service.append(cwd, client_path, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except (TransferCancelledError, FilesystemOperationError) as error:
            return self._failure(error)
        except (OSError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def upload_unique(
        self,
        session: Any,
        *,
        chunks: Iterable[bytes],
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Store an upload under a server-generated unique filename."""

        event = self._event_for(session, cancel_event)
        try:
            service = self._service_for(session)
            result = service.store_unique(session.current_dir, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except (TransferCancelledError, FilesystemOperationError) as error:
            return self._failure(error)
        except (OSError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def download(
        self,
        session: Any,
        filepath: str,
        *,
        data_socket: Any = None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Read a validated file and send it through the RDT adapter."""

        event = self._event_for(session, cancel_event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            chunks = service.read_chunks(cwd, client_path)
            transferred = self._send(chunks, data_socket, endpoint, event)
            if transferred is False:
                return TransferResult(False, 426, error="RDT sender failed")
            count = transferred if isinstance(transferred, int) else 0
            return TransferResult(True, 226, count, service.prepare_retrieve(cwd, client_path))
        except TransferCancelledError as error:
            return self._failure(error)
        except FilesystemOperationError as error:
            return self._failure(error)
        except (OSError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def cancel(self, session: Any) -> None:
        """Signal cancellation and close the session-owned data socket."""

        event = getattr(session, "transfer_cancel_event", None)
        if event is None:
            event = threading.Event()
            session.transfer_cancel_event = event
        event.set()
        session.transfer_cancelled = True

        transfer = getattr(session, "current_transfer", None)
        cancel = getattr(transfer, "cancel", None)
        if callable(cancel):
            cancel()

        data_socket = getattr(session, "data_socket", None)
        if data_socket is not None:
            try:
                data_socket.close()
            except OSError:
                pass

    def _service_for(self, session: Any) -> FilesystemService:
        if self.filesystem is not None:
            return self.filesystem
        root = getattr(session, "ftp_root", None)
        if not root:
            raise ValueError("Transfer session has no FTP root")
        self.filesystem = FilesystemService(root)
        return self.filesystem

    def _target(self, service_path: str, session: Any):
        service = self._service_for(session)
        cwd = os.path.realpath(getattr(session, "current_dir", service.root_dir))
        # Existing Role A passes an absolute path.  Convert it back to a
        # client-relative path so FilesystemService remains the sole validator.
        if os.path.isabs(service_path):
            client_path = os.path.relpath(service_path, cwd)
        else:
            client_path = service_path
        return service, cwd, client_path

    def _receive(self, data_socket: Any, endpoint: Any, event: threading.Event):
        if self.receiver is None:
            raise ValueError("No RDT receiver configured")
        method = getattr(self.receiver, "receive", self.receiver)
        return self._invoke(method, data_socket, endpoint, event)

    def _send(self, chunks: Iterable[bytes], data_socket: Any, endpoint: Any, event: threading.Event):
        if self.sender is None:
            raise ValueError("No RDT sender configured")
        method = getattr(self.sender, "send", self.sender)
        return self._invoke(method, chunks, data_socket, endpoint, event)

    @staticmethod
    def _invoke(method: Callable, *args):
        """Call adapters with the full contract, allowing simple test doubles."""
        try:
            return method(*args)
        except TypeError:
            # Transitional compatibility for adapters that omit endpoint.
            return method(*[arg for arg in args if arg is not None])

    @staticmethod
    def _event_for(session: Any, event: threading.Event | None) -> threading.Event:
        if event is None:
            event = threading.Event()
        session.transfer_cancel_event = event
        session.transfer_cancelled = False
        return event

    @staticmethod
    def _failure(error: FilesystemOperationError) -> TransferResult:
        return TransferResult(False, error.reply_code, error=str(error))

    @staticmethod
    def _finish(session: Any, event: threading.Event) -> None:
        if getattr(session, "transfer_cancel_event", None) is event:
            session.transfer_cancel_event = None
        session.current_transfer = None
