#!/usr/bin/env python3
"""
Simple test to check AGI server connection handling
"""

import socket
import time

def test_agi_connection():
    """Test AGI server connection directly"""
    
    print("🔍 Simple AGI Connection Test")
    print("=" * 40)
    
    try:
        # Connect to AGI server
        print("📡 Connecting to AGI server on localhost:5001...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 5001))
        print("✅ Connected to AGI server")
        
        # Send a simple AGI request
        print("📤 Sending AGI request...")
        agi_request = "agi_callerid: 1234567890\nagi_extension: 1412\nagi_uniqueid: test_123\n\n"
        print(f"Request: {repr(agi_request)}")
        
        sock.send(agi_request.encode())
        print("✅ Request sent")
        
        # Wait for response with shorter timeout
        print("⏳ Waiting for response (5 second timeout)...")
        sock.settimeout(5)
        
        try:
            response = sock.recv(1024)
            if response:
                print(f"📥 Response received: {response.decode()}")
                print("✅ AGI server is working!")
            else:
                print("📥 No response received")
        except socket.timeout:
            print("⏰ Timeout waiting for response")
            print("❌ AGI server is not processing requests properly")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agi_connection()
