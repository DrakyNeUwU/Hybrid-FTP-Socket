# 12. Limitations and Future Work

The project implements all three FTP transfer modes: `MODE S` (stream
passthrough), `MODE B` (RFC 959 block framing) and `MODE C` (FTP RLE
compression) with streaming codecs and SHA-256-preserving E2E verification.
Remaining limitations: compressed mode applies only the fixed FTP RLE scheme
(no adaptive per-file strategy), RDT uses a fixed bounded Go-Back-N window
rather than adaptive congestion control, and client-side mode defaults to `S`
unless the user selects B/C. Future work could add TLS, configurable
authentication, richer interoperability testing with standard FTP servers, and
broader network-performance measurements.
