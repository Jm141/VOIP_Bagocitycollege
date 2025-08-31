# 🌐 Network Setup Guide: Flask PC ↔ Asterisk PC

## 📋 Prerequisites
- Both PCs must be on the same network (same router/switch)
- Asterisk server must be running on the other PC
- Windows Firewall must allow connections on port 5038

## 🔍 Step 1: Find Your Asterisk PC's IP Address

On your **Asterisk PC**, run:
```cmd
ipconfig
```

Look for the IPv4 address (usually starts with 192.168.x.x or 10.x.x.x)

## 🔧 Step 2: Configure Asterisk AMI

On your **Asterisk PC**, edit the file:
```
C:\Program Files\Asterisk\etc\asterisk\manager.conf
```

Add or modify this section:
```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = your_secure_password_here
read = all
write = all
```

**Important:** 
- `bindaddr = 0.0.0.0` allows connections from any IP
- `secret = your_secure_password_here` - choose a strong password
- Remember the username (`admin`) and secret for the next step

## 🔧 Step 3: Update Flask Configuration

On your **Flask PC**, edit `asterisk_ami_config.py`:

```python
# Change this to your Asterisk PC's actual IP address
AMI_HOST = '192.168.1.100'  # Replace with actual IP from Step 1

# Use the credentials from Step 2
AMI_USERNAME = 'admin'       # Username from manager.conf
AMI_SECRET = 'your_secure_password_here'  # Secret from manager.conf
```

## 🔧 Step 4: Configure Windows Firewall

On your **Asterisk PC**, allow port 5038:

1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → "TCP" → "Specific local ports: 5038"
5. Allow the connection
6. Apply to all profiles
7. Name it "Asterisk AMI"

## 🧪 Step 5: Test Connectivity

On your **Flask PC**, test the connection:

```cmd
# Test if you can reach the Asterisk PC
ping 192.168.1.100

# Test if port 5038 is accessible
telnet 192.168.1.100 5038
```

If telnet works, you should see a blank screen (press Ctrl+C to exit).

## 🔄 Step 6: Reload Asterisk Configuration

On your **Asterisk PC**, reload the configuration:

```cmd
# In Asterisk CLI
asterisk -rx "manager reload"
```

## 🚀 Step 7: Test the Integration

1. Start your Flask app
2. Make a call to extension 1412 from your softphone
3. Check Flask logs for AMI connection status
4. Visit `/extension1412` in your browser

## 🐛 Troubleshooting

### Connection Refused
- Check if Asterisk is running
- Verify port 5038 is open in Windows Firewall
- Check `manager.conf` syntax

### Authentication Failed
- Verify username and secret in `asterisk_ami_config.py`
- Check `manager.conf` credentials
- Reload Asterisk manager: `asterisk -rx "manager reload"`

### Network Unreachable
- Ensure both PCs are on same network
- Check router settings
- Try using IP addresses instead of hostnames

## 📱 Example Softphone Test

1. **Register softphone** with your Asterisk server
2. **Call extension 1412**
3. **Check Flask logs** for incoming call
4. **Visit `/extension1412`** to see the call

## 🔒 Security Notes

- Change default AMI password
- Consider restricting AMI access to specific IPs
- Use HTTPS for Flask if accessible from internet
- Regularly update passwords

## 📞 Support

If you still have issues:
1. Check Asterisk logs: `C:\Program Files\Asterisk\var\log\asterisk\full`
2. Check Flask logs for error messages
3. Verify network connectivity between PCs
4. Test with simple ping/telnet first
