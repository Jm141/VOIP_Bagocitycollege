# 🌐 PJSIP Port Forwarding Setup Guide

This guide provides step-by-step instructions for setting up port forwarding and configuring PJSIP to make your Asterisk server accessible from the internet.

## 📋 **Prerequisites**

- ✅ Asterisk server running with PJSIP
- ✅ Local SIP extensions working (both numbers reachable)
- ✅ SSH access to your Asterisk server
- ✅ Access to your router's admin panel
- ✅ Basic understanding of networking

## 🔍 **Phase 1: Port Forwarding Setup**

### **Step 1: Find Your Router's IP Address**
```bash
# On your local machine (not the Asterisk server)
# Windows
ipconfig

# Linux/Mac
ip route show default

# Look for "Default Gateway" - this is your router's IP
# Usually 192.168.1.1, 192.168.0.1, or 10.0.0.1
```

### **Step 2: Find Your Asterisk Server's Local IP**
```bash
# SSH into your Asterisk server and run:
ip addr show
# or
hostname -I

# Note the IP address (e.g., 192.168.1.100)
```

### **Step 3: Access Your Router's Admin Panel**
1. Open a web browser on your local machine
2. Navigate to your router's IP address (e.g., `http://192.168.1.1`)
3. Enter admin credentials (check router label or manual)
4. Look for "Port Forwarding", "Virtual Server", or "NAT" section

### **Step 4: Configure Port Forwarding Rules**

#### **📡 TP-Link Routers**
1. Go to **Advanced** → **NAT Forwarding** → **Virtual Servers**
2. Click **Add New**
3. Add these rules:

**Rule 1 - SIP Signaling (UDP):**
- Service Port: `5060`
- Internal Port: `5060`
- IP Address: `YOUR_ASTERISK_SERVER_IP` (e.g., 192.168.1.100)
- Protocol: `UDP`
- Status: `Enabled`

**Rule 2 - SIP Signaling (TCP fallback):**
- Service Port: `5060`
- Internal Port: `5060`
- IP Address: `YOUR_ASTERISK_SERVER_IP`
- Protocol: `TCP`
- Status: `Enabled`

**Rule 3 - RTP Media Range:**
- Service Port: `10000-20000`
- Internal Port: `10000-20000`
- IP Address: `YOUR_ASTERISK_SERVER_IP`
- Protocol: `UDP`
- Status: `Enabled`

#### **📡 Netgear Routers**
1. Go to **Advanced** → **Port Forwarding/Port Triggering**
2. Click **Add Custom Service**
3. Add these services:

**Service 1 - Asterisk SIP UDP:**
- Service Name: `Asterisk SIP UDP`
- Service Type: `UDP`
- External Starting Port: `5060`
- External Ending Port: `5060`
- Internal Starting Port: `5060`
- Internal Ending Port: `5060`
- Internal IP Address: `YOUR_ASTERISK_SERVER_IP`

**Service 2 - Asterisk SIP TCP:**
- Service Name: `Asterisk SIP TCP`
- Service Type: `TCP`
- External Starting Port: `5060`
- External Ending Port: `5060`
- Internal Starting Port: `5060`
- Internal Ending Port: `5060`
- Internal IP Address: `YOUR_ASTERISK_SERVER_IP`

**Service 3 - Asterisk RTP:**
- Service Name: `Asterisk RTP`
- Service Type: `UDP`
- External Starting Port: `10000`
- External Ending Port: `20000`
- Internal Starting Port: `10000`
- Internal Ending Port: `20000`
- Internal IP Address: `YOUR_ASTERISK_SERVER_IP`

#### **📡 Asus Routers**
1. Go to **WAN** → **Virtual Server/Port Forwarding**
2. Click **Add Profile**
3. Add these profiles:

**Profile 1 - SIP UDP:**
- Service Name: `Asterisk SIP UDP`
- Port Range: `5060`
- Local IP: `YOUR_ASTERISK_SERVER_IP`
- Local Port: `5060`
- Protocol: `UDP`

