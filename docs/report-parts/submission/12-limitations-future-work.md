# 12. Limitations and Future Work

Only stream mode is implemented; `MODE B` and `MODE C` return `502`. The RDT
implementation is designed for the project scope and uses a fixed bounded
Go-Back-N window rather than adaptive congestion control. Future work could add
TLS, configurable authentication, richer interoperability testing, and broader
network-performance measurements.
