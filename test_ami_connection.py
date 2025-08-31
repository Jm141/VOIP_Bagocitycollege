#!/usr/bin/env python3
"""
Test script to verify AMI connection between Flask PC and Asterisk PC
Run this on your Flask PC to test connectivity
"""

import socket
import sys
import time

def test_network_connectivity(host, port):
    """Test basic network connectivity"""
    print(f"🔍 Testing network connectivity to {host}:{port}")
    
    try:
        # Test basic ping-like connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Network connectivity: SUCCESS - Port {port} is reachable")
            return True
        else:
            print(f"❌ Network connectivity: FAILED - Port {port} is not reachable")
            return False
            
    except Exception as e:
        print(f"❌ Network connectivity: ERROR - {e}")
        return False

def test_ami_connection(host, port, username, secret):
    """Test AMI connection and authentication"""
    print(f"\n🔐 Testing AMI connection to {host}:{port}")
    
    try:
        # Connect to AMI
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Wait for Asterisk greeting
        greeting = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"📡 Asterisk greeting: {greeting.strip()}")
        
        # Send login
        login_msg = f"Action: Login\r\nUsername: {username}\r\nSecret: {secret}\r\n\r\n"
        sock.send(login_msg.encode())
        
        # Get response
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"🔑 Login response: {response.strip()}")
        
        if "Success" in response:
            print("✅ AMI authentication: SUCCESS")
            
            # Test a simple action
            status_msg = "Action: Status\r\n\r\n"
            sock.send(status_msg.encode())
            
            status_response = sock.recv(1024).decode('utf-8', errors='ignore')
            print(f"📊 Status response: {status_response.strip()}")
            
            # Logout
            logout_msg = "Action: Logoff\r\n\r\n"
            sock.send(logout_msg.encode())
            
            sock.close()
            return True
        else:
            print("❌ AMI authentication: FAILED")
            sock.close()
            return False
            
    except Exception as e:
        print(f"❌ AMI connection: ERROR - {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Asterisk AMI Connection Test")
    print("=" * 50)
    
    # Get configuration
    try:
        from asterisk_ami_config import AMI_HOST, AMI_PORT, AMI_USERNAME, AMI_SECRET
        print(f"📋 Configuration loaded from asterisk_ami_config.py")
    except ImportError:
        print("⚠️  asterisk_ami_config.py not found, using defaults")
        AMI_HOST = '192.168.1.100'  # Change this to your Asterisk PC's IP
        AMI_PORT = 5038
        AMI_USERNAME = 'admin'
        AMI_SECRET = 'your_secret'
    
    print(f"📍 Target: {AMI_HOST}:{AMI_PORT}")
    print(f"👤 Username: {AMI_USERNAME}")
    print(f"🔑 Secret: {'*' * len(AMI_SECRET)}")
    print()
    
    # Test 1: Network connectivity
    if not test_network_connectivity(AMI_HOST, AMI_PORT):
        print("\n❌ Network test failed. Please check:")
        print("   1. Both PCs are on the same network")
        print("   2. Asterisk PC is running")
        print("   3. Windows Firewall allows port 5038")
        print("   4. IP address is correct")
        return
    
    # Test 2: AMI connection
    if test_ami_connection(AMI_HOST, AMI_PORT, AMI_USERNAME, AMI_SECRET):
        print("\n🎉 All tests passed! Your Flask app should be able to connect to Asterisk AMI.")
        print("\n📝 Next steps:")
        print("   1. Start your Flask app")
        print("   2. Make a call to extension 1412")
        print("   3. Check Flask logs for AMI connection status")
        print("   4. Visit /extension1412 in your browser")
    else:
        print("\n❌ AMI test failed. Please check:")
        print("   1. Asterisk manager.conf is configured correctly")
        print("   2. Username and secret are correct")
        print("   3. Asterisk manager is enabled and reloaded")
        print("   4. Run 'asterisk -rx \"manager reload\"' on Asterisk PC")

if __name__ == "__main__":
    main()
