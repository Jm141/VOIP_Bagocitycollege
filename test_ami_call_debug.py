#!/usr/bin/env python3
"""
Debug script to test AMI call integration
"""

import requests
import time
import json

def test_ami_call_debug():
    """Test AMI call integration with debug logging"""
    
    base_url = "http://localhost:5000"
    
    print("🔔 Testing AMI Call Integration Debug")
    print("=" * 50)
    
    print("\n📋 Debug Steps:")
    print("1. Make sure Flask app is running")
    print("2. Open calls page in browser: http://localhost:5000/calls")
    print("3. Open browser console to see debug logs")
    print("4. Make a call to extension 1412")
    print("5. Check Flask app console for AGI logs")
    print("6. Check browser console for WebSocket events")
    
    print("\n🔍 What to Look For:")
    print("• Flask console: AGI connection and call processing logs")
    print("• Flask console: Socket.IO event emission logs")
    print("• Browser console: WebSocket connection and event logs")
    print("• Calls page: New call appearance")
    
    print("\n🚨 Common Issues:")
    print("• AGI server not receiving calls")
    print("• Socket.IO events not being emitted")
    print("• WebSocket connection issues")
    print("• Call data format mismatches")
    
    print("\n📱 Test Call Flow:")
    print("1. Call extension 1412 from your phone/SIP client")
    print("2. Check Flask console for AGI logs")
    print("3. Check if call appears in calls page")
    print("4. Check browser console for WebSocket events")
    
    print("\n" + "=" * 50)
    print("🔍 Debug mode enabled - check all console outputs!")

if __name__ == "__main__":
    test_ami_call_debug()