**Profile 2 - SIP TCP:**
- Service Name: `Asterisk SIP TCP`
- Port Range: `5060`
- Local IP: `YOUR_ASTERISK_SERVER_IP`
- Local Port: `5060`
- Protocol: `TCP`

**Profile 3 - RTP:**
- Service Name: `Asterisk RTP`
- Port Range: `10000-20000`
- Local IP: `YOUR_ASTERISK_SERVER_IP`
- Local Port: `10000-20000`
- Protocol: `UDP`

#### **📡 Linksys Routers**
1. Go to **Security** → **Apps and Gaming** → **Single Port Forwarding**
2. Add each port:

**SIP UDP:**
- Application: `Asterisk SIP UDP`
- External Port: `5060`
- Internal Port: `5060`
- Protocol: `UDP`
- To IP Address: `YOUR_ASTERISK_SERVER_IP`

**SIP TCP:**
- Application: `Asterisk SIP TCP`
- External Port: `5060`
- Internal Port: `5060`
- Protocol: `TCP`
- To IP Address: `YOUR_ASTERISK_SERVER_IP`

**RTP:**
- Application: `Asterisk RTP`
- External Port: `10000-20000`
- Internal Port: `10000-20000`
- Protocol: `UDP`
- To IP Address: `YOUR_ASTERISK_SERVER_IP`

#### **📡 Generic Router Instructions**
If your router isn't listed above:
1. Look for **Port Forwarding**, **Virtual Server**, **NAT**, or **Applications & Gaming**
2. Add rules for each port range
3. Ensure protocol matches (UDP for SIP/RTP, TCP for SIP fallback)
4. Set internal IP to your Asterisk server's IP address

### **Step 5: Save and Apply Port Forwarding Rules**
1. Click **Save** or **Apply** for each rule
2. Restart your router if prompted
3. Wait for router to fully restart

## ⚙️ **Phase 2: PJSIP Configuration for External Access**

### **Step 6: Find Your Public IP Address**
```bash
# SSH into your Asterisk server and run:
curl -s ifconfig.me
# or
curl -s ipinfo.io/ip

# Note your public IP address
```

### **Step 7: Update PJSIP Global Configuration**
```bash
# SSH into your Asterisk server
sudo nano /etc/asterisk/pjsip.conf
```

Find the `[global]` section and add/update these lines:
```ini
[global]
type=global
debug=yes

; NAT Configuration for external access
local_net=192.168.1.0/255.255.255.0
external_media_address=YOUR_PUBLIC_IP
external_signaling_address=YOUR_PUBLIC_IP
```

**⚠️ Important:**
- Replace `YOUR_PUBLIC_IP` with your actual public IP address
- Replace `192.168.1.0/255.255.255.0` with your actual local network range

### **Step 8: Update PJSIP Transport Configuration**
Find the `[transport-udp]` section and ensure it looks like this:
```ini
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
```

### **Step 9: Update PJSIP Endpoint Configuration**
For each of your extensions, ensure they have proper NAT settings:
```ini
[1001]
type=endpoint
context=internal
disallow=all
allow=ulaw
allow=alaw
allow=gsm
auth=auth1001
aors=1001
direct_media=no
force_rport=yes
rewrite_contact=yes
rtp_symmetric=yes
force_avp=yes
ice_support=yes
use_ptime=yes
media_use_received_transport=yes
media_address=YOUR_PUBLIC_IP
```

**Repeat for each extension (1002, etc.)**

### **Step 10: Update PJSIP AOR Configuration**
For each extension's AOR section:
```ini
[aor1001]
type=aor
max_contacts=5
remove_existing=yes
qualify_frequency=60
default_expiration=3600
maximum_expiration=7200
minimum_expiration=60
```

### **Step 11: Update PJSIP Auth Configuration**
For each extension's auth section:
```ini
[auth1001]
type=auth
auth_type=userpass
username=1001
password=your_password_here
realm=asterisk
```

## 🧪 **Phase 3: Testing and Verification**

### **Step 12: Reload PJSIP Configuration**
```bash
# In Asterisk CLI
sudo asterisk -r

asterisk*CLI> pjsip reload
asterisk*CLI> dialplan reload
```

