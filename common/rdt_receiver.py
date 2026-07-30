import socket
from common.rdt_header import RDTHeader
from common.file_utils import write_file_from_chunks

def receive_file_rdt(udp_socket: socket.socket, save_path: str):
    expected_seq = 0
    chunks = []
    while True:
        try:
            data, addr = udp_socket.recvfrom(2048)
            header, payload = RDTHeader.unpack(data)
            if not header.is_valid_checksum(payload):
                continue
            ack_pkt = RDTHeader.pack_ack(ack_num=header.seq)
            udp_socket.sendto(ack_pkt, addr)
            
            if header.seq == expected_seq:
                chunks.append(payload)
                expected_seq += 1

                if header.is_last:
                    break 

        except socket.timeout:
            continue
    write_file_from_chunks(save_path, chunks)
    return True