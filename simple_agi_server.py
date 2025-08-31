#!/usr/bin/env python3
"""
Minimal working AGI server for testing
"""

import socket
import threading
import time

class SimpleAGIServer:
    def __init__(self, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the AGI server"""
        try:
            print(f"Starting AGI server on {self.host}:{self.port}")
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"AGI server started successfully")
            
            # Start server in main thread for simplicity
            self._accept_connections()
            
        except Exception as e:
            print(f"Failed to start AGI server: {e}")
            return False
        
        return True
    
    def _accept_connections(self):
        """Accept incoming AGI connections"""
        print("Waiting for AGI connections...")
        
        while self.running:
            try:
                print("Calling accept()...")
                client_socket, address = self.server_socket.accept()
                print(f"AGI connection accepted from {address}")
                
                # Handle connection in main thread for simplicity
                self._handle_agi_connection(client_socket, address)
                
            except Exception as e:
                if self.running:
                    print(f"Error accepting AGI connection: {e}")
                else:
                    break
    
    def _handle_agi_connection(self, client_socket, address):
        """Handle individual AGI connection"""
        try:
            print(f"Handling AGI connection from {address}")
            
            # Read AGI environment variables
            agi_vars = {}
            print("Reading AGI environment variables...")
            
            # Read data line by line
            buffer = ""
            while True:
                char = client_socket.recv(1).decode('utf-8')
                if not char:
                    break
                
                buffer += char
                
                if char == '\n':
                    line = buffer.strip()
                    buffer = ""
                    
                    print(f"Received line: '{line}'")
                    
                    if not line:  # Empty line marks end of environment variables
                        print("Empty line found, end of environment variables")
                        break
                    
                    if ':' in line:
                        key, value = line.split(':', 1)
                        agi_vars[key.strip()] = value.strip()
                        print(f"Parsed AGI variable: {key.strip()} = {value.strip()}")
            
            print(f"AGI variables: {agi_vars}")
            
            # Process the AGI request
            print("Processing AGI request...")
            
            # Extract call information
            caller_id = agi_vars.get('agi_callerid', 'Unknown')
            extension = agi_vars.get('agi_extension', '1412')
            unique_id = agi_vars.get('agi_uniqueid', 'test_123')
            channel = agi_vars.get('agi_channel', '')
            
            print(f"AGI call received - Caller: {caller_id}, Extension: {extension}, Channel: {channel}")
            
            # Return success response to Asterisk
            response = "200 result=0\n"
            print(f"Sending response: {response}")
            client_socket.send(response.encode())
            
            print("AGI request processed successfully")
            
        except Exception as e:
            print(f"Error handling AGI connection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("Closing AGI connection")
            client_socket.close()
    
    def stop(self):
        """Stop the AGI server"""
        print("Stopping AGI server...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("AGI server stopped")

def test_simple_agi():
    """Test the simple AGI server"""
    print("🚀 Testing Simple AGI Server")
    print("=" * 40)
    
    server = SimpleAGIServer()
    
    try:
        # Start server in a separate thread
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Test connection
        print("\n🔌 Testing AGI server connection...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 5001))
        print("✅ Connected to AGI server")
        
        # Send test AGI request
        print("📤 Sending test AGI request...")
        agi_request = "agi_callerid: 1234567890\nagi_extension: 1412\nagi_uniqueid: test_123\n\n"
        sock.send(agi_request.encode())
        print("✅ Request sent")
        
        # Wait for response
        print("⏳ Waiting for response...")
        response = sock.recv(1024)
        if response:
            print(f"📥 Response received: {response.decode()}")
            print("✅ AGI server is working!")
        else:
            print("📥 No response received")
        
        sock.close()
        
        # Stop server
        server.stop()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_agi()
