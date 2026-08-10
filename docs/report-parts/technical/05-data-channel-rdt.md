# 5. Data Channel — UDP/RDT

**Status:** Complete
**Purpose:** Describe the UDP/RDT header, serialization, ACK/retry behavior,
FIN/ABORT lifecycle, and test evidence.
**Requirement:** RQ-04, RQ-06, RQ-10, RQ-12. **Owner:** B. **Reviewer:** A/C.  
**Code:** `common/RDTHeader.py`, `common/rdt_sender.py`, and
`common/rdt_receiver.py`.

## Architecture and wire format

The data path uses UDP with a project-specific reliable data-transfer layer,
separate from TCP control. `RDTSenderAdapter` connects the transfer manager or
client to the sender; `RDTReceiverAdapter` validates and reassembles received
chunks for file writing.

The 20-byte, big-endian RDT header contains `transfer_id`, `seq_num`,
`ack_num`, `flags`, `checksum`, and payload `length`. Flags identify DATA, ACK,
FIN, START, and ABORT packets. CRC-32 covers the agreed header fields and
payload, allowing both peers to reject corrupted data.

## Reliable transfer flow

The sender first transmits a START packet with transfer metadata and waits for
ACK sequence 0. It then sends DATA in a bounded Go-Back-N window of up to four
packets. The receiver validates peer, transfer ID, length, and checksum; it
delivers only the next expected packet and returns a cumulative ACK for the
highest contiguous sequence. A timeout retransmits the current window until a
finite retry limit is reached.

After the last DATA packet, the sender transmits FIN. The receiver acknowledges
it and remains briefly available to re-acknowledge a duplicate FIN. ABORT stops
the transfer immediately and safely. This preserves the shared header and TCP
control contract while extending the earlier Stop-and-Wait design.

## Verification evidence

```bash
pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q
```

The recorded result is **45 passed in 67.09s**. Coverage includes header
serialization, valid and corrupt checksums, packet and ACK loss, corruption,
empty and chunk-boundary files, cancellation/ABORT, and retry timeouts.

The verified success sequence is `START → ACK(0) → DATA/ACK → FIN/ACK`; ABORT
is the terminal cancellation or fatal-error path.
