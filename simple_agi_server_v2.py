#!/usr/bin/env python3
"""
Simple AGI server v2 - reading data in chunks with Flask integration
"""

import socket
import threading
import time
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleAGIServerV2:
    def __init__(self, host='0.0.0.0', port=5001, flask_url='http://127.0.0.1:5000'):
        self.host = host
        self.port = port
        self.flask_url = flask_url
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the AGI server"""
        try:
            logger.info(f"Starting AGI server on {self.host}:{self.port}")
            logger.info(f"Flask integration URL: {self.flask_url}")
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info(f"AGI server started successfully")
            
            # Start server in main thread for simplicity
            self._accept_connections()
            
        except Exception as e:
            logger.error(f"Failed to start AGI server: {e}")
            return False
        
        return True
    
    def _accept_connections(self):
        """Accept incoming AGI connections"""
        logger.info("Waiting for AGI connections...")
        
        while self.running:
            try:
                logger.debug("Calling accept()...")
                client_socket, address = self.server_socket.accept()
                logger.info(f"AGI connection accepted from {address}")
                
                # Handle connection in main thread for simplicity
                self._handle_agi_connection(client_socket, address)
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting AGI connection: {e}")
                else:
                    break
    
    def _handle_agi_connection(self, client_socket, address):
        """Handle individual AGI connection"""
        try:
            logger.info(f"Handling AGI connection from {address}")
            
            # Read AGI environment variables
            agi_vars = {}
            logger.debug("Reading AGI environment variables...")
            
            # Read all data first
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                logger.debug(f"Received chunk: {chunk}")
                
                # Check if we have the end marker (double newline)
                if b'\n\n' in data:
                    break
            
            logger.debug(f"Total data received: {data}")
            
            # Decode and split into lines
            lines = data.decode('utf-8').split('\n')
            logger.debug(f"Split into {len(lines)} lines")
            
            for line in lines:
                line = line.strip()
                logger.debug(f"Processing line: '{line}'")
                
                if not line:  # Empty line marks end of environment variables
                    logger.debug("Empty line found, end of environment variables")
                    break
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    agi_vars[key.strip()] = value.strip()
                    logger.debug(f"Parsed AGI variable: {key.strip()} = {value.strip()}")
            
            logger.info(f"AGI variables: {agi_vars}")
            
            # Process the AGI request
            logger.info("Processing AGI request...")
            
            # Extract call information
            caller_id = agi_vars.get('agi_callerid', 'Unknown')
            extension = agi_vars.get('agi_extension', '1412')
            unique_id = agi_vars.get('agi_uniqueid', 'test_123')
            channel = agi_vars.get('agi_channel', '')
            
            logger.info(f"AGI call received - Caller: {caller_id}, Extension: {extension}, Channel: {channel}")
            
            # Notify Flask app about the incoming call
            self._notify_flask_app(caller_id, extension, unique_id, channel)
            
            # Return success response to Asterisk
            response = "200 result=0\n"
            logger.debug(f"Sending response: {response}")
            client_socket.send(response.encode())
            
            logger.info("AGI request processed successfully")
            
        except Exception as e:
            logger.error(f"Error handling AGI connection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.debug("Closing AGI connection")
            client_socket.close()
    
    def _notify_flask_app(self, caller_id, extension, unique_id, channel):
        """Notify Flask app about incoming call via HTTP"""
        try:
            # Prepare call data
            call_data = {
                'callerid': caller_id,
                'extension': extension,
                'uniqueid': unique_id,
                'channel': channel,
                'timestamp': time.time()
            }
            
            logger.info(f"Notifying Flask app about call: {call_data}")
            
            # Send HTTP request to Flask app
            response = requests.post(
                f"{self.flask_url}/asterisk/extension1412",
                data=call_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully notified Flask app about call {unique_id}")
                logger.debug(f"Flask response: {response.text}")
            else:
                logger.warning(f"Flask app returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to notify Flask app: {e}")
        except Exception as e:
            logger.error(f"Unexpected error notifying Flask app: {e}")
    
    def stop(self):
        """Stop the AGI server"""
        logger.info("Stopping AGI server...")
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("AGI server stopped")

def test_simple_agi_v2():
    """Test the simple AGI server v2"""
    print("🚀 Testing Simple AGI Server V2")
    print("=" * 40)
    
    server = SimpleAGIServerV2()
    
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
    # Start the actual AGI server
    server = SimpleAGIServerV2()
    print("🚀 Starting AGI Server...")
    print("=" * 40)
    print(f"Host: {server.host}")
    print(f"Port: {server.port}")
    print(f"Flask URL: {server.flask_url}")
    print("=" * 40)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping AGI server...")
        server.stop()
        print("✅ AGI server stopped")
