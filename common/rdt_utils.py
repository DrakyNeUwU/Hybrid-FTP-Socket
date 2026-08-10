import socket

def parse_pasv_response(response_str):
    """
    Parse an IP address and port from a PASV reply such as
    '227 Entering Passive Mode (127,0,0,1,35,42)'.
    """
    start = response_str.find('(')
    end = response_str.find(')')
    if start == -1 or end == -1:
        raise ValueError("Invalid PASV response format")
    
    parts = list(map(int, response_str[start+1:end].split(',')))
    ip = ".".join(map(str, parts[:4]))
    port = parts[4] * 256 + parts[5]
    return ip, port

def format_port_command(ip, port):
    """
    Create the PORT-command argument from an IP address and port.
    """
    h_parts = ip.split('.')
    p1, p2 = port // 256, port % 256
    return f"PORT {','.join(h_parts)},{p1},{p2}\r\n"
