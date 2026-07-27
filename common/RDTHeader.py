import struct

class RDT: 
    format = "!IIHHH"
    size = struct.calcsize(format) 
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


