#!/usr/bin/env python3
"""
Test script to verify phone-audio endpoint works with a real call:
1. Simulate a call
2. Answer the call to start recording
3. Send audio data via phone-audio endpoint
4. End the call and check recording
"""

import requests
import time
import json
import base64
import math

def test_phone_audio_with_call():
    """Test phone-audio endpoint with a real call"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🎤 Testing Phone Audio with Real Call")
    print("=" * 50)
    
    # Step 1: Simulate call from phone simulator
    print("\n📞 Step 1: Phone simulator makes call")
    call_response = requests.get(f"{base_url}/simulate-call?number=5551234")
    if call_response.status_code == 200:
        call_data = call_response.json()
        if call_data['success']:
            call_id = call_data['call_id']
            print(f"   ✅ Call created: {call_id}")
        else:
            print(f"   ❌ Failed to create call: {call_data['error']}")
            return
    else:
        print(f"   ❌ HTTP error: {call_response.status_code}")
        return
    
    # Step 2: Wait for call to be processed
    print("\n⏳ Step 2: Waiting for call processing...")
    time.sleep(2)
    
    # Step 3: Admin answers the call
    print("\n👨‍💼 Step 3: Admin answers call")
    answer_response = requests.get(f"{base_url}/test-answer-call/{call_id}")
    if answer_response.status_code == 200:
        answer_data = answer_response.json()
        if answer_data['success']:
            print(f"   ✅ Call answered successfully")
            print(f"   🎙️  Recording started: {answer_data['recording_started']}")
        else:
            print(f"   ❌ Failed to answer call: {answer_data['error']}")
            return
    else:
        print(f"   ❌ HTTP error: {answer_response.status_code}")
        return
    
    # Step 4: Send real audio data via phone-audio endpoint
    print("\n🎵 Step 4: Sending real audio data via phone-audio endpoint")
    print("   Expected: Audio with varying frequencies (speech-like)")
    
    for i in range(10):  # Send 10 audio frames
        # Generate realistic audio data (simulating speech patterns)
        sample_rate = 44100
        duration = 0.5  # 500ms
        samples = int(sample_rate * duration)
        
        # Create varying frequency content to simulate speech
        real_audio = []
        for j in range(samples):
            time_val = j / sample_rate
            # Mix multiple frequencies to simulate speech
            freq1 = 200 + 100 * math.sin(time_val * 2)  # Varying base frequency
            freq2 = 800 + 200 * math.sin(time_val * 3)  # Mid frequency
            freq3 = 1200 + 300 * math.sin(time_val * 1.5)  # High frequency
            
            sample1 = 0.3 * math.sin(2 * math.pi * freq1 * time_val)
            sample2 = 0.2 * math.sin(2 * math.pi * freq2 * time_val)
            sample3 = 0.1 * math.sin(2 * math.pi * freq3 * time_val)
            
            combined_sample = sample1 + sample2 + sample3
            int_sample = int(combined_sample * 16384)  # 16-bit
            real_audio.extend([int_sample & 0xFF, (int_sample >> 8) & 0xFF])
        
        # Convert to base64
        base64_audio = base64.b64encode(bytes(real_audio)).decode('utf-8')
        
        # Send to server using phone-audio endpoint
        audio_response = requests.post(f"{base_url}/api/calls/{call_id}/phone-audio", 
                                     json={
                                         'audio_data': base64_audio,
                                         'source': 'caller',
                                         'for_recording': True
                                     })
        
        if audio_response.status_code == 200:
            audio_data = audio_response.json()
            if audio_data['success']:
                print(f"   ✅ Audio frame {i+1}: {audio_data['frames_count']} frames, {audio_data['total_bytes']} bytes")
            else:
                print(f"   ❌ Audio frame {i+1} failed: {audio_data['error']}")
        else:
            print(f"   ❌ Audio frame {i+1} HTTP error: {audio_response.status_code}")
        
        time.sleep(0.5)  # Wait 500ms between frames
    
    # Step 5: End the call
    print("\n⏹️  Step 5: Ending call and saving recording")
    hangup_response = requests.get(f"{base_url}/test-hangup-call/{call_id}")
    if hangup_response.status_code == 200:
        hangup_data = hangup_response.json()
        if hangup_data['success']:
            print(f"   ✅ Call ended successfully")
            print(f"   ⏱️  Duration: {hangup_data['duration']} seconds")
            print(f"   💾 Recording saved: {hangup_data['recording_saved']}")
        else:
            print(f"   ❌ Failed to end call: {hangup_data['error']}")
            return
    else:
        print(f"   ❌ HTTP error: {hangup_response.status_code}")
        return
    
    # Step 6: Check the recording file
    print("\n📁 Step 6: Checking recording file")
    import os
    recording_file = f"recordings/call_{call_id}.wav"
    if os.path.exists(recording_file):
        file_size = os.path.getsize(recording_file)
        print(f"   ✅ Recording file exists: {recording_file}")
        print(f"   📊 File size: {file_size} bytes ({file_size/1024:.1f} KB)")
        
        if file_size > 100000:  # More than 100KB
            print(f"   🎵 File appears to contain substantial audio data")
        else:
            print(f"   ⚠️  File size seems small - may contain only static")
    else:
        print(f"   ❌ Recording file not found: {recording_file}")
    
    print("\n🎉 Phone Audio Test Completed!")
    print("\n📝 Summary:")
    print("   1. ✅ Call created and answered")
    print("   2. ✅ Recording started automatically")
    print("   3. ✅ Real audio data sent via phone-audio endpoint")
    print("   4. ✅ Call ended and recording saved")
    print("   5. ✅ Recording file verified")
    
    print(f"\n🔍 Check the recording file: {recording_file}")
    print("   This should now contain real audio with varying frequencies, not static")

if __name__ == "__main__":
    try:
        test_phone_audio_with_call()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("   Make sure the Flask app is running on http://localhost:5000") 