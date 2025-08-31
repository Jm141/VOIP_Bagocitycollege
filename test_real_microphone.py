#!/usr/bin/env python3
"""
Real Microphone Recording Test
This script helps test the voice recording functionality with actual microphone input
"""
import requests
import time
import json
import os
import webbrowser
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_PHONE_NUMBER = "1234567890"

def check_server_status():
    """Check if the VOIP server is running"""
    print("🔍 Checking server status...")
    
    try:
        response = requests.get(f"{BASE_URL}/test-system", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is running")
            print(f"   - Database: {data.get('database', 'Unknown')}")
            print(f"   - Audio Recording: {data.get('audio_recording', 'Unknown')}")
            print(f"   - Active Calls: {data.get('active_calls', 0)}")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Make sure the server is running with: python app_direct_mysql.py")
        return False

def simulate_incoming_call():
    """Create a simulated incoming call"""
    print("📞 Creating simulated incoming call...")
    
    try:
        response = requests.get(f"{BASE_URL}/simulate-call?number={TEST_PHONE_NUMBER}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                call_id = data['call_id']
                print(f"✅ Call created successfully: {call_id}")
                print(f"   - Caller ID: {data['call_data']['caller_id']}")
                print(f"   - Status: {data['call_data']['status']}")
                return call_id
            else:
                print(f"❌ Call creation failed: {data.get('error')}")
                return None
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error creating call: {e}")
        return None

def open_browser_interfaces():
    """Open the browser interfaces for testing"""
    print("🌐 Opening browser interfaces...")
    
    # Open phone simulator
    phone_url = f"{BASE_URL}/phone"
    print(f"   📱 Opening Phone Simulator: {phone_url}")
    webbrowser.open(phone_url)
    
    time.sleep(2)
    
    # Open admin interface
    admin_url = f"{BASE_URL}/calls"
    print(f"   👨‍💼 Opening Admin Interface: {admin_url}")
    webbrowser.open(admin_url)
    
    print("\n" + "="*60)
    print("🎯 BROWSER INTERFACES OPENED")
    print("="*60)
    print("Two browser tabs should now be open:")
    print("1. 📱 Phone Simulator - This simulates the caller's phone")
    print("2. 👨‍💼 Admin Interface - This is where you answer/manage calls")
    print("="*60)

def wait_for_call_answer(call_id, timeout=60):
    """Wait for the call to be answered"""
    print(f"⏳ Waiting for call {call_id} to be answered...")
    print("   👆 Go to the Admin Interface and click 'Answer' on the incoming call")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/api/calls")
            if response.status_code == 200:
                data = response.json()
                calls = data.get('data', [])
                
                for call in calls:
                    if call['call_id'] == call_id:
                        if call['status'] == 'answered':
                            print(f"✅ Call {call_id} has been answered!")
                            return True
                        elif call['status'] in ['rejected', 'ended']:
                            print(f"❌ Call was {call['status']}")
                            return False
            
            time.sleep(2)
            print("   ⏳ Still waiting for call to be answered...")
            
        except Exception as e:
            print(f"   ⚠️ Error checking call status: {e}")
            time.sleep(2)
    
    print(f"⏰ Timeout waiting for call to be answered")
    return False

def guide_microphone_test():
    """Guide the user through microphone testing"""
    print("\n" + "="*60)
    print("🎤 MICROPHONE RECORDING TEST")
    print("="*60)
    print("Now you'll test real microphone recording:")
    print("")
    print("1. 📱 Go to the Phone Simulator tab")
    print("2. 🔊 Allow microphone access when prompted")
    print("3. 🎵 Click 'Test 5s Recording' to verify your microphone works")
    print("4. ▶️ Click 'Play Test Audio' to hear your recording")
    print("5. ✅ If the test works, your microphone is ready!")
    print("")
    print("After testing, you can:")
    print("- 📞 Make a call by clicking the green call button")
    print("- 🎤 Speak into your microphone during the call")
    print("- 📝 Your voice will be recorded automatically")
    print("="*60)
    
    input("Press Enter after you've tested your microphone...")

def monitor_recording(call_id, duration=30):
    """Monitor the recording progress"""
    print(f"📊 Monitoring recording for call {call_id}...")
    print("   🎤 Speak into your microphone now!")
    print(f"   ⏱️ Recording for {duration} seconds...")
    
    start_time = time.time()
    last_frames = 0
    
    while time.time() - start_time < duration:
        try:
            # Check if call is still active and recording
            response = requests.get(f"{BASE_URL}/api/calls")
            if response.status_code == 200:
                data = response.json()
                calls = data.get('data', [])
                
                call_found = False
                for call in calls:
                    if call['call_id'] == call_id:
                        call_found = True
                        if call['status'] == 'answered' and call.get('recording', False):
                            elapsed = int(time.time() - start_time)
                            remaining = duration - elapsed
                            print(f"   🔴 Recording... {elapsed}s elapsed, {remaining}s remaining")
                        elif call['status'] == 'ended':
                            print(f"   📞 Call ended")
                            return True
                        break
                
                if not call_found:
                    print(f"   ⚠️ Call {call_id} not found in active calls")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"   ⚠️ Error monitoring recording: {e}")
            time.sleep(3)
    
    print(f"   ⏰ Recording time completed")
    return True

def check_recording_file(call_id):
    """Check if the recording file was created and analyze it"""
    print(f"📁 Checking recording file for call {call_id}...")
    
    recording_path = f"recordings/call_{call_id}.wav"
    
    if os.path.exists(recording_path):
        file_size = os.path.getsize(recording_path)
        print(f"✅ Recording file found: {recording_path}")
        print(f"📊 File size: {file_size:,} bytes")
        
        # Analyze file size to determine if it's real audio
        if file_size > 100000:  # More than 100KB
            print(f"🎵 Excellent! This is a substantial recording with real audio content")
        elif file_size > 90000:  # More than ~1 second of silence
            print(f"🎵 Good! This appears to be a real recording (not just silence)")
        else:
            print(f"🔇 This appears to be a silent recording (fallback)")
            print(f"   This might happen if:")
            print(f"   - Microphone access was denied")
            print(f"   - No audio was captured")
            print(f"   - WebM conversion failed")
        
        return True, file_size
    else:
        print(f"❌ Recording file not found: {recording_path}")
        return False, 0

def list_all_recordings():
    """List all recording files"""
    print("\n📋 All recordings in directory:")
    recordings_dir = "recordings"
    
    if not os.path.exists(recordings_dir):
        print("   📁 No recordings directory found")
        return
    
    files = [f for f in os.listdir(recordings_dir) if f.endswith('.wav')]
    if not files:
        print("   📁 No WAV files found")
        return
    
    # Sort by modification time (newest first)
    files_with_time = []
    for file in files:
        file_path = os.path.join(recordings_dir, file)
        file_size = os.path.getsize(file_path)
        mod_time = os.path.getmtime(file_path)
        files_with_time.append((file, file_size, mod_time))
    
    files_with_time.sort(key=lambda x: x[2], reverse=True)
    
    for file, file_size, mod_time in files_with_time:
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        if file_size > 90000:
            status = "🎵 Real Audio"
        else:
            status = "🔇 Silent"
        print(f"   📁 {file}: {file_size:,} bytes ({status}) - {mod_time_str}")

def main():
    """Run the complete real microphone test"""
    print("🎯 REAL MICROPHONE RECORDING TEST")
    print("=" * 60)
    print("This test will help you verify that real microphone")
    print("recording works with your VOIP system.")
    print("=" * 60)
    
    # Step 1: Check server
    if not check_server_status():
        print("\n❌ Cannot proceed without server running")
        return
    
    # Step 2: Create incoming call
    call_id = simulate_incoming_call()
    if not call_id:
        print("\n❌ Cannot proceed without a call")
        return
    
    print(f"\n📱 Test Call ID: {call_id}")
    
    # Step 3: Open browser interfaces
    open_browser_interfaces()
    
    # Step 4: Guide microphone testing
    guide_microphone_test()
    
    # Step 5: Wait for call to be answered
    if not wait_for_call_answer(call_id):
        print("\n❌ Call was not answered - test cannot continue")
        return
    
    # Step 6: Monitor recording
    print("\n🎤 RECORDING PHASE")
    print("Speak clearly into your microphone for the next 30 seconds...")
    monitor_recording(call_id, duration=30)
    
    # Step 7: End call instruction
    print("\n📞 Now end the call:")
    print("   👆 Go to the Admin Interface and click 'Hangup' or")
    print("   👆 Go to the Phone Simulator and click the red hangup button")
    
    # Wait for call to end
    print("\n⏳ Waiting for call to end...")
    timeout = 60
    start_time = time.time()
    call_ended = False
    
    while time.time() - start_time < timeout and not call_ended:
        try:
            response = requests.get(f"{BASE_URL}/api/calls")
            if response.status_code == 200:
                data = response.json()
                calls = data.get('data', [])
                
                call_found = False
                for call in calls:
                    if call['call_id'] == call_id:
                        call_found = True
                        if call['status'] == 'ended':
                            call_ended = True
                            print("✅ Call has ended")
                        break
                
                if not call_found:
                    call_ended = True
                    print("✅ Call completed (no longer in active calls)")
            
            if not call_ended:
                time.sleep(3)
                
        except Exception as e:
            print(f"⚠️ Error checking call status: {e}")
            time.sleep(3)
    
    if not call_ended:
        print("⏰ Timeout waiting for call to end, checking recordings anyway...")
    
    # Step 8: Check recording results
    print("\n📁 RECORDING RESULTS")
    time.sleep(3)  # Wait for file system
    
    found, file_size = check_recording_file(call_id)
    
    # Step 9: Show all recordings
    list_all_recordings()
    
    # Step 10: Final results
    print("\n" + "=" * 60)
    print("🎯 REAL MICROPHONE TEST RESULTS")
    print("=" * 60)
    
    if found and file_size > 90000:
        print("✅ SUCCESS! Real microphone recording is working!")
        print("   - Recording file created")
        print("   - File contains actual audio content")
        print("   - System is ready for production use")
    elif found:
        print("⚠️ PARTIAL SUCCESS - Recording file created but may be silent")
        print("   - Check microphone permissions in browser")
        print("   - Ensure you spoke during the recording")
        print("   - Try the test again")
    else:
        print("❌ FAILED - No recording file created")
        print("   - Check server logs for errors")
        print("   - Verify FFmpeg is working")
        print("   - Check file permissions")
    
    print("\n💡 To test again:")
    print("   1. Run this script again: python test_real_microphone.py")
    print("   2. Or use the browser interfaces directly")
    print("   3. Check server logs for detailed error information")
    print("=" * 60)

if __name__ == "__main__":
    main() 