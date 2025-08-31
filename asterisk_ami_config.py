# Asterisk Manager Interface (AMI) Configuration
# Update these settings to match your Asterisk server configuration

# AMI Connection Settings
AMI_HOST = '192.168.3.6'  # Your Asterisk server IP address
AMI_PORT = 5038          # Default AMI port
AMI_USERNAME = 'admin'   # AMI username from manager.conf
AMI_SECRET = 'jm1412'     # AMI secret from manager.conf

# Flask Application Settings
FLASK_HOST = '172.29.192.1'  # Your Flask PC's IP address
FLASK_PORT = 5000         # Flask port

# Extension Settings
DEFAULT_EXTENSION = '1412'  # Extension to handle

# Database Settings (if needed for call logging)
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'voip_system'

# Logging Settings
LOG_LEVEL = 'INFO'
LOG_FILE = 'asterisk_ami.log'

# Call Handling Settings
CALL_TIMEOUT = 30000      # 30 seconds
MAX_CALL_DURATION = 3600  # 1 hour
