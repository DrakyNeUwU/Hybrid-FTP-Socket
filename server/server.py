from server.data_channel import ServerDataChannel
def process_client_command(command, args, client_tcp_socket):
    if command == "STOR":
        filename = args[0]
        data_channel = ServerDataChannel()
        udp_port = data_channel.get_port()
        
        client_tcp_socket.send(f"227 Entering UDP Mode (Port {udp_port})\n".encode())
        
        data_channel.handle_receive_file(f"./storage/{filename}")
        client_tcp_socket.send(b"226 Transfer Complete.\n")