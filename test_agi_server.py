#!/usr/bin/env python3
"""
Test script to verify AGI server functionality
"""

import socket
import time
import threading

def test_agi_server():
    """Test if AGI server is running and accepting connections"""
    
    print("🔍 Testing AGI Server Functionality")
    print("=" * 50)
    
    # Test 1: Check if port 5001 is listening
    print("\n📡 Test 1: Checking if port 5001 is listening...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 5001))
        sock.close()
        
        if result == 0:
            print("✅ Port 5001 is open and listening")
        else:
            print("❌ Port 5001 is not accessible")
            print("   This means the AGI server is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False
    
    # Test 2: Try to connect to AGI server
    print("\n🔌 Test 2: Testing AGI server connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 5001))
        print("✅ Successfully connected to AGI server")
        
        # Send a test AGI request
        print("📤 Sending test AGI request...")
        test_request = """agi_callerid: 1234567890
agi_extension: 1412
agi_uniqueid: test_123
agi_channel: SIP/test-123

"""
        sock.send(test_request.encode())
        
        # Wait for response
        print("⏳ Waiting for response...")
        response = sock.recv(1024).decode()
        print(f"📥 Received response: {response}")
        
        sock.close()
        print("✅ AGI server is responding to requests")
        
    except Exception as e:
        print(f"❌ Error testing AGI connection: {e}")
        return False
    
    print("\n🎉 AGI Server Test Passed!")
    print("The AGI server is running and accepting connections.")
    print("If calls still don't appear, the issue is in the call processing pipeline.")
    
    return True

def test_flask_app():
    """Test if Flask app can start AGI server"""
    
    print("\n🧪 Test 3: Testing Flask App AGI Server Initialization...")
    
    try:
        # Import the app to trigger initialization
        import app_direct_mysql
        
        print("✅ Flask app imported successfully")
        print("✅ AGI server should be initialized")
        
        # Check if agi_server exists and has required attributes
        if hasattr(app_direct_mysql, 'agi_server'):
            agi_server = app_direct_mysql.agi_server
            print(f"✅ AGI server object exists: {agi_server}")
            print(f"✅ AGI server host: {agi_server.host}")
            print(f"✅ AGI server port: {agi_server.port}")
            print(f"✅ AGI server running: {agi_server.running}")
            print(f"✅ AGI server socketio_instance: {agi_server.socketio_instance is not None}")
        else:
            print("❌ AGI server object not found in Flask app")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Flask app: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting AGI Server Tests...")
    
    # Test Flask app initialization
    if not test_flask_app():
        print("\n❌ Flask app test failed")
        exit(1)
    
    # Test AGI server connectivity
    if not test_agi_server():
        print("\n❌ AGI server test failed")
        print("\n🔍 Troubleshooting:")
        print("1. Make sure Flask app is running")
        print("2. Check if port 5001 is not blocked by firewall")
        print("3. Check Flask console for AGI server startup logs")
        exit(1)
    
    print("\n🎯 All Tests Passed!")
    print("Your AGI server is working correctly.")
    print("If calls still don't appear in the calls page,")
    print("the issue is likely in the call processing or Socket.IO emission.")
