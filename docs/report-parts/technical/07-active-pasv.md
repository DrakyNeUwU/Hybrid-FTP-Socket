# 7. Active and Passive Modes

`PORT` configures an Active UDP endpoint after strict six-octet validation and
peer/IP checks. `PASV` allocates a UDP endpoint and replies with `227`.
Replacing an endpoint closes the previous socket; QUIT, disconnect, and ABOR
also clean it up.

For Active downloads, the client sends a zero-payload START probe after `150`.
This establishes the UDP/NAT path before the server begins the real transfer.
It does not change the TCP or RDT header contract. Localhost and two-machine
LAN Active/PASV transfers were verified with matching source/server/client
SHA-256 values.
