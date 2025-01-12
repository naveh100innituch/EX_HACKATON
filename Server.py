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

# Server Settings
TCP_PORT = 5000
UDP_PORT = 5001

def broadcast_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        while True:
            offer_message = struct.pack(
                '>IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, UDP_PORT, TCP_PORT
            )
            udp_socket.sendto(offer_message, ('<broadcast>', UDP_BROADCAST_PORT))
            print("[Server] Offer broadcast sent.")
            time.sleep(1)

# Handle TCP Requests
def handle_tcp_connection(client_socket, address):
    try:
        file_size = int(client_socket.recv(BUFFER_SIZE).decode().strip())
        print(f"[Server] TCP request from {address}, file size: {file_size} bytes")

        data = b'1' * file_size
        client_socket.sendall(data)
        print(f"[Server] TCP transfer to {address} completed.")

    except Exception as e:
        print(f"[Server] Error handling TCP connection: {e}")
    finally:
        client_socket.close()

# Handle UDP Requests
def handle_udp_connection(data, client_address, udp_socket):
    try:
        _, msg_type, file_size = struct.unpack('>IBQ', data[:13])

        if msg_type != REQUEST_MESSAGE_TYPE:
            print(f"[Server] Invalid UDP request type from {client_address}")
            return

        total_segments = file_size // BUFFER_SIZE + (1 if file_size % BUFFER_SIZE else 0)

        for segment in range(total_segments):
            payload = struct.pack(
                '>IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, segment
            ) + b'1' * BUFFER_SIZE

            udp_socket.sendto(payload, client_address)

        print(f"[Server] UDP transfer to {client_address} completed.")

    except Exception as e:
        print(f"[Server] Error handling UDP connection: {e}")

# Start TCP Server
def start_tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(("", TCP_PORT))
        tcp_socket.listen()
        print(f"[Server] TCP server started on port {TCP_PORT}")

        while True:
            client_socket, client_address = tcp_socket.accept()
            threading.Thread(target=handle_tcp_connection, args=(client_socket, client_address)).start()

# Start UDP Server
def start_udp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("", UDP_PORT))
        print(f"[Server] UDP server started on port {UDP_PORT}")

        while True:
            data, client_address = udp_socket.recvfrom(BUFFER_SIZE)
            threading.Thread(target=handle_udp_connection, args=(data, client_address, udp_socket)).start()

# Main Function
def main():
    print("[Server] Starting server...")

    # Start threads for broadcasting offers, TCP, and UDP servers
    threading.Thread(target=broadcast_offers, daemon=True).start()
    threading.Thread(target=start_tcp_server, daemon=True).start()
    threading.Thread(target=start_udp_server, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()