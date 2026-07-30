from common.rdt_receiver import receive_file_rdt

def handle_download(filename, udp_socket):
    print(f"Đang tải file {filename}...")
    receive_file_rdt(udp_socket, save_path=f"./downloads/{filename}")
    print("Tải file thành công!")