import os
import socket
import struct
import threading
import time
import platform
import select

class Colors:
    # Text Colors
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    YELLOW = '\033[33m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


MAGIC_COOKIE = 0xabcddcba
OFFER_MSG_TYPE = 2
REQUEST_MSG_TYPE = 3
PAYLOAD_MSG_TYPE = 4
UDP_PORT = 13117
TCP_PORT = 5000
BUFFER_SIZE = 1024
BROADCAST_INTERVAL = 1.0
PAYLOAD_SIZE = 4096
TCP_BACKLOG = 5


hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
server_running = threading.Event()

# Statistics
total_tcp_connections = 0
total_data_transferred = 0

def create_udp_socket():
    """
        Create a UDP socket with cross-platform support.

        returns:
            UDP socket
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if platform.system() != "Windows":
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock

def broadcast_offers():
    """
        Sends periodic UDP broadcast messages to advertise the server's availability.
    """
    time.sleep(1)   # making sure TCP and UDP sockets are set before any broadcast
    try:
        with create_udp_socket() as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"{Colors.OKGREEN}[Broadcast] UDP broadcast started at {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
            offer_message = struct.pack(
                '!IbHH', MAGIC_COOKIE, OFFER_MSG_TYPE, UDP_PORT, TCP_PORT
            )
            while True:
                udp_socket.sendto(offer_message, ('<broadcast>', UDP_PORT))
                time.sleep(BROADCAST_INTERVAL)
    except Exception as e:
        print(f"{Colors.FAIL}[Broadcast] Error in UDP broadcast: {e}{Colors.ENDC}")


def handle_tcp_connection(client_socket, address):
    """
        Handles a client's TCP request for data transfer.

        Args:
            client_socket (socket.socket): The client's TCP socket connection.
            address (tuple): The address of the connected client (IP, port).
    """
    global total_tcp_connections, total_data_transferred
    try:
        file_size_data = client_socket.recv(BUFFER_SIZE)
        if not file_size_data: return
        file_size = int(file_size_data.decode().strip())
        print(f"{Colors.OKCYAN}[TCP] TCP request from {address}, file size: {file_size} bytes{Colors.ENDC}")

        chunk_size=1024*1024
        for i in range(0,file_size,chunk_size):
            data = b'1' * min(chunk_size, file_size - i)
            client_socket.sendall(data)

        print(f"{Colors.OKCYAN}[TCP] TCP transfer to {address} completed.{Colors.ENDC}")
        total_tcp_connections += 1
        total_data_transferred += file_size
    except Exception as e:
        print(f"{Colors.FAIL}[TCP] Error handling TCP connection: {e}{Colors.ENDC}")
    finally:
        client_socket.close()


def handle_udp_connection():
    """
        Handles a client's UDP request for data transfer.
    """
    try:
        with create_udp_socket() as udp_sock:
            udp_sock.bind(('', UDP_PORT))
            print(f"{Colors.YELLOW}[UDP] Listening on UDP port {UDP_PORT}{Colors.ENDC}")

            while server_running.is_set():
                readable, _, _ = select.select([udp_sock], [], [], 1)
                for sock in readable:
                    data, addr = sock.recvfrom(BUFFER_SIZE)
                    if len(data) < 5:
                        continue
                    # Unpack incoming UDP message: MAGIC_COOKIE + MESSAGE_TYPE + FILE_SIZE
                    magic_cookie, msg_type = struct.unpack('!Ib', data[:5])
                    if magic_cookie != MAGIC_COOKIE:
                        print(f"{Colors.FAIL}[UDP] Invalid magic cookie from {addr}{Colors.ENDC}")
                        continue
                    if msg_type != REQUEST_MSG_TYPE:
                        # print(f"{Colors.FAIL}[UDP] Invalid request type from {addr}{Colors.ENDC}")
                        continue

                    file_size = struct.unpack('!Q', data[5:13])[0]
                    total_segments = (file_size + PAYLOAD_SIZE - 1) // PAYLOAD_SIZE
                    print(f"{Colors.YELLOW}[UDP] Requesting {file_size} bytes from {addr}{Colors.ENDC}")
                    print(f"{Colors.YELLOW}[UDP] Total segments to send: {total_segments}{Colors.ENDC}")

                    for segment in range(total_segments):
                        header = struct.pack('!IbQQ', MAGIC_COOKIE, PAYLOAD_MSG_TYPE, total_segments,
                                             segment)
                        payload_data = os.urandom(PAYLOAD_SIZE - len(header))
                        sock.sendto(header + payload_data, addr)
                    print(f"{Colors.YELLOW}[UDP] UDP transfer to {addr} completed.{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}[UDP] {e}{Colors.ENDC}")


def start_tcp_server():
    '''
        Starting TCP server on TCP port.
    '''
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("", TCP_PORT))
            tcp_socket.listen()
            print(f"{Colors.OKCYAN}[TCP] TCP server started on port {TCP_PORT}{Colors.ENDC}")

            while server_running.is_set():
                readable, _, _ = select.select([tcp_socket], [], [], 1)
                for sock in readable:
                    client_socket, address = sock.accept()
                    threading.Thread(target=handle_tcp_connection, args=(client_socket, address), daemon=True).start()

    except Exception as e:
        print(f"{Colors.FAIL}[TCP] Error in TCP server: {e}{Colors.ENDC}")


def start_server():
    '''
        Activates Server's functions
    '''
    global total_tcp_connections, total_data_transferred
    try:
        server_running.set()
        print(f"{Colors.OKGREEN}[Server] Server started, listening on IP {ip_address} on {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
        threading.Thread(target=broadcast_offers, daemon=True).start()
        threading.Thread(target=handle_udp_connection, daemon=True).start()
        start_tcp_server()

    except KeyboardInterrupt:
        print(f"{Colors.WARNING}\nServer shutting down...{Colors.ENDC}")
        server_running.clear()
    finally:
        print(f"{Colors.OKGREEN}[Server] Server terminated.{Colors.ENDC}")
        print(f"{Colors.BOLD + Colors.HEADER}[Server] Total TCP connections: {total_tcp_connections}{Colors.ENDC}")
        print(f"{Colors.BOLD + Colors.HEADER}[Server] Total data transferred: {total_data_transferred} bytes{Colors.ENDC}")


if __name__ == "__main__":
    start_server()
