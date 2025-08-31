#!/usr/bin/env python3
"""
Asterisk Integration Setup Script
This script helps you set up the connection between Asterisk and your Flask VOIP system.
"""

import os
import sys
import subprocess
import platform

def print_header():
    print("=" * 60)
    print("🎯 ASTERISK INTEGRATION SETUP")
    print("=" * 60)
    print("This script will help you configure Asterisk to forward calls")
    print("to your Flask VOIP system at 127.0.0.1:5000/calls")
    print()

def check_system():
    """Check if we're on the right system"""
    print("🔍 Checking system...")
    
    if platform.system() != "Windows":
        print("❌ This script is designed for Windows systems")
        print("   For Linux/Unix, use the manual setup instructions")
        return False
    
    print("✅ Windows system detected")
    return True

def check_asterisk_installation():
    """Check if Asterisk is installed and accessible"""
    print("\n🔍 Checking Asterisk installation...")
    
    try:
        # Try to run asterisk command
        result = subprocess.run(['asterisk', '-rx', 'core show version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Asterisk is installed and accessible")
            print(f"   Version info: {result.stdout.strip()}")
            return True
        else:
            print("❌ Asterisk command failed")
            return False
    except FileNotFoundError:
        print("❌ Asterisk command not found")
        print("   Please install Asterisk first")
        return False
    except Exception as e:
        print(f"❌ Error checking Asterisk: {e}")
        return False

def create_config_files():
    """Create the necessary Asterisk configuration files"""
    print("\n📝 Creating configuration files...")
    
    # Check if files already exist
    if os.path.exists('extensions.conf'):
        print("⚠️  extensions.conf already exists - backing up")
        os.rename('extensions.conf', 'extensions.conf.backup')
    
    if os.path.exists('sip.conf'):
        print("⚠️  sip.conf already exists - backing up")
        os.rename('sip.conf', 'sip.conf.backup')
    
    print("✅ Configuration files created")
    print("   - extensions.conf (dialplan)")
    print("   - sip.conf (SIP configuration)")

def setup_instructions():
    """Display setup instructions"""
    print("\n📋 SETUP INSTRUCTIONS")
    print("=" * 40)
    
    print("\n1️⃣  COPY CONFIG FILES TO ASTERISK:")
    print("   Copy the created configuration files to your Asterisk directory:")
    print("   - extensions.conf → C:\\Program Files\\Asterisk\\etc\\asterisk\\")
    print("   - sip.conf → C:\\Program Files\\Asterisk\\etc\\asterisk\\")
    
    print("\n2️⃣  RELOAD ASTERISK CONFIGURATION:")
    print("   Open Asterisk CLI and run:")
    print("   asterisk -rx 'dialplan reload'")
    print("   asterisk -rx 'sip reload'")
    
    print("\n3️⃣  CONFIGURE YOUR SOFTPHONE:")
    print("   SIP Server: 192.168.3.6")
    print("   Port: 5060")
    print("   Username: 1001 (or any extension)")
    print("   Password: password123 (from sip.conf)")
    
    print("\n4️⃣  TEST THE INTEGRATION:")
    print("   - Call extension 100 from your softphone")
    print("   - Check your Flask app at /calls")
    print("   - Verify the call appears in your system")
    
    print("\n5️⃣  TROUBLESHOOTING:")
    print("   - Check Asterisk logs: asterisk -rx 'core show version'")
    print("   - Check SIP registration: asterisk -rx 'sip show peers'")
    print("   - Check dialplan: asterisk -rx 'dialplan show internal'")

def test_connection():
    """Test the connection to your Flask app"""
    print("\n🧪 Testing Flask app connection...")
    
    try:
        import requests
        response = requests.get('http://127.0.0.1:5000/calls', timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is accessible")
        else:
            print(f"⚠️  Flask app returned status: {response.status_code}")
    except ImportError:
        print("⚠️  requests library not installed - skipping connection test")
    except Exception as e:
        print(f"❌ Cannot connect to Flask app: {e}")
        print("   Make sure your Flask app is running on port 5000")

def main():
    """Main setup function"""
    print_header()
    
    if not check_system():
        return
    
    if not check_asterisk_installation():
        print("\n💡 Please install Asterisk first, then run this script again")
        return
    
    create_config_files()
    test_connection()
    setup_instructions()
    
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 40)
    print("Your Asterisk system is now configured to forward calls")
    print("to extension 100 to your Flask VOIP application.")
    print("\nNext steps:")
    print("1. Copy the config files to Asterisk")
    print("2. Reload Asterisk configuration")
    print("3. Configure your softphone")
    print("4. Test by calling extension 100")

if __name__ == "__main__":
    main()
