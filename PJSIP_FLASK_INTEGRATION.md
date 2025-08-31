# 🎯 PJSIP + Flask Integration Setup Guide

This guide will help you set up your PJSIP Asterisk system to forward calls to your Flask VOIP application.

## 📋 **What We're Setting Up**

```
Softphone → Asterisk (192.168.3.6) → SIP2SIP → Flask App (127.0.0.1:5000/calls)
```

- **Your softphone** calls extension 100
- **Asterisk** receives the call via PJSIP
- **SIP2SIP** handles external connectivity
- **Flask app** receives the call at `/asterisk/incoming`

## 🚀 **Step 1: Copy Configuration Files**

Copy these files to your Asterisk configuration directory:

### **pjsip.conf** → `C:\Program Files\Asterisk\etc\asterisk\`
### **extensions.conf** → `C:\Program Files\Asterisk\etc\asterisk\`

## 🔧 **Step 2: Reload Asterisk Configuration**

Open Asterisk CLI and run:

```bash
asterisk -rx "pjsip reload"
asterisk -rx "dialplan reload"
```

## 📱 **Step 3: Configure Your Softphone**

Configure your softphone with these settings:

- **SIP Server**: `192.168.3.6`
- **Port**: `5060`
- **Username**: `1001` (or any extension from pjsip.conf)
- **Password**: `password123` (from pjsip.conf)
- **Transport**: `UDP`

## 🧪 **Step 4: Test the Integration**

1. **Register your softphone** with Asterisk
2. **Call extension 100** from your softphone
3. **Check your Flask app** at `/calls` - the call should appear
4. **Verify the call** is logged in your database

## 🔍 **Step 5: Troubleshooting**

### **Check PJSIP Status**
```bash
asterisk -rx "pjsip show endpoints"
asterisk -rx "pjsip show registrations"
asterisk -rx "pjsip show contacts"
```

### **Check Dialplan**
```bash
asterisk -rx "dialplan show internal"
asterisk -rx "dialplan show incoming"
```

### **Check Flask Integration**
- Ensure your Flask app is running on port 5000
- Check the `/asterisk/incoming` endpoint is accessible
- Monitor Flask logs for incoming calls

## 📊 **How It Works**

1. **Softphone calls 100** → Asterisk receives via PJSIP
2. **Asterisk routes** to `[internal]` context
3. **Extension 100** executes AGI command
4. **AGI calls** `http://127.0.0.1:5000/asterisk/incoming`
5. **Flask app** processes the call and stores it in database
6. **Call appears** in your `/calls` interface

## 🎯 **Key Benefits**

- ✅ **Real-time call integration** with your Flask app
- ✅ **Automatic call logging** to database
- ✅ **SIP2SIP connectivity** maintained
- ✅ **Local extensions** for testing
- ✅ **Modern PJSIP** instead of legacy SIP

## 🔒 **Security Notes**

- Change default passwords in `pjsip.conf`
- Use strong authentication for extensions
- Consider firewall rules for SIP traffic
- Monitor for unauthorized access attempts

## 📞 **Testing Scenarios**

1. **Local call**: Call 100 from your softphone
2. **External call**: Call your SIP2SIP number
3. **Extension call**: Call 1001, 1002, etc.
4. **Flask integration**: Verify calls appear in web interface

## 🆘 **Common Issues**

### **Softphone won't register**
- Check IP address and port
- Verify username/password match pjsip.conf
- Check firewall settings

### **Calls not reaching Flask**
- Verify Flask app is running on port 5000
- Check Asterisk logs for AGI errors
- Test `/asterisk/incoming` endpoint manually

### **SIP2SIP not working**
- Check internet connectivity
- Verify SIP2SIP credentials
- Check PJSIP registration status

## 🎉 **Success Indicators**

- ✅ Softphone registers with Asterisk
- ✅ Calls to extension 100 work
- ✅ Calls appear in Flask app
- ✅ Database records are created
- ✅ SIP2SIP connectivity maintained

---

**Need help?** Check Asterisk logs and Flask application logs for detailed error messages.
