from client.ftp_cli import _upload_arguments, run_command


class FakeClient:
    def __init__(self):
        self.calls = []

    def command(self, value):
        self.calls.append(("command", value))
        return "200 OK\r\n"

    def upload_file(self, local, remote, cmd, mode):
        self.calls.append(("upload", local, remote, cmd, mode))
        return True

    def download_file(self, remote, mode):
        self.calls.append(("download", remote, mode))
        return True


def test_upload_arguments_default_remote_name(tmp_path):
    source = tmp_path / "demo file.bin"
    source.write_bytes(b"data")
    assert _upload_arguments(["STOR", str(source)]) == (str(source), "demo file.bin")


def test_terminal_transfer_commands_use_production_client(tmp_path):
    source = tmp_path / "demo.bin"
    source.write_bytes(b"data")
    client = FakeClient()

    assert run_command(client, f'STOR "{source}" remote.bin', "PASV") == ("226 Transfer complete", False)
    assert run_command(client, "RETR remote.bin", "PASV") == ("226 Transfer complete", False)
    assert run_command(client, "PWD", "PASV") == ("200 OK", False)

    assert client.calls == [
        ("upload", str(source), "remote.bin", "STOR", "PASV"),
        ("download", "remote.bin", "PASV"),
        ("command", "PWD"),
    ]
