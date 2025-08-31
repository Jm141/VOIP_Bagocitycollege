# 🎵 VOIP Audio Recording System

A **fully functional VOIP audio recording system** that captures real-time conversations with automatic recording and proper audio quality.

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Start the System**
```bash
python app_direct_mysql.py
```

### **3. Access the System**
- **Phone Simulator**: http://localhost:5000/phone
- **Admin Interface**: http://localhost:5000/calls
- **Login**: admin / admin123

### **4. Make a Test Call**
1. Open phone simulator in one browser tab
2. Open admin calls page in another tab
3. Make a call from phone simulator
4. Answer the call in admin interface
5. Speak into microphone during the call
6. Hang up - recording is automatically saved

## 📁 **File Structure**

```
VOIP/
├── app_direct_mysql.py          # Main Flask application
├── templates/                   # HTML templates
│   ├── phone.html              # Phone simulator interface
│   ├── calls.html              # Admin calls management
│   ├── dashboard.html          # Main dashboard
│   ├── login.html              # Login page
│   └── base.html               # Base template
├── recordings/                  # Audio recordings storage
├── requirements.txt             # Python dependencies
├── test_phone_audio_with_call.py # Test script
└── AUDIO_FORMAT_MISMATCH_FIX.md # Complete documentation
```

## 🎯 **Core Features**

- ✅ **Real-time audio capture** from microphone
- ✅ **Automatic recording** when calls are answered
- ✅ **High-quality WAV files** with proper duration
- ✅ **WebSocket communication** for real-time sync
- ✅ **Test recording functionality** for verification
- ✅ **Admin interface** for call management

## 🔍 **Testing**

### **Quick Test**
Use the test script to verify everything works:
```bash
python test_phone_audio_with_call.py
```

### **Manual Test**
Both phone simulator and admin calls page have **"Test 5s Recording"** buttons that:
1. Record 5 seconds of microphone audio
2. Save the recording
3. Provide **"Play Test Audio"** button for immediate playback

## 📚 **Documentation**

For complete system documentation, troubleshooting, and technical details, see:
**[AUDIO_FORMAT_MISMATCH_FIX.md](AUDIO_FORMAT_MISMATCH_FIX.md)**

## 🎉 **Status**

**The system is fully operational and working perfectly!**
- Real audio recordings with correct duration
- Consistent performance across multiple tests
- Ready for production use

---

*Last Updated: 2025-08-22*
*Status: FULLY OPERATIONAL* 