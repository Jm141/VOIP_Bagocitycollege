#!/usr/bin/env python3
"""
Quick test to verify microphone initialization fix
"""
import requests
import time

BASE_URL = "http://localhost:5000"

def test_microphone_access():
    """Test if the microphone initialization fix works"""
    print("🎤 Testing Microphone Initialization Fix")
    print("=" * 50)
    
    # Check server status
    try:
        response = requests.get(f"{BASE_URL}/test-system", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server error: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    print("\n🌐 Opening Phone Simulator...")
    import webbrowser
    webbrowser.open(f"{BASE_URL}/phone")
    
    print("\n📋 INSTRUCTIONS:")
    print("1. The Phone Simulator should now be open in your browser")
    print("2. Look for the 'Test Microphone' button")
    print("3. Click it and allow microphone access when prompted")
    print("4. Speak for 3 seconds when recording starts")
    print("5. You should hear your recording played back")
    
    print("\n🔧 TROUBLESHOOTING:")
    print("- If you see 'Microphone not initialized', click 'Initialize Audio' button")
    print("- Make sure to allow microphone access in your browser")
    print("- Check the browser console for any error messages")
    
    print("\n✅ EXPECTED RESULT:")
    print("- Microphone access granted")
    print("- 3-second recording captured")
    print("- Audio playback of your recording")
    print("- Success message displayed")
    
    print("\n" + "=" * 50)
    print("🎯 Test the microphone now and let me know the results!")

if __name__ == "__main__":
    test_microphone_access() 