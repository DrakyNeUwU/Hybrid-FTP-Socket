import socket
from common.rdt_header import RDTHeader
from common.file_utils import write_file_from_chunks

def receive_file_rdt(udp_socket: socket.socket, save_path: str):
    expected_seq = 0
    chunks = []
    
    while True:
        try:
            data, addr = udp_socket.recvfrom(2048)
            
            header = RDTHeader.deserialize(data)
            
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

                if header.flags & RDTHeader.FLAG_FIN:
                    break 

        except socket.timeout:
            continue
    write_file_from_chunks(save_path, chunks)
    return True