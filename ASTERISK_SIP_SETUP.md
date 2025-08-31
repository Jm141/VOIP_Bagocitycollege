# 🎯 Asterisk & SIP Setup Guide for VOIP System

This guide will walk you through setting up **Asterisk PBX** and **SIP configuration** to integrate with your existing VOIP audio recording system.

## 📑 **Table of Contents**

- [📋 Prerequisites](#-prerequisites)
- [🖥️ VM-Specific Setup for Ubuntu Server](#️-vm-specific-setup-for-ubuntu-server)
- [🌐 Port Forwarding Setup Guide](#-port-forwarding-setup-guide)
- [🚀 Step 1: Install Asterisk](#️-step-1-install-asterisk)
- [⚙️ Step 2: Configure Asterisk](#️-step-2-configure-asterisk)
- [🔧 Step 3: Create Recording Directory](#️-step-3-create-recording-directory)
- [📱 Step 4: Configure SIP Clients](#️-step-4-configure-sip-clients)
- [🔄 Step 5: Reload Asterisk Configuration](#️-step-5-reload-asterisk-configuration)
- [🧪 Step 6: Test Your Setup](#️-step-6-test-your-setup)
- [🔗 Step 7: Integrate with Your VOIP System](#️-step-7-integrate-with-your-voip-system)
- [🌐 Step 8: Network Configuration](#️-step-8-network-configuration)
- [📊 Step 9: Monitoring & Logs](#️-step-9-monitoring--logs)
- [🚨 Troubleshooting](#️-troubleshooting)
- [📚 Additional Resources](#️-additional-resources)
- [✅ Verification Checklist](#️-verification-checklist)

## 📋 **Prerequisites**

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or Windows
- **Python**: 3.8+ (already installed for your VOIP system)
- **Network**: Static IP address or port forwarding capability
- **Hardware**: Microphone and speakers/headphones for testing

## 🖥️ **VM-Specific Setup for Ubuntu Server**

### **VM Requirements**
- **RAM**: Minimum 2GB, recommended 4GB+ for production
- **CPU**: 2+ cores with virtualization support enabled
- **Storage**: 20GB+ available space (SSD recommended)
- **Network**: Bridge mode or NAT with port forwarding

### **VM Network Configuration**
```bash
# Check network interface
ip addr show

# Configure static IP (if needed)
sudo nano /etc/netplan/01-netcfg.yaml
```

Example netplan configuration:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:  # Your VM network interface
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # Your desired IP
      gateway4: 192.168.1.1
      nameservers:
          addresses: [8.8.8.8, 8.8.4.4]
```

Apply changes:
```bash
sudo netplan apply
sudo systemctl restart systemd-networkd
```

### **VM Performance Optimization**
```bash
# Install VMware Tools (if using VMware)
sudo apt install open-vm-tools open-vm-tools-desktop

# Install VirtualBox Guest Additions (if using VirtualBox)
# Mount the Guest Additions ISO and run the installer

# Optimize for audio processing
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_ratio=15' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio=5' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### **VM Audio Configuration**
```bash
# Install audio dependencies
sudo apt install -y pulseaudio pulseaudio-utils

# Configure PulseAudio for VM
sudo nano /etc/pulse/default.pa
```

Add these lines to default.pa:
```bash
# Load audio drivers
load-module module-alsa-sink device=hw:0,0
load-module module-alsa-source device=hw:0,0
load-module module-null-sink sink_name=null
load-module module-null-source source_name=null
```

## 🌐 **Port Forwarding Setup Guide**

### **Why Port Forwarding is Essential**
Port forwarding allows external devices (like SIP phones from the internet) to reach your Asterisk server behind a router. Without it, only devices on your local network can connect.

### **Required Ports for Asterisk**
- **UDP 5060**: SIP signaling (call setup/teardown)
- **UDP 10000-20000**: RTP media (audio/video streams)
- **TCP 8088**: HTTP/ARI interface (optional, for management)

### **Step 1: Find Your Router's IP Address**
```bash
# On Windows
ipconfig

# On Linux/Mac
ip route show default

# Look for "Default Gateway" - this is your router's IP
# Usually 192.168.1.1, 192.168.0.1, or 10.0.0.1
```

### **Step 2: Access Your Router's Admin Panel**
1. Open a web browser
2. Navigate to your router's IP address (e.g., `http://192.168.1.1`)
3. Enter admin credentials (check router label or manual)
4. Look for "Port Forwarding", "Virtual Server", or "NAT" section

### **Step 3: Configure Port Forwarding by Router Type**

#### **📡 TP-Link Routers**
1. Go to **Advanced** → **NAT Forwarding** → **Virtual Servers**
2. Click **Add New**
3. Configure each port:

**SIP Signaling:**
- Service Port: `5060`
- Internal Port: `5060`
- IP Address: `192.168.1.100` (your VM's IP)
- Protocol: `UDP`
- Status: `Enabled`

**RTP Media Range:**
- Service Port: `10000-20000`
- Internal Port: `10000-20000`
- IP Address: `192.168.1.100`
- Protocol: `UDP`
- Status: `Enabled`

**HTTP Interface (Optional):**
- Service Port: `8088`
- Internal Port: `8088`
- IP Address: `192.168.1.100`
- Protocol: `TCP`
- Status: `Enabled`

#### **📡 Netgear Routers**
1. Go to **Advanced** → **Port Forwarding/Port Triggering**
2. Click **Add Custom Service**
3. Configure each port:

**SIP:**
- Service Name: `Asterisk SIP`
- Service Type: `UDP`
- External Starting Port: `5060`
- External Ending Port: `5060`
- Internal Starting Port: `5060`
- Internal Ending Port: `5060`
- Internal IP Address: `192.168.1.100`

**RTP:**
- Service Name: `Asterisk RTP`
- Service Type: `UDP`
- External Starting Port: `10000`
- External Ending Port: `20000`
- Internal Starting Port: `10000`
- Internal Ending Port: `20000`
- Internal IP Address: `192.168.1.100`

#### **📡 Asus Routers**
1. Go to **WAN** → **Virtual Server/Port Forwarding**
2. Click **Add Profile**
3. Configure each port:

**SIP:**
- Service Name: `Asterisk SIP`
- Port Range: `5060`
- Local IP: `192.168.1.100`
- Local Port: `5060`
- Protocol: `UDP`

**RTP:**
- Service Name: `Asterisk RTP`
- Port Range: `10000-20000`
- Local IP: `192.168.1.100`
- Local Port: `10000-20000`
- Protocol: `UDP`

#### **📡 Linksys Routers**
1. Go to **Security** → **Apps and Gaming** → **Single Port Forwarding**
2. Add each port:

**SIP:**
- Application: `Asterisk SIP`
- External Port: `5060`
- Internal Port: `5060`
- Protocol: `UDP`
- To IP Address: `192.168.1.100`

**RTP:**
- Application: `Asterisk RTP`
- External Port: `10000-20000`
- Internal Port: `10000-20000`
- Protocol: `UDP`
- To IP Address: `192.168.1.100`

#### **📡 Generic Router Instructions**
If your router isn't listed above:
1. Look for **Port Forwarding**, **Virtual Server**, **NAT**, or **Applications & Gaming**
2. Add rules for each port range
3. Ensure protocol matches (UDP for SIP/RTP, TCP for HTTP)
4. Set internal IP to your VM's IP address

### **Step 4: Configure Static IP for Your VM**
Port forwarding requires a static IP. Configure your VM to use a fixed IP address:

```bash
# Edit network configuration
sudo nano /etc/netplan/01-netcfg.yaml
```

Example configuration:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: no
      addresses:
        - 192.168.1.100/24  # Choose an IP outside DHCP range
      gateway4: 192.168.1.1
      nameservers:
          addresses: [8.8.8.8, 8.8.4.4]
```

Apply changes:
```bash
sudo netplan apply
sudo systemctl restart systemd-networkd
```

### **Step 5: Test Port Forwarding**

#### **Test from External Network**
1. Use your phone's mobile data (not WiFi)
2. Test SIP port: `telnet YOUR_PUBLIC_IP 5060`
3. Test RTP range: `telnet YOUR_PUBLIC_IP 10000`

#### **Test from Router's Network**
```bash
# From another device on your network
telnet 192.168.1.100 5060
telnet 192.168.1.100 8088
```

#### **Online Port Testing Tools**
- [CanYouSeeMe.org](https://canyouseeme.org/)
- [PortChecker.co](https://portchecker.co/)
- [YouGetSignal.com](https://www.yougetsignal.com/tools/open-ports/)

### **Step 6: Configure Asterisk for External Access**

#### **Update sip.conf for NAT**
```bash
sudo nano /etc/asterisk/sip.conf
```

Add these lines to the `[general]` section:
```ini
[general]
context=default
allowguest=no
allowoverlap=no
bindport=5060
bindaddr=0.0.0.0
srvlookup=yes
disallow=all
allow=ulaw
allow=alaw
allow=gsm
language=en

; NAT Configuration
nat=force_rport,comedia
localnet=192.168.1.0/255.255.255.0
externip=YOUR_PUBLIC_IP_ADDRESS
localip=192.168.1.100
```

#### **Update RTP Configuration**
```bash
sudo nano /etc/asterisk/rtp.conf
```

Create or update the file:
```ini
[general]
rtpstart=10000
rtpend=20000
rtpchecksums=no
```

### **Step 7: Firewall Configuration**

#### **VM Firewall (UFW)**
```bash
# Allow Asterisk ports
sudo ufw allow 5060/udp comment "Asterisk SIP"
sudo ufw allow 5060/tcp comment "Asterisk SIP TCP"
sudo ufw allow 10000:20000/udp comment "Asterisk RTP"
sudo ufw allow 8088/tcp comment "Asterisk HTTP"

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```

#### **Router Firewall**
- Ensure port forwarding rules are active
- Check if router has additional firewall settings
- Some routers require enabling "DMZ" mode for full access

### **Step 8: Test External Connectivity**

#### **Test SIP Registration from External Network**
1. Configure a SIP client (like Zoiper) on your phone
2. Use your public IP address as the SIP server
3. Try to register with extension credentials
4. Check Asterisk logs for registration attempts

#### **Test Call from External Network**
1. Make a call from external SIP client
2. Check if audio is working
3. Verify call recording is saved

### **Troubleshooting Port Forwarding**

#### **Common Issues and Solutions**

**Issue: Ports show as closed**
- Check if VM is running and accessible locally
- Verify router port forwarding rules are active
- Ensure VM firewall allows the ports
- Check if ISP blocks common ports

**Issue: SIP registration fails from external network**
- Verify external IP is correct in Asterisk config
- Check if router supports UDP port forwarding
- Ensure no conflicting services on same ports

**Issue: Audio works but one-way only**
- Check RTP port range forwarding
- Verify NAT settings in Asterisk
- Ensure both UDP and TCP 5060 are forwarded

**Issue: Intermittent connectivity**
- Check router's connection stability
- Verify VM has stable network configuration
- Monitor router logs for connection drops

#### **Debug Commands**
```bash
# Check if ports are listening
sudo netstat -tlnp | grep -E ':(5060|8088)'
sudo ss -tlnp | grep -E ':(5060|8088)'

# Check UFW status
sudo ufw status verbose

# Check Asterisk logs
sudo tail -f /var/log/asterisk/full | grep -i sip

# Test local connectivity
telnet localhost 5060
telnet localhost 8088
```

#### **Router-Specific Troubleshooting**

**TP-Link:**
- Check "Virtual Server" status is enabled
- Verify "Service Port" matches "Internal Port"
- Ensure "IP Address" is correct

**Netgear:**
- Check "Port Forwarding" is enabled
- Verify "External" and "Internal" ports match
- Ensure "Internal IP Address" is correct

**Asus:**
- Check "Virtual Server" is enabled
- Verify "Port Range" format is correct
- Ensure "Local IP" is correct

### **Advanced Port Forwarding Scenarios**

#### **Multiple Asterisk Servers**
If running multiple Asterisk instances:
- Use different external ports (5061, 5062, etc.)
- Forward to different internal IPs
- Configure unique RTP ranges for each

#### **Load Balancing**
For high-availability setups:
- Use router's load balancing features
- Forward ports to multiple internal servers
- Configure health checks

#### **Security Considerations**
- Only forward necessary ports
- Use strong passwords for SIP extensions
- Consider VPN for remote access
- Monitor access logs regularly

## 🚀 **Step 1: Install Asterisk**

### **Ubuntu/Debian Linux**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential wget libssl-dev libncurses5-dev libnewt-dev libxml2-dev linux-headers-$(uname -r) libsqlite3-dev uuid-dev libjansson-dev libcurl4-openssl-dev

# Download and install Asterisk
cd /usr/src/
sudo wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-18-current.tar.gz
sudo tar -xzf asterisk-18-current.tar.gz
cd asterisk-18.*/

# Configure and compile
sudo ./configure --with-jansson-bundled
sudo make menuselect
sudo make
sudo make install
sudo make samples
sudo make config

# Start Asterisk service
sudo systemctl enable asterisk
sudo systemctl start asterisk
```

### **Windows**
1. Download Asterisk for Windows from [Asterisk for Windows](https://www.asterisk.org/downloads/asterisk-for-windows/)
2. Run the installer as Administrator
3. Follow the installation wizard
4. Asterisk will be installed as a Windows service

## ⚙️ **Step 2: Configure Asterisk**

### **Access Asterisk CLI**
```bash
# Connect to Asterisk CLI
sudo asterisk -rvvv

# Or if running as service
sudo asterisk -r
```

### **Basic Configuration Files**

#### **1. sip.conf (SIP Configuration)**
```bash
sudo nano /etc/asterisk/sip.conf
```

Add this configuration:
```ini
[general]
context=default
allowguest=no
allowoverlap=no
bindport=5060
bindaddr=0.0.0.0
srvlookup=yes
disallow=all
allow=ulaw
allow=alaw
allow=gsm
language=en

; SIP User Extensions
[1001]
type=friend
secret=password123
host=dynamic
context=internal
disallow=all
allow=ulaw
allow=alaw
nat=force_rport,comedia
qualify=yes

[1002]
type=friend
secret=password456
host=dynamic
context=internal
disallow=all
allow=ulaw
allow=alaw
nat=force_rport,comedia
qualify=yes
```

#### **2. extensions.conf (Dialplan)**
```bash
sudo nano /etc/asterisk/extensions.conf
```

Add this configuration:
```ini
[general]
static=yes
writeprotect=no

[globals]
CONSOLE=Console/dsp
IAXINFO=guest

[default]
exten => s,1,NoOp(Default context)
exten => s,n,Hangup()

[internal]
exten => 1001,1,NoOp(Calling extension 1001)
exten => 1001,n,Dial(SIP/1001,20,tT)
exten => 1001,n,Hangup()

exten => 1002,1,NoOp(Calling extension 1002)
exten => 1002,n,Dial(SIP/1002,20,tT)
exten => 1002,n,Hangup()

; Call recording
exten => 1001,1,NoOp(Recording call for extension 1001)
exten => 1001,n,Set(RECORDING_FILE=/var/spool/asterisk/recordings/${UNIQUEID})
exten => 1001,n,MixMonitor(${RECORDING_FILE}.wav,b,1)
exten => 1001,n,Dial(SIP/1001,20,tT)
exten => 1001,n,Hangup()

exten => 1002,1,NoOp(Recording call for extension 1002)
exten => 1002,n,Set(RECORDING_FILE=/var/spool/asterisk/recordings/${UNIQUEID})
exten => 1002,n,MixMonitor(${RECORDING_FILE}.wav,b,1)
exten => 1002,n,Dial(SIP/1002,20,tT)
exten => 1002,n,Hangup()

; Test extension
exten => 9999,1,NoOp(Test recording)
exten => 9999,n,Answer()
exten => 9999,n,Wait(1)
exten => 9999,n,Playback(demo-abouttotry)
exten => 9999,n,Wait(1)
exten => 9999,n,Hangup()
```

#### **3. http.conf (HTTP Interface)**
```bash
sudo nano /etc/asterisk/http.conf
```

Add this configuration:
```ini
[general]
enabled=yes
bindaddr=0.0.0.0
bindport=8088
```

#### **4. ari.conf (ARI Configuration)**
```bash
sudo nano /etc/asterisk/ari.conf
```

Add this configuration:
```ini
[general]
enabled = yes
pretty = yes

[asterisk]
type = user
read_only = no
password = your_ari_password_here
```

## 🔧 **Step 3: Create Recording Directory**
```bash
# Create recordings directory
sudo mkdir -p /var/spool/asterisk/recordings
sudo chown -R asterisk:asterisk /var/spool/asterisk/recordings
sudo chmod 755 /var/spool/asterisk/recordings
```

## 📱 **Step 4: Configure SIP Clients**

### **Softphone Applications**
- **Zoiper** (Windows/Mac/Linux)
- **X-Lite** (Windows/Mac)
- **MicroSIP** (Windows)
- **Linphone** (Cross-platform)

### **SIP Client Configuration**
Use these settings in your softphone:
- **SIP Server**: Your Asterisk server IP
- **Port**: 5060
- **Username**: 1001 or 1002
- **Password**: password123 or password456
- **Domain**: Your server IP or domain

## 🔄 **Step 5: Reload Asterisk Configuration**
```bash
# In Asterisk CLI
asterisk*CLI> sip reload
asterisk*CLI> dialplan reload
asterisk*CLI> http reload
asterisk*CLI> ari reload
```

## 🧪 **Step 6: Test Your Setup**

### **1. Test SIP Registration**
```bash
# In Asterisk CLI
asterisk*CLI> sip show peers
```

You should see your extensions registered.

### **2. Test Call Recording**
```bash
# Make a test call to extension 9999
asterisk*CLI> console dial 9999
```

### **3. Check Recordings**
```bash
# List recordings
ls -la /var/spool/asterisk/recordings/
```

## 🔗 **Step 7: Integrate with Your VOIP System**

### **Modify Your Python Application**
Update your `app_direct_mysql.py` to include Asterisk integration:

```python
# Add to your imports
import requests
import json

# Asterisk ARI configuration
ASTERISK_ARI_URL = "http://localhost:8088"
ASTERISK_ARI_USER = "asterisk"
ASTERISK_ARI_PASSWORD = "your_ari_password_here"

def get_asterisk_recordings():
    """Fetch recordings from Asterisk"""
    try:
        response = requests.get(
            f"{ASTERISK_ARI_URL}/ari/recordings/stored",
            auth=(ASTERISK_ARI_USER, ASTERISK_ARI_PASSWORD)
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error fetching Asterisk recordings: {e}")
        return []

def download_asterisk_recording(recording_name):
    """Download a recording from Asterisk"""
    try:
        response = requests.get(
            f"{ASTERISK_ARI_URL}/ari/recordings/stored/{recording_name}/file",
            auth=(ASTERISK_ARI_USER, ASTERISK_ARI_PASSWORD)
        )
        if response.status_code == 200:
            # Save to your recordings directory
            with open(f"recordings/{recording_name}.wav", "wb") as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"Error downloading recording: {e}")
        return False
```

## 🌐 **Step 8: Network Configuration**

> **📖 For detailed port forwarding setup instructions, see the [Port Forwarding Setup Guide](#-port-forwarding-setup-guide) section above.**

### **Firewall Rules**
```bash
# Allow SIP traffic
sudo ufw allow 5060/udp
sudo ufw allow 5060/tcp

# Allow RTP media
sudo ufw allow 10000:20000/udp

# Allow HTTP interface
sudo ufw allow 8088/tcp
```

### **VM Network Configuration**

#### **1. VM Network Mode**
- **Bridge Mode**: VM gets IP from your router (recommended for production)
- **NAT Mode**: VM uses host's network with port forwarding (good for testing)
- **Host-Only**: VM only communicates with host

#### **2. VM Network Troubleshooting**
```bash
# Check VM network interface
ip addr show
ip route show

# Test external connectivity
ping 8.8.8.8
curl -I http://google.com

# Check if ports are accessible from host
# From host machine, test:
telnet YOUR_VM_IP 5060
telnet YOUR_VM_IP 8088
```

#### **3. VM Firewall Configuration**
```bash
# Install and configure UFW
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (if needed)
sudo ufw allow ssh

# Allow Asterisk ports
sudo ufw allow 5060/udp
sudo ufw allow 5060/tcp
sudo ufw allow 10000:20000/udp
sudo ufw allow 8088/tcp

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```

## 📊 **Step 9: Monitoring & Logs**

### **View Asterisk Logs**
```bash
# Real-time logs
sudo tail -f /var/log/asterisk/full

# SIP debug
sudo asterisk -rvvv
```

### **Check SIP Status**
```bash
# In Asterisk CLI
asterisk*CLI> sip show peers
asterisk*CLI> sip show registry
asterisk*CLI> core show calls
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. SIP Registration Fails**
- Check firewall settings
- Verify SIP credentials
- Check network connectivity

#### **2. No Audio**
- Verify RTP ports are open
- Check NAT settings
- Ensure codec compatibility

#### **3. Recording Issues**
- Check directory permissions
- Verify disk space
- Check MixMonitor configuration

### **VM-Specific Issues**

#### **1. VM Audio Problems**
```bash
# Check if audio devices are detected
ls -la /dev/snd/
aplay -l
arecord -l

# If no audio devices, install dummy audio
sudo modprobe snd-dummy
echo 'snd-dummy' | sudo tee -a /etc/modules

# Test audio
speaker-test -t wav -c 2
```

#### **2. VM Network Issues**
```bash
# Check VM network interface
ip addr show
ip route show

# Test connectivity
ping 8.8.8.8
nslookup google.com

# Check if ports are listening
sudo netstat -tlnp | grep :5060
sudo netstat -tlnp | grep :8088
```

#### **3. VM Performance Issues**
```bash
# Monitor system resources
htop
iotop
nethogs

# Check Asterisk logs for errors
sudo tail -f /var/log/asterisk/full | grep -i error
```

### **Debug Commands**
```bash
# Enable SIP debugging
asterisk*CLI> sip set debug on

# Enable RTP debugging
asterisk*CLI> rtp set debug on

# Check channel status
asterisk*CLI> channel show
```

## 📚 **Additional Resources**

- [Asterisk Documentation](https://wiki.asterisk.org/)
- [SIP Protocol RFC](https://tools.ietf.org/html/rfc3261)
- [Asterisk ARI Documentation](https://wiki.asterisk.org/wiki/display/AST/Asterisk+12+ARI)

## ✅ **Verification Checklist**

- [ ] Asterisk installed and running
- [ ] SIP extensions configured
- [ ] Dialplan configured
- [ ] Recording directory created
- [ ] Firewall ports opened
- [ ] SIP client registered
- [ ] Test call successful
- [ ] Recording saved
- [ ] Integration with VOIP system working

## 🖥️ **VM-Specific Verification Checklist**

- [ ] VM has sufficient resources (RAM, CPU, Storage)
- [ ] VM network interface configured correctly
- [ ] VM can reach external internet
- [ ] Host can reach VM on required ports
- [ ] VM audio devices detected and working
- [ ] VM firewall configured and enabled
- [ ] VM performance monitoring tools installed
- [ ] VM backup strategy implemented
- [ ] VM snapshots created before major changes

### **Quick VM Health Check**
```bash
# Check system resources
free -h
nproc
df -h

# Check network
ip addr show
ping -c 3 8.8.8.8

# Check services
sudo systemctl status asterisk
sudo systemctl status ufw

# Check ports
sudo netstat -tlnp | grep -E ':(5060|8088)'
```

## 🔧 **Quick Port Forwarding Reference**

### **Essential Ports**
| Port | Protocol | Purpose | Required |
|------|----------|---------|----------|
| 5060 | UDP | SIP signaling | ✅ Yes |
| 5060 | TCP | SIP signaling (fallback) | ✅ Yes |
| 10000-20000 | UDP | RTP media streams | ✅ Yes |
| 8088 | TCP | HTTP/ARI interface | ❌ Optional |

### **Router Quick Setup**
1. **Access router**: Navigate to `http://192.168.1.1` (or your router's IP)
2. **Find port forwarding**: Look for "Port Forwarding", "Virtual Server", or "NAT"
3. **Add rules**: Forward each port range to your VM's IP address
4. **Test**: Use online port checkers to verify

### **Common Router Locations**
- **TP-Link**: Advanced → NAT Forwarding → Virtual Servers
- **Netgear**: Advanced → Port Forwarding/Port Triggering
- **Asus**: WAN → Virtual Server/Port Forwarding
- **Linksys**: Security → Apps and Gaming → Single Port Forwarding

## 🎉 **Next Steps**

Once Asterisk and SIP are working:
1. **Scale up**: Add more extensions
2. **Advanced features**: IVR, voicemail, call queues
3. **Security**: Implement TLS/SRTP
4. **Monitoring**: Set up call analytics
5. **Backup**: Configure automated backups

---

*This setup will give you a professional-grade VOIP system with Asterisk PBX and SIP capabilities, integrated with y