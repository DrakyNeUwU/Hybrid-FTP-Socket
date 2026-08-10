"""Compatibility exports for the canonical Role B RDT adapters.

The implementation lives in ``common`` so the server and standalone tests use
the same wire protocol and constructor contract.
"""

from common.rdt_receiver import RDTReceiverAdapter
from common.rdt_sender import RDTSenderAdapter

__all__ = ["RDTSenderAdapter", "RDTReceiverAdapter"]