### **Step 13: Test Port Forwarding**
```bash
# From your local machine (not the server), test:
telnet YOUR_PUBLIC_IP 5060

# Or use online port checkers:
# - https://canyouseeme.org/
# - https://portchecker.co/
# - https://www.yougetsignal.com/tools/open-ports/
```

### **Step 14: Test External SIP Registration**
1. **Configure SIP client** (like Zoiper) on your phone
2. **Use mobile data** (not WiFi) to test external access
3. **SIP settings:**
   - SIP Server: `YOUR_PUBLIC_IP`
   - Port: `5060`
   - Username: `1001` (or your extension)
   - Password: `your_password`
   - Domain: `YOUR_PUBLIC_IP`

### **Step 15: Verify Registration**
```bash
# In Asterisk CLI
asterisk*CLI> pjsip show endpoints
asterisk*CLI> pjsip show registrations
asterisk*CLI> pjsip show contacts
```

## 🔧 **Phase 4: Troubleshooting**

### **Common Issues and Solutions**

#### **Issue: Can't register from external network**
```bash
# Check if ports are listening
sudo netstat -tlnp | grep :5060

# Check PJSIP status
asterisk*CLI> pjsip show transports

# Check firewall
sudo ufw status verbose
```

**Solutions:**
- Verify port forwarding rules are active
- Check if ISP blocks port 5060
- Ensure PJSIP is listening on all interfaces

#### **Issue: One-way audio**
**Solutions:**
- Verify RTP port range (10000-20000) is forwarded
- Check NAT settings in PJSIP configuration
- Ensure `direct_media=no` is set

#### **Issue: Registration fails**
**Solutions:**
- Verify public IP is correct in PJSIP config
- Check if ISP blocks port 5060
- Ensure port forwarding rules are active

#### **Issue: Intermittent connectivity**
**Solutions:**
- Check router's connection stability
- Verify server has stable network configuration
- Monitor Asterisk logs for errors

### **Debug Commands**
```bash
# Check if ports are listening
sudo netstat -tlnp | grep -E ':(5060|8088)'
sudo ss -tlnp | grep -E ':(5060|8088)'

# Check UFW status
sudo ufw status verbose

# Check Asterisk logs
sudo tail -f /var/log/asterisk/full | grep -i pjsip

# Test local connectivity
telnet localhost 5060
```

## ✅ **Verification Checklist**

- [ ] Port forwarding rules configured on router
- [ ] PJSIP global NAT settings updated
- [ ] PJSIP endpoints configured for external access
- [ ] Public IP address configured correctly
- [ ] Port 5060 accessible from external network
- [ ] SIP client can register using public IP
- [ ] Calls work in both directions
- [ ] Audio quality is acceptable
- [ ] Recording functionality works
- [ ] No firewall blocking issues

## 🎯 **Final Test**

1. **From external network** (mobile data), register SIP client
2. **Make a test call** to your local extensions
3. **Verify audio quality** and recording functionality
4. **Check Asterisk logs** for any errors
5. **Test call recording** from external client

## 🔒 **Security Considerations**

1. **Use strong passwords** for your SIP extensions
2. **Consider changing default port 5060** to avoid automated attacks
3. **Monitor access logs** regularly
4. **Consider VPN access** for additional security
5. **Regularly update** Asterisk and system packages

## 📚 **Additional Resources**

- [Asterisk PJSIP Documentation](https://wiki.asterisk.org/wiki/display/AST/PJSIP+Configuration)
- [PJSIP NAT Traversal Guide](https://wiki.asterisk.org/wiki/display/AST/PJSIP+NAT+Traversal)
- [Asterisk Security Best Practices](https://wiki.asterisk.org/wiki/display/AST/Security+Best+Practices)

---

## 🎉 **Success Indicators**

Once completed successfully, you should have:
- ✅ External SIP clients can register to your Asterisk server
- ✅ Calls work in both directions with good audio quality
- ✅ Call recording functionality works from external clients
- ✅ Stable connectivity from various external networks
- ✅ Proper NAT traversal for SIP and RTP traffic

**Your Asterisk server will now be accessible from anywhere on the internet!**
