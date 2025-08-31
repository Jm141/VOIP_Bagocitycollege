# 🔍 AMI Call Debugging - Issues Found and Fixed

## 🚨 **Root Cause Identified**

The main issue was that **AMI calls were being stored correctly but not displayed in the calls page** because the `/api/calls/public` endpoint was missing the `source` field that identifies AMI calls.

## ✅ **Fixes Applied**

### 1. **Fixed API Endpoint Missing Source Field**
- **Problem**: `/api/calls/public` endpoint wasn't returning `source` and `sip_channel` fields
- **Fix**: Added `source` and `sip_channel` fields to both active calls and database calls
- **Result**: AMI calls now have `source: 'ami'` and can be properly identified

### 2. **Enhanced Debug Logging**
- **AGI Server**: Added detailed logging for call processing and Socket.IO emission
- **Frontend**: Added WebSocket event logging and call processing debug info
- **Result**: Better visibility into what's happening when calls come in

### 3. **Improved Call Data Structure**
- **Active Calls**: Now include `caller_number` field for consistency
- **Database Calls**: Default to `source: 'phone_simulator'` for existing calls
- **Result**: Consistent call data structure across all call types

## 🔧 **Technical Details**

### **Before (Broken)**
```python
# API endpoint was missing source field
all_calls.append({
    'id': call_data['call_id'],
    # ... other fields ...
    # Missing: 'source' and 'sip_channel'
})
```

### **After (Fixed)**
```python
# API endpoint now includes source field
all_calls.append({
    'id': call_data['call_id'],
    # ... other fields ...
    'source': call_data.get('source', 'phone_simulator'),
    'sip_channel': call_data.get('sip_channel')
})
```

## 🧪 **How to Test the Fix**

### **Step 1: Restart Flask App**
```bash
python app_direct_mysql.py
```

### **Step 2: Open Calls Page**
- Navigate to: `http://localhost:5000/calls`
- Open browser console (F12) to see debug logs

### **Step 3: Make AMI Call**
- Call extension 1412 from your phone/SIP client
- Watch Flask console for AGI logs
- Watch browser console for WebSocket events

### **Step 4: Verify Call Appears**
- Call should appear in calls page with AMI badge
- Should show orange styling and "AMI" indicator
- Should be filterable by "AMI Calls" source

## 📊 **Expected Debug Output**

### **Flask Console (AGI Server)**
```
INFO:__main__:AGI connection from ('192.168.3.6', 39192)
INFO:__main__:AGI variables: {'agi_callerid': '1234567890', 'agi_extension': '1412', ...}
INFO:__main__:AGI call received - Caller: 1234567890, Extension: 1412, Channel: ...
INFO:__main__:Storing call ... in database...
INFO:__main__:Call ... stored in database
INFO:__main__:Call ... added to active_calls: {...}
INFO:__main__:Total active calls: 1
INFO:__main__:Notifying Flask app about call ...
INFO:__main__:Emitting 'new_call' event for call ...
INFO:__main__:Emitting 'call_update' event for call ...
INFO:__main__:Socket.IO events emitted for AMI call ...
```

### **Browser Console (Calls Page)**
```
🔌 Initializing WebSocket connection...
✅ WebSocket connected to admin interface
🔌 Socket ID: [socket-id]
📞 New call event received: {call_id: "...", source: "ami", ...}
🔔 Is AMI call? true
📝 Processed new call object: {...}
📊 Updated calls lists - Total calls: 1, Filtered calls: 1
🔔 AMI call detected, showing special notification
```

## 🎯 **What Should Happen Now**

1. **AMI calls appear immediately** in the calls page
2. **Visual distinction** between AMI and phone simulator calls
3. **Real-time updates** via WebSocket
4. **Proper filtering** by call source
5. **Call management** (answer/reject/hangup) works for AMI calls

## 🔍 **If Still Not Working**

### **Check These Points:**
1. **AGI Server**: Is it receiving connections? (Check Flask console)
2. **Socket.IO**: Are events being emitted? (Check Flask console)
3. **WebSocket**: Is browser connecting? (Check browser console)
4. **Call Data**: Is source field present? (Check browser console)

### **Common Issues:**
- **Firewall blocking port 5001** (AGI server)
- **Socket.IO not initialized** properly
- **Browser WebSocket connection** failing
- **Call data format** mismatches

## 🎉 **Expected Result**

After these fixes, when you call extension 1412:
1. ✅ Call appears in calls page immediately
2. ✅ Shows AMI badge and orange styling
3. ✅ Can be answered/rejected/hung up
4. ✅ Appears in AMI calls filter
5. ✅ Updates call source summary cards

The system should now work as intended with both phone simulator and AMI calls appearing in the unified calls page!
