import socket
from common.rdt_header import RDTHeader
from common.file_utils import read_file_chunks

def send_file_rdt(filepath: str, dest_ip: str, dest_port: int):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(0.5)  
    
    chunks = list(read_file_chunks(filepath))
    
    for seq_num, chunk in enumerate(chunks):
        is_last = (seq_num == len(chunks) - 1)
        flags = RDTHeader.FLAG_FIN if is_last else RDTHeader.FLAG_DATA
        
        header = RDTHeader(seq_num=seq_num, ack_num=0, flags=flags, length=len(chunk))
        header.checksum = header.compute_checksum(chunk)
        
        packet = header.serialize() + chunk

        while True:
            try:
                udp_socket.sendto(packet, (dest_ip, dest_port))
                
                # Chờ ACK
                ack_data, _ = udp_socket.recvfrom(1024)
                ack_header = RDTHeader.deserialize(ack_data)
                
                if (ack_header.flags & RDTHeader.FLAG_ACK) and ack_header.ack_num == seq_num:
                    break
            except socket.timeout:
                print(f"[Timeout] Gửi lại gói {seq_num}...")

    udp_socket.close()