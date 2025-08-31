#!/usr/bin/env python3
"""
Debug socket communication
"""

import socket
import threading
import time

def server():
    """Simple server that just accepts connections and prints data"""
    print("🚀 Starting debug server...")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 5001))
    server_socket.listen(5)
    
    print("✅ Server listening on port 5001")
    
    try:
        while True:
            print("⏳ Waiting for connection...")
            client_socket, address = server_socket.accept()
            print(f"✅ Connection accepted from {address}")
            
            # Read data
            print("📥 Reading data...")
            data = client_socket.recv(1024)
            print(f"📥 Received: {data}")
            
            if data:
                print(f"📥 Decoded: {data.decode()}")
                
                # Send response
                response = "Hello from server!\n"
                print(f"📤 Sending: {response}")
                client_socket.send(response.encode())
            
            client_socket.close()
            print("🔌 Connection closed")
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    finally:
        server_socket.close()

def client():
    """Simple client that connects and sends data"""
    print("🔌 Starting debug client...")
    
    time.sleep(2)  # Wait for server to start
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 5001))
        print("✅ Connected to server")
        
        # Send data
        message = "Hello from client!\n"
        print(f"📤 Sending: {message}")
        sock.send(message.encode())
        
        # Wait for response
        print("⏳ Waiting for response...")
        response = sock.recv(1024)
        print(f"📥 Response: {response.decode()}")
        
        sock.close()
        print("🔌 Client closed")
        
    except Exception as e:
        print(f"❌ Client error: {e}")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=server, daemon=True)
    server_thread.start()
    
    # Start client
    client()
    
    # Wait a bit for server to finish
    time.sleep(1)
