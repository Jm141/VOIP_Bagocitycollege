#!/usr/bin/env python3
"""
Test script to verify voice recording functionality
"""
import requests
import time
import json
import base64
import os

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_PHONE_NUMBER = "1234567890"

def test_call_simulation():
    """Test creating a simulated call"""
    print("🔔 Testing call simulation...")
    
    try:
        response = requests.get(f"{BASE_URL}/simulate-call?number={TEST_PHONE_NUMBER}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                call_id = data['call_id']
                print(f"✅ Call simulated successfully: {call_id}")
                return call_id
            else:
                print(f"❌ Call simulation failed: {data.get('error')}")
                return None
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error simulating call: {e}")
        return None

def test_call_answer(call_id):
    """Test answering the call to start recording"""
    print(f"📞 Testing call answer for {call_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/test-answer-call/{call_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Call answered successfully")
                return True
            else:
                print(f"❌ Call answer failed: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error answering call: {e}")
        return False

def test_audio_sending(call_id):
    """Test sending audio data to the call"""
    print(f"🎤 Testing audio sending for {call_id}...")
    
    try:
        # Generate some test audio data (simulating real voice)
        # This creates a simple sine wave that should be valid audio
        import math
        
        sample_rate = 44100
        duration = 2.0  # 2 seconds
        frequency = 440  # A4 note
        
        # Generate audio samples
        samples = []
        for i in range(int(sample_rate * duration)):
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
            samples.append(sample)
        
        # Convert to bytes (16-bit PCM)
        audio_data = b''.join([sample.to_bytes(2, byteorder='little', signed=True) for sample in samples])
        
        # Convert to base64
        base64_audio = base64.b64encode(audio_data).decode('utf-8')
        
        # Send audio data
        payload = {
            'audio_data': base64_audio,
            'source': 'caller',
            'for_recording': True,
            'is_complete_file': True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/{call_id}/phone-audio",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Audio sent successfully: {data.get('frames_count')} frames, {data.get('total_bytes')} bytes")
                return True
            else:
                print(f"❌ Audio sending failed: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending audio: {e}")
        return False

def test_call_hangup(call_id):
    """Test hanging up the call to save recording"""
    print(f"📞 Testing call hangup for {call_id}...")
    
    try:
        response = requests.get(f"{BASE_URL}/test-hangup-call/{call_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Call hung up successfully")
                return True
            else:
                print(f"❌ Call hangup failed: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error hanging up call: {e}")
        return False

def check_recording_file(call_id):
    """Check if recording file was created"""
    print(f"📁 Checking recording file for {call_id}...")
    
    recording_path = f"recordings/call_{call_id}.wav"
    
    if os.path.exists(recording_path):
        file_size = os.path.getsize(recording_path)
        print(f"✅ Recording file found: {recording_path}")
        print(f"📊 File size: {file_size} bytes")
        
        # Check if it's a real recording (not just silence)
        if file_size > 90000:  # More than ~1 second of silence
            print(f"🎵 This appears to be a real recording (not just silence)")
        else:
            print(f"🔇 This appears to be a silent recording (fallback)")
        
        return True
    else:
        print(f"❌ Recording file not found: {recording_path}")
        return False

def test_webm_audio_sending(call_id):
    """Test sending WebM audio data (more realistic test)"""
    print(f"🎤 Testing WebM audio sending for {call_id}...")
    
    try:
        # Create a simple WebM-like audio structure
        # This is a minimal valid WebM header + some audio data
        webm_header = b'\x1a\x45\xdf\xa3'  # EBML signature
        webm_header += b'\x01\x00\x00\x00\x00\x00\x00'  # EBML version
        
        # Add some dummy audio data
        audio_data = b'\x00' * 1000  # 1KB of audio data
        
        # Combine header and audio
        webm_audio = webm_header + audio_data
        
        # Convert to base64
        base64_audio = base64.b64encode(webm_audio).decode('utf-8')
        
        # Send audio data
        payload = {
            'audio_data': base64_audio,
            'source': 'caller',
            'for_recording': True,
            'is_complete_file': True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/{call_id}/phone-audio",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ WebM audio sent successfully: {data.get('frames_count')} frames, {data.get('total_bytes')} bytes")
                return True
            else:
                print(f"❌ WebM audio sending failed: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending WebM audio: {e}")
        return False

def main():
    """Run the complete recording test"""
    print("🎯 Starting Voice Recording Test")
    print("=" * 50)
    
    # Step 1: Simulate a call
    call_id = test_call_simulation()
    if not call_id:
        print("❌ Cannot proceed without a call ID")
        return
    
    print(f"\n📱 Call ID: {call_id}")
    
    # Step 2: Answer the call to start recording
    if not test_call_answer(call_id):
        print("❌ Cannot proceed without answering the call")
        return
    
    print("\n⏳ Waiting 2 seconds for recording to initialize...")
    time.sleep(2)
    
    # Step 3: Send PCM audio data
    print("\n🎵 Testing PCM audio sending...")
    test_audio_sending(call_id)
    
    # Step 4: Send WebM audio data
    print("\n🎵 Testing WebM audio sending...")
    test_webm_audio_sending(call_id)
    
    # Step 5: Wait a bit more for audio processing
    print("\n⏳ Waiting 3 seconds for audio processing...")
    time.sleep(3)
    
    # Step 6: Hang up the call to save recording
    if not test_call_hangup(call_id):
        print("❌ Cannot save recording without hanging up")
        return
    
    # Step 7: Check if recording file was created
    print("\n📁 Checking recording results...")
    time.sleep(2)  # Wait for file system
    check_recording_file(call_id)
    
    print("\n" + "=" * 50)
    print("🎯 Voice Recording Test Complete!")
    
    # List all recordings
    print("\n📋 All recordings in directory:")
    recordings_dir = "recordings"
    if os.path.exists(recordings_dir):
        files = [f for f in os.listdir(recordings_dir) if f.endswith('.wav')]
        for file in sorted(files):
            file_path = os.path.join(recordings_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"  📁 {file}: {file_size} bytes")

if __name__ == "__main__":
    main() 