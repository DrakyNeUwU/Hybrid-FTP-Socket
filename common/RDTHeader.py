import struct
import zlib


class RDTHeader:
    format = "!IIIHIH"
    size = struct.calcsize(format)  
    FLAG_DATA  = 0x01  
    FLAG_ACK   = 0x02  
    FLAG_FIN   = 0x04  
    FLAG_START = 0x08  
    FLAG_ABORT = 0x10 

    _VALID_FLAG_SETS = frozenset({
        FLAG_DATA,            
        FLAG_FIN,              
        FLAG_DATA | FLAG_FIN,  
        FLAG_ACK,             
        FLAG_START,            
        FLAG_ABORT,           
    })

    def __init__(
        self,
        transfer_id: int,
        seq_num: int,
        ack_num: int,
        flags: int,
        checksum: int = 0,
        length: int = 0,
    ):
        self.transfer_id = transfer_id
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.checksum = checksum
        self.length = length
    @classmethod
    def is_valid_flags(cls, flags: int) -> bool:
        return flags in cls._VALID_FLAG_SETS

    def serialize(self) -> bytes:
        if not self.is_valid_flags(self.flags):
            raise ValueError(f"Invalid RDT flags: {self.flags:#x}")
        if not 0 <= self.length <= 0xFFFF:
            raise ValueError("RDT payload length out of range")
        return struct.pack(
            self.format,
            self.transfer_id,
            self.seq_num,
            self.ack_num,
            self.flags,
            self.checksum,
            self.length,
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "RDTHeader":
        if len(data) < cls.size:
            raise ValueError(f"Dữ liệu quá ngắn: {len(data)} < {cls.size}")
        transfer_id, seq_num, ack_num, flags, checksum, length = struct.unpack(
            cls.format, data[: cls.size]
        )
        return cls(transfer_id, seq_num, ack_num, flags, checksum, length)

    def validate_length(self, packet_data: bytes) -> bool:
        available = len(packet_data) - self.size
        return 0 <= self.length == available

    def compute_checksum(self, payload: bytes = b"") -> int:
        header_fields = struct.pack(
            "!IIIHI",          
            self.transfer_id,
            self.seq_num,
            self.ack_num,
            self.flags,
            self.length,
        )
        return zlib.crc32(header_fields + payload) & 0xFFFFFFFF

    def verify_checksum(self, payload: bytes = b"") -> bool:
        return self.checksum == self.compute_checksum(payload)
