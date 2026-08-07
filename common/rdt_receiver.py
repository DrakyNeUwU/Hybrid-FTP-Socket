import socket
from common.RDTHeader import RDTHeader
from common.file_handler import write_file_from_chunks

def receive_file_rdt(udp_socket: socket.socket, save_path: str,progress_cb=None, is_cancelled=lambda: False):
    udp_socket.settimeout(1.0)
    expected_seq = 0
    chunks = []
    
    while True:
        if is_cancelled():
            udp_socket.close()
            return False
        try:
            data, addr = udp_socket.recvfrom(2048)
            if len(data) < RDTHeader.size:
                continue
            header = RDTHeader.deserialize(data)
            if header.flags & RDTHeader.FLAG_ABORT:
                print("[Abort] Nhận tín hiệu hủy từ Sender!")
                return False
            payload = data[RDTHeader.size : RDTHeader.size + header.length]  
            if not header.verify_checksum(payload):
                print(f"[Checksum Error] Bỏ qua gói {header.seq_num}")
                continue
            ack_header = RDTHeader(
                seq_num=0,
                ack_num=header.seq_num,
                flags=RDTHeader.FLAG_ACK,
                length=0
            )
            ack_header.checksum = ack_header.compute_checksum(b"")
            udp_socket.sendto(ack_header.serialize(), addr)
            
            if header.seq_num == expected_seq:
                chunks.append(payload)
                expected_seq += 1
                if progress_cb:
                    progress_cb(len(payload))
                if header.flags & RDTHeader.FLAG_FIN:
                    break 
            elif header.seq_num < expected_seq:
                print(f"[Duplicate] Nhận lại gói cũ {header.seq_num}, gửi lại ACK.")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Error] Receiver gặp lỗi: {e}")
            return False
    write_file_from_chunks(save_path, chunks)
    return True