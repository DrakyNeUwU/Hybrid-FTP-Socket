# 12. Limitations and Future Work

The current handoff baseline accepts `MODE S`; `MODE B/C` return `502` until
Role A implements and verifies their transfer semantics. Separate RFC block
framing and compression codecs are not currently implemented. The RDT
implementation uses a fixed bounded Go-Back-N window
rather than adaptive congestion control. Future work could add distinct MODE
codecs, TLS, configurable authentication, richer interoperability testing, and
broader network-performance measurements.
