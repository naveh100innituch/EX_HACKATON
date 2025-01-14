import os
import socket
import struct
import threading
import time

import select


class Colors:
    # Text Colors
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    LIGHTGREY = '\033[37m'
    DARKGREY = '\033[90m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[97m'

    # Background Colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[107m'

    # Text Formatting
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'

    # Reset
    ENDC = '\033[0m'

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

UDP_PORT = 13117
BUFFER_SIZE = 4096

# Client Settings
TIMEOUT = 1  # Timeout for UDP listening in seconds

def get_available_udp_port():
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Bind to port 0 to let the OS assign a free port
        sock.bind(('', 0))
        # Get the assigned port number
        return sock.getsockname()[1]

def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        if os.name == 'nt':
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        udp_socket.bind(("", UDP_PORT))
        print(f"{Colors.OKGREEN}[Client] Listening for offers...{Colors.ENDC}")

        while True:
            try:
                data, server_address = udp_socket.recvfrom(BUFFER_SIZE)
                if len(data) >= 9:
                    magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                    if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                        print(f"{Colors.OKGREEN+Colors.BOLD}[Client] Offer received from {server_address[0]}: UDP port {udp_port}, TCP port {tcp_port}{Colors.ENDC}")
                        return server_address[0], udp_port, tcp_port
            except struct.error:
                print(f"{Colors.FAIL+Colors.BOLD}[Client] Invalid packet received{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.FAIL+Colors.BOLD}[Client] Error while listening for offers: {e}{Colors.ENDC}")

# Handle TCP Connection
def handle_tcp_connection(server_ip, tcp_port, file_size, tr_num,stats):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())

            start_time = time.time()
            received_data = 0

            while True:
                ready_socks, _, _ = select.select([tcp_socket], [], [], 1)
                if ready_socks:
                    data = tcp_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    received_data += len(data)
                else:
                    break  # No more data within timeout

            duration = time.time() - start_time
            speed = received_data*8 / duration if duration > 0 else 0  # Prevent division by zero
            print(f"{Colors.OKCYAN}[TCP] TCP transfer #{tr_num} completed: {received_data} bytes in {duration:.2f} seconds, speed: {speed:.2f} bytes/second")
            stats.append((tcp_socket, duration, speed))

    except Exception as e:
        print(f"{Colors.FAIL}[TCP] TCP connection error: {e}")

# Handle UDP Connection
def handle_udp_connection(server_ip, udp_port, file_size, tr_num,stats):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.settimeout(TIMEOUT)
            udp_socket.bind(('', 0))

            # Prepare the request message to send to the server
            request_message = struct.pack('!IbQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)
            udp_socket.sendto(request_message, (server_ip, udp_port))
            print(f"{Colors.BOLD}{Colors.YELLOW}[UDP] Sent UDP request to {server_ip}:{udp_port}{Colors.ENDC}")

            start_time = time.time()
            received_segments = set()
            total_segments = 0

            while True:
                ready_socks, _, _ = select.select([udp_socket], [], [], TIMEOUT)
                if ready_socks:
                    try:
                        data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                        if len(data) >= 21:
                            magic_cookie, msg_type, total_seg, current_seg = struct.unpack('!IbQQ', data[:21])
                            if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_MESSAGE_TYPE:
                                received_segments.add(current_seg)
                                total_segments = total_seg
                                if current_seg + 1 == total_seg:
                                    break

                    except socket.timeout:
                        print(f"{Colors.YELLOW}[UDP] Received UDP timeout")
                        break
                else:
                    break

            duration = time.time() - start_time
            speed = file_size / duration if duration > 0 else 0  # Prevent division by zero
            success_rate = (len(received_segments) / total_segments) * 100 if total_segments else 0
            print(f"{Colors.YELLOW}[UDP] UDP transfer #{tr_num} completed: {len(received_segments)}/{total_segments} segments in {duration:.2f} seconds, speed: {speed:.2f} bytes/second, success rate: {success_rate:.2f}%")
            stats.append((tr_num, duration, speed, success_rate))

    except Exception as e:
        print(f"{Colors.FAIL}[UDP] UDP connection error: {e}")

# Main Function
def start_client():
    print(f"{Colors.OKGREEN}[Client] Client started, listening for offer requests...")
    try:
        while True:
            server_ip, udp_port, tcp_port = listen_for_offers()
            file_size = int(input(f"{Colors.OKGREEN}[Client] Enter file size (bytes): "))
            num_tcp = int(input(f"{Colors.OKGREEN}[Client] Enter number of TCP connections: "))
            num_udp = int(input(f"{Colors.OKGREEN}[Client] Enter number of UDP connections: "))

            tcp_stats, udp_stats, tcp_threads, udp_threads = [], [], [], []

            tcp_threads = [
                threading.Thread(target=handle_tcp_connection, args=(server_ip, tcp_port, file_size, _+1,tcp_stats))
                for _ in range(num_tcp)
            ]

            udp_threads = [
                threading.Thread(target=handle_udp_connection, args=(server_ip, udp_port, file_size, _+1,udp_stats))
                for _ in range(num_udp)
            ]

            for thread in tcp_threads + udp_threads:
                thread.start()
            for thread in tcp_threads + udp_threads:
                thread.join()

            # for conn_id, duration, speed in tcp_stats:
            #     print(
            #         f"{Colors.OKCYAN}[TCP] TCP transfer #{conn_id} finished, total time: {duration:.2f} seconds, speed: {speed:.2f} bps{Colors.ENDC}")
            #
            # for conn_id, duration, speed, success_rate in udp_stats:
            #     status_color = Colors.OKGREEN if success_rate >= 95 else Colors.WARNING if success_rate >= 85 else Colors.FAIL
            #     print(f"{Colors.YELLOW}[UDP] UDP transfer #{conn_id} finished, total time: {duration:.2f} seconds, speed: {speed:.2f} bps, success rate: {success_rate:.2f}%{Colors.ENDC}")

            print(f"{Colors.BOLD}{Colors.HEADER}[Client] All transfers complete yipeee!! {Colors.ENDC}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.BOLD}{Colors.FAIL}[Client] Client interrupted. Shutting down gracefully...{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.BOLD}{Colors.FAIL}[Client] Unexpected error: {e}{Colors.ENDC}")


if __name__ == "__main__":
    start_client()
