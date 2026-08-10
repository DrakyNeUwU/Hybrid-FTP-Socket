"""Tests for Role C's shared, thread-safe filesystem API."""

import os
import threading

import pytest

from common.filesystem_service import (
    FilesystemOperationError,
    FilesystemService,
    TransferCancelledError,
)


@pytest.fixture
def service(tmp_path):
    root = tmp_path / "ftp-root"
    root.mkdir()
    return FilesystemService(str(root))


class TestFilesystemContract:
    def test_session_paths_are_independent(self, service):
        first = service.make_directory(service.root_dir, "first")
        second = service.make_directory(service.root_dir, "second")

        assert service.change_directory(service.root_dir, "first") == first
        assert service.change_directory(service.root_dir, "second") == second
        assert service.display_path(first) == "/first"
        assert service.display_path(second) == "/second"

    def test_cdup_at_root_stays_in_root(self, service):
        assert service.parent_directory(service.root_dir) == service.root_dir

    def test_traversal_returns_structured_ftp_error(self, service):
        with pytest.raises(FilesystemOperationError) as caught:
            service.stat(service.root_dir, "../secret.txt")

        assert caught.value.reply_code == 550
        assert caught.value.operation == "resolve"

    def test_listing_hides_symlink_that_escapes_root(self, service, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        link = os.path.join(service.root_dir, "outside-link")
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks are unavailable on this platform")

        assert "outside-link" not in service.names(service.root_dir)
        assert service.list(service.root_dir) == []


class TestAtomicUploads:
    def test_store_replaces_file_only_after_success(self, service):
        target = os.path.join(service.root_dir, "report.bin")
        with open(target, "wb") as output:
            output.write(b"old")

        result = service.store(service.root_dir, "report.bin", [b"new", b" data"])

        assert result.bytes_written == 8
        assert result.filename == "report.bin"
        with open(target, "rb") as uploaded:
            assert uploaded.read() == b"new data"
        assert not any(name.endswith(".part") for name in os.listdir(service.root_dir))

    def test_cancel_preserves_old_file_and_removes_temporary_file(self, service):
        target = os.path.join(service.root_dir, "report.bin")
        with open(target, "wb") as output:
            output.write(b"keep me")
        cancelled = threading.Event()
        cancelled.set()

        with pytest.raises(TransferCancelledError) as caught:
            service.store(service.root_dir, "report.bin", [b"discard"], cancelled)

        assert caught.value.reply_code == 426
        with open(target, "rb") as uploaded:
            assert uploaded.read() == b"keep me"
        assert not any(name.endswith(".part") for name in os.listdir(service.root_dir))

    def test_concurrent_append_does_not_mix_chunks(self, service):
        target = os.path.join(service.root_dir, "shared.bin")
        with open(target, "wb") as output:
            output.write(b"base|")
        barrier = threading.Barrier(3)
        errors = []

        def append(marker):
            try:
                barrier.wait()
                service.append(
                    service.root_dir,
                    "shared.bin",
                    [marker + b"1|", marker + b"2|"],
                )
            except Exception as error:  # captured for assertion in main thread
                errors.append(error)

        workers = [
            threading.Thread(target=append, args=(b"A",)),
            threading.Thread(target=append, args=(b"B",)),
        ]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join(timeout=2)

        assert errors == []
        with open(target, "rb") as uploaded:
            result = uploaded.read()
        assert result in (b"base|A1|A2|B1|B2|", b"base|B1|B2|A1|A2|")

    def test_stou_generates_unique_names(self, service):
        results = [
            service.store_unique(service.root_dir, [str(index).encode("ascii")])
            for index in range(5)
        ]

        assert len({result.filename for result in results}) == 5
        assert all(os.path.isfile(result.path) for result in results)
