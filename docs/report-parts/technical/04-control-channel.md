# 4. Control Channel — TCP

**Status:** Complete
**Purpose:** Describe the TCP control-channel architecture, parser, session
management, 28-command matrix, MODE negotiation, and FTP-reply mapping.
**Requirement:** RQ-02, RQ-03, RQ-05, RQ-10. **Owner:** Role A. **Reviewer:** Role C.  
**Code:** `server/command_parser.py`, `server/command_handler.py`,
`server/session.py`, `server/client_handler.py`, and `server/ftp_reply.py`.

## 4.1 Architecture and pipeline

Each client has a dedicated TCP control connection. `ClientHandler` buffers
bytes and splits CRLF-delimited commands. `CommandParser` separates the
case-insensitive command name and argument, while `CommandHandler` validates
and dispatches it. Each client has an isolated `Session`; filesystem access and
UDP/RDT transfers cross the `FilesystemService` and `TransferManager`
boundaries.

The handler supports fragmented commands, multiple commands received together,
and invalid UTF-8 without crashing a client thread. A session owns login state,
the current FTP directory/root, transfer type and mode, negotiated UDP endpoint,
and cancellation state.

## 4.2 Command compliance

The required FTP commands are implemented: `USER`, `PASS`, `QUIT`, `NOOP`,
`PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `DELE`, `RNFR`, `RNTO`, `LIST`, `NLST`,
`SIZE`, `MDTM`, `STAT`, `HASH`, `TYPE`, `MODE`, `HELP`, `PORT`, `PASV`,
`RETR`, `STOR`, `STOU`, `APPE`, and `ABOR`.

`LIST` and `NLST` return textual metadata on the TCP control channel. They do
not create a UDP endpoint or RDT transfer lifecycle. UDP/RDT is reserved for
file payloads in `RETR`, `STOR`, `STOU`, and `APPE`.

## 4.3 MODE and transfer lifecycle

`MODE S` is supported and returns `200`. Block and compressed modes (`MODE B`
and `MODE C`) return `502 Mode not implemented`; this avoids claiming support
for codecs or block framing that the project does not implement. MODE is stored
per session, so one client cannot change another client’s transfer mode.

For a file transfer, the handler requires `PORT` or `PASV`, sends `150` on TCP,
and starts a bounded UDP/RDT worker. Success sends `226`; a failure or `ABOR`
sends an appropriate `4xx`/`5xx` reply. `ABOR` sets the shared cancellation
event, closes the UDP socket, and joins the worker with a finite timeout.

## 4.4 Verification evidence

The final Role A control/session audit ran:

```bash
python3 -m pytest tests/test_command_parser.py tests/test_commands.py \
  tests/test_session.py tests/test_threaded_server.py -q
```

It reported **63 passed in 5.71s**. The final WSL2 regression reported **199
passed in 96.72s**, including end-to-end transfer tests. See
`docs/evidence/final-week-rdt-gbn-verification.md`.
