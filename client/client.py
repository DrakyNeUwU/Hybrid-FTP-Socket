from common.rdt_receiver import receive_file_rdt

def handle_download(filename, udp_socket):
    print(f"Downloading {filename}...")
    receive_file_rdt(udp_socket, save_path=f"./downloads/{filename}")
    print("Download completed successfully!")
