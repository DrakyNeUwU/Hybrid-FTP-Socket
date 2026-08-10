"""Transfer orchestration shared by Roles A, B, and C.

Role A owns command parsing and FTP replies.  Role B supplies an RDT sender or
receiver adapter.  This module owns the transfer lifecycle and delegates all
path/file work to :class:`common.filesystem_service.FilesystemService`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
import socket
import threading
from collections.abc import Iterable
from typing import Any, Callable

from common.filesystem_service import (
    FilesystemOperationError,
    FilesystemService,
    TransferCancelledError,
)
from common.mode_codec import decode_chunks, encode_chunks
from common.rdt_context import Endpoint, TransferContext
from common.RDTHeader import RDTHeader


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
        context = self._context_for(session, "STOR", data_socket, endpoint, event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            if chunks is None:
                chunks = self._receive(data_socket, endpoint, context)
            chunks = decode_chunks(chunks, self._mode_for(session))
            result = service.store(cwd, client_path, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except TransferCancelledError as error:
            return self._failure(error)
        except FilesystemOperationError as error:
            return self._failure(error)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def append(
        self,
        session: Any,
        filepath: str,
        *,
        chunks: Iterable[bytes] | None = None,
        data_socket: Any = None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Append received chunks through the filesystem service atomically."""

        event = self._event_for(session, cancel_event)
        context = self._context_for(session, "APPE", data_socket, endpoint, event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            if chunks is None:
                chunks = self._receive(data_socket, endpoint, context)
            chunks = decode_chunks(chunks, self._mode_for(session))
            result = service.append(cwd, client_path, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except (TransferCancelledError, FilesystemOperationError) as error:
            return self._failure(error)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            return TransferResult(False, 426, error=str(error))
        finally:
            self._finish(session, event)

    def upload_unique(
        self,
        session: Any,
        *,
        chunks: Iterable[bytes] | None = None,
        data_socket: Any = None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> TransferResult:
        """Store an upload under a server-generated unique filename."""

        event = self._event_for(session, cancel_event)
        context = self._context_for(session, "STOU", data_socket, endpoint, event)
        try:
            service = self._service_for(session)
            if chunks is None:
                chunks = self._receive(data_socket, endpoint, context)
            chunks = decode_chunks(chunks, self._mode_for(session))
            result = service.store_unique(session.current_dir, chunks, event)
            return TransferResult(True, 226, result.bytes_written, result.path)
        except (TransferCancelledError, FilesystemOperationError) as error:
            return self._failure(error)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
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
        context = self._context_for(session, "RETR", data_socket, endpoint, event)
        try:
            service, cwd, client_path = self._target(service_path=filepath, session=session)
            chunks = service.read_chunks(cwd, client_path)
            context = replace(context, total_bytes=service.size(cwd, client_path))
            if getattr(session, "data_mode", None) == "PASSIVE":
                peer = self._wait_for_passive_peer(data_socket, session, context)
                context = replace(
                    context,
                    endpoint=Endpoint(peer[0], peer[1], "PASSIVE"),
                )
            chunks = encode_chunks(chunks, self._mode_for(session))
            transferred = self._send(chunks, data_socket, context.endpoint, context)
            if transferred is False:
                return TransferResult(False, 426, error="RDT sender failed")
            count = transferred if isinstance(transferred, int) else 0
            return TransferResult(True, 226, count, service.prepare_retrieve(cwd, client_path))
        except TransferCancelledError as error:
            return self._failure(error)
        except FilesystemOperationError as error:
            return self._failure(error)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
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
            session.data_socket = None

    def _service_for(self, session: Any) -> FilesystemService:
        if self.filesystem is not None:
            return self.filesystem
        root = getattr(session, "ftp_root", None)
        if not root:
            raise ValueError("Transfer session has no FTP root")
        self.filesystem = FilesystemService(root)
        return self.filesystem

    @staticmethod
    def _mode_for(session: Any) -> str:
        mode = getattr(session, "transfer_mode", "S") or "S"
        return str(mode).strip().upper()

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

    def _receive(self, data_socket: Any, endpoint: Any, context: TransferContext):
        if self.receiver is None:
            raise ValueError("No RDT receiver configured")
        method = getattr(self.receiver, "receive", self.receiver)
        return self._invoke(method, data_socket, context.endpoint, context)

    def _send(self, chunks: Iterable[bytes], data_socket: Any, endpoint: Any, context: TransferContext):
        if self.sender is None:
            raise ValueError("No RDT sender configured")
        method = getattr(self.sender, "send", self.sender)
        return self._invoke(method, chunks, data_socket, context.endpoint, context)

    @staticmethod
    def _wait_for_passive_peer(data_socket: Any, session: Any,
                               context: TransferContext) -> tuple[str, int]:
        """Read the client's authenticated UDP readiness probe for PASV RETR."""
        if data_socket is None:
            raise ValueError("Passive transfer has no UDP socket")
        data_socket.settimeout(context.timeout_seconds)
        expected_ip = getattr(session, "peer_ip", None)
        for _ in range(context.max_timeouts):
            if context.cancel_event.is_set():
                raise TransferCancelledError()
            try:
                packet, address = data_socket.recvfrom(RDTHeader.size + 64)
            except socket.timeout:
                continue
            except OSError as error:
                raise ValueError("Passive UDP socket closed") from error
            if expected_ip and address[0] != expected_ip:
                continue
            try:
                header = RDTHeader.deserialize(packet)
            except ValueError:
                continue
            if (
                header.flags == RDTHeader.FLAG_START
                and header.seq_num == 0
                and header.validate_length(packet)
                and header.verify_checksum(packet[RDTHeader.size:])
            ):
                return address[0], address[1]
        raise ValueError("Passive client did not provide a UDP readiness probe")

    @staticmethod
    def _context_for(session: Any, operation: str, data_socket: Any,
                     endpoint: tuple[str, int] | Endpoint | None,
                     event: threading.Event) -> TransferContext:
        if isinstance(endpoint, Endpoint):
            resolved = endpoint
        elif endpoint is not None:
            mode = getattr(session, "data_mode", "PASSIVE") or "PASSIVE"
            resolved = Endpoint(endpoint[0], endpoint[1], mode)
        else:
            resolved = Endpoint("127.0.0.1", 0, "PASSIVE")
        return TransferContext(
            transfer_id=str(getattr(session, "transfer_id", "unknown")),
            operation=operation,
            session_id=str(getattr(session, "session_id", "unknown")),
            endpoint=resolved,
            cancel_event=event,
            transfer_mode=str(getattr(session, "transfer_mode", "S") or "S").strip().upper(),
        )

    @staticmethod
    def _invoke(method: Callable, *args):
        """Call adapters with the full contract."""
        return method(*args)

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
        data_socket = getattr(session, "data_socket", None)
        if data_socket is not None:
            try:
                data_socket.close()
            except OSError:
                pass
        session.data_socket = None
        session.data_host = None
        session.data_port = None
        session.data_mode = None
