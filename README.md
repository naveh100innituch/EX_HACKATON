# Network Speed Test Application

This project implements a client-server application to compare download speeds over UDP and TCP protocols. The application uses Python's networking capabilities to demonstrate performance differences between these protocols.

## Overview

- **Server**: Broadcasts availability via UDP, handles data transfer requests over TCP and UDP, and provides performance statistics.
- **Client**: Listens for server broadcasts, connects to the server using both protocols, and measures download speed, success rate, and latency.

## Features

### Server
- **Broadcasting**: Advertises server availability using UDP.
- **TCP Handling**: Manages multiple client connections concurrently for reliable data transfer.
- **UDP Handling**: Responds to client requests with segmented, best-effort data transfer.
- **Performance Logging**: Logs total connections, data transferred, and server activity.

### Client
- **Server Discovery**: Listens for UDP broadcasts from the server.
- **Data Download**: Requests data using both TCP and UDP.
- **Performance Metrics**: Calculates download speed, success rate, and duration for each transfer.
- **Concurrency**: Supports multi-threaded connections for both protocols.

## Usage

### Running the Server
1. Ensure Python 3.x is installed.
2. Execute:
   ```bash
   python Server.py
   
### Running the Client
1. Ensure Python 3.x is installed.
2. Execute:
   ```bash
   python Client.py
   
### Constants
1. UDP Port: 13117
2. TCP Port: 5000 
3. Buffer Size: 1024 bytes 
4. Broadcast Interval: 1 second 
5. Payload Size: 4 KB
6. OFFER_MSG_TYPE: 2 
7. REQUEST_MSG_TYPE: 3 
8. PAYLOAD_MSG_TYPE: 4

### Notes
1. Client and server must be on the same network. 
2. Modify port numbers in the constants section if necessary.