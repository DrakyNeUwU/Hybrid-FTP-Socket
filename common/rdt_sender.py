import socket
from common.RDTHeader import RDTHeader
from common.file_handler import read_file_chunks
import os

def send_file_rdt(filepath: str, dest_ip: str, dest_port: int, progress_cb=None, is_cancelled=lambda: False, max_retries: int = 10):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(0.5)  

    total_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    transferred_bytes = 0

    chunks = list(read_file_chunks(filepath))
    if not chunks:
        chunks = [b""]
    for seq_num, chunk in enumerate(chunks):
        if is_cancelled():
            abort_header = RDTHeader(seq_num=seq_num, ack_num=0, flags=RDTHeader.FLAG_ABORT, length=0)
            udp_socket.sendto(abort_header.serialize(), (dest_ip, dest_port))
            udp_socket.close()
            return False

        is_last = (seq_num == len(chunks) - 1)
        flags = RDTHeader.FLAG_FIN if is_last else RDTHeader.FLAG_DATA
        
        header = RDTHeader(seq_num=seq_num, ack_num=0, flags=flags, length=len(chunk))
        header.checksum = header.compute_checksum(chunk)
        packet = header.serialize() + chunk
        retries = 0
        ack_received = False
        while retries < max_retries:
            if is_cancelled():
                udp_socket.close()
                return False
            try:
                udp_socket.sendto(packet, (dest_ip, dest_port))
                # Chờ ACK
                ack_data, _ = udp_socket.recvfrom(1024)
                ack_header = RDTHeader.deserialize(ack_data)
                
                if (ack_header.flags & RDTHeader.FLAG_ACK) and ack_header.ack_num == seq_num:
                    ack_received = True
                    transferred_bytes += len(chunk)
                    if progress_cb:
                        progress_cb(transferred_bytes, total_size)
                    break
            except socket.timeout:
                retries += 1 
                print(f"[Timeout] Gửi lại gói {seq_num}(Lần {retries}/{max_retries})...")
        if not ack_received:
            print(f"[Error] Quá số lần thử lại cho gói {seq_num}. Hủy truyền file.")
            udp_socket.close()
            return False
    udp_socket.close()
    return True