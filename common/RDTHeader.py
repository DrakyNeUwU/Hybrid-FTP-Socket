import struct
import zlib
class RDTHeader: 
    format = "!IIHIH"
    size = struct.calcsize(format) 

    FLAG_DATA = 0x0 
    FLAG_ACK  = 0x1 # phản hồi ACK
    FLAG_FIN  = 0x2 # kết thúc file (is_last)
    FLAG_START= 0x4
    FLAG_ABORT= 0x8 # hủy truyển file
    def __init__ (value, seq_num: int, ack_num: int, flags: int, checksum: int = 0, length: int = 0):
        value.seq_num = seq_num
        value.ack_num = ack_num
        value.flags = flags
        value.checksum = checksum
        value.length = length
    def serialize (value) -> bytes:
        return struct.pack(
            value.format, 
            value.seq_num,
            value.ack_num,
            value.flags,
            value.checksum,
            value.length
        )
    @classmethod
    def deserialize(value, data:bytes):
        if len(data) < value.size:
            raise ValueError ("kich thuoc du lieu ngan")
        seq_num, ack_num, flags, checksum, length = struct.unpack(value.format, data[:value.size])
        return value (seq_num, ack_num, flags, checksum, length)
    def compute_checksum(self, payload: bytes = b"") -> int:
        return zlib.crc32(payload)
    def verify_checksum(self, payload: bytes = b"") -> bool:
        return self.checksum == self.compute_checksum(payload)