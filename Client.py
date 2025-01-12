import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

UDP_BROADCAST_PORT = 13117
BUFFER_SIZE = 1024

# Client Settings
TIMEOUT = 1  # Timeout for UDP listening in seconds

def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        udp_socket.bind(("", UDP_BROADCAST_PORT))
        print("[Client] Listening for offers...")

        while True:
            try:
                data, server_address = udp_socket.recvfrom(BUFFER_SIZE)
                if len(data) >= 9:
                    magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('>IBHH', data[:9])
                    if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MESSAGE_TYPE:
                        print(f"[Client] Offer received from {server_address[0]}: UDP port {udp_port}, TCP port {tcp_port}")
                        return server_address[0], udp_port, tcp_port
            except socket.timeout:
                print("[Client] No offers received. Retrying...")

# Handle TCP Connection
def handle_tcp_connection(server_ip, tcp_port, file_size):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())

            start_time = time.time()
            received_data = tcp_socket.recv(BUFFER_SIZE)
            total_received = len(received_data)

            while received_data:
                received_data = tcp_socket.recv(BUFFER_SIZE)
                total_received += len(received_data)

            duration = time.time() - start_time
            speed = total_received / duration
            print(f"[Client] TCP transfer completed: {total_received} bytes in {duration:.2f} seconds, speed: {speed:.2f} bytes/second")
    except Exception as e:
        print(f"[Client] TCP connection error: {e}")

# Handle UDP Connection
def handle_udp_connection(server_ip, udp_port, file_size):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.settimeout(TIMEOUT)

            request_message = struct.pack('>IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)
            udp_socket.sendto(request_message, (server_ip, udp_port))

            start_time = time.time()
            received_segments = 0
            total_segments = None

            while True:
                try:
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) >= 21:
                        magic_cookie, msg_type, total_seg, current_seg = struct.unpack('>IBQQ', data[:21])

                        if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_MESSAGE_TYPE:
                            received_segments += 1
                            if total_segments is None:
                                total_segments = total_seg

                except socket.timeout:
                    break

            duration = time.time() - start_time
            success_rate = (received_segments / total_segments) * 100 if total_segments else 0
            speed = (received_segments * BUFFER_SIZE) / duration

            print(f"[Client] UDP transfer completed: {received_segments}/{total_segments} segments in {duration:.2f} seconds, speed: {speed:.2f} bytes/second, success rate: {success_rate:.2f}%")

    except Exception as e:
        print(f"[Client] UDP connection error: {e}")

# Main Function
def main():
    print("[Client] Starting client...")

    while True:
        server_ip, udp_port, tcp_port = listen_for_offers()

        file_size = int(input("Enter file size (bytes): "))
        num_tcp = int(input("Enter number of TCP connections: "))
        num_udp = int(input("Enter number of UDP connections: "))

        tcp_threads = [
            threading.Thread(target=handle_tcp_connection, args=(server_ip, tcp_port, file_size))
            for _ in range(num_tcp)
        ]

        udp_threads = [
            threading.Thread(target=handle_udp_connection, args=(server_ip, udp_port, file_size))
            for _ in range(num_udp)
        ]

        for thread in tcp_threads + udp_threads:
            thread.start()

        for thread in tcp_threads + udp_threads:
            thread.join()

        print("[Client] All transfers completed. Listening for new offers...")

if __name__ == "__main__":
    main()
