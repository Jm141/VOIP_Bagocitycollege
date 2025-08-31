from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os
import json
import logging
from datetime import datetime, timedelta
import threading
import time
import base64
from io import BytesIO
import subprocess
import uuid

# Try to import audio libraries, but make them optional
try:
    import wave
    import pyaudio
    import numpy as np
    AUDIO_AVAILABLE = True
    
    # Audio recording settings
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("Audio libraries not available. Voice recording will be disabled.")
    
    # Default audio settings (won't be used)
    CHUNK = 1024
    FORMAT = None
    CHANNELS = 1
    RATE = 44100

# Asterisk Manager Interface (AMI) integration
class AsteriskAMI:
    def __init__(self, host='127.0.0.1', port=5038, username='admin', secret='admin'):
        self.host = host
        self.port = port
        self.username = username
        self.secret = secret
        self.connected = False
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Connect to Asterisk AMI"""
        try:
            import socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Login to AMI
            login_msg = f"Action: Login\r\nUsername: {self.username}\r\nSecret: {self.secret}\r\n\r\n"
            self.socket.send(login_msg.encode())
            
            response = self.socket.recv(1024).decode()
            if "Success" in response:
                self.connected = True
                self.logger.info("Connected to Asterisk AMI")
                return True
            else:
                self.logger.error(f"AMI login failed: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to AMI: {e}")
            return False
    
    def send_action(self, action, params=None):
        """Send an action to Asterisk AMI"""
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            if params is None:
                params = {}
            
            message = f"Action: {action}\r\n"
            for key, value in params.items():
                message += f"{key}: {value}\r\n"
            message += "\r\n"
            
            self.socket.send(message.encode())
            response = self.socket.recv(1024).decode()
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to send AMI action {action}: {e}")
            self.connected = False
            return None
    
    def originate_call(self, context, extension, caller_id, priority=1, timeout=30000):
        """Originate a call using AMI"""
        params = {
            'Context': context,
            'Extension': extension,
            'Callerid': caller_id,
            'Priority': priority,
            'Timeout': timeout
        }
        return self.send_action('Originate', params)
    
    def get_channel_status(self, channel):
        """Get status of a specific channel"""
        return self.send_action('GetVar', {'Channel': channel, 'Variable': 'CHANNEL'})
    
    def hangup_channel(self, channel, cause=16):
        """Hangup a specific channel"""
        return self.send_action('Hangup', {'Channel': channel, 'Cause': str(cause)})
    
    def close(self):
        """Close AMI connection"""
        if self.connected:
            try:
                self.send_action('Logoff')
                self.socket.close()
                self.connected = False
                self.logger.info("AMI connection closed")
            except:
                pass

# Asterisk Gateway Interface (AGI) Server
class AGIServer:
    def __init__(self, host='0.0.0.0', port=5001, logger=None, socketio_instance=None):
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger(__name__)
        self.socketio_instance = socketio_instance
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the AGI server"""
        try:
            import socket
            self.logger.info(f"Creating socket for AGI server on {self.host}:{self.port}")
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            self.logger.info("Binding socket to address...")
            self.server_socket.bind((self.host, self.port))
            
            self.logger.info("Setting socket to listen mode...")
            self.server_socket.listen(5)
            
            self.running = True
            self.logger.info(f"AGI Server started on {self.host}:{self.port}")
            
            # Start server in a separate thread
            import threading
            self.logger.info("Starting AGI server thread...")
            server_thread = threading.Thread(target=self._accept_connections, daemon=True, name="AGI-Server-Thread")
            server_thread.start()
            self.logger.info(f"AGI server thread started successfully: {server_thread.name} (daemon: {server_thread.daemon})")
            self.logger.info(f"Thread alive: {server_thread.is_alive()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start AGI server: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def stop(self):
        """Stop the AGI server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.logger.info("AGI Server stopped")
    
    def _accept_connections(self):
        """Accept incoming AGI connections"""
        import threading
        import socket
        current_thread = threading.current_thread()
        self.logger.info(f"AGI server thread started: {current_thread.name} (daemon: {current_thread.daemon})")
        self.logger.info("Waiting for connections...")
        
        while self.running:
            try:
                self.logger.info("Calling accept() on server socket...")
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"AGI connection accepted from {address}")
                
                # Handle each connection in a separate thread
                self.logger.info(f"Creating client thread for {address}")
                client_thread = threading.Thread(
                    target=self._handle_agi_connection, 
                    args=(client_socket, address),
                    daemon=True,
                    name=f"AGI-Client-{address[0]}-{address[1]}"
                )
                client_thread.start()
                self.logger.info(f"Client thread started for {address}: {client_thread.name}")
                self.logger.info(f"Client thread alive: {client_thread.is_alive()}")
                
                # Wait a moment to see if the thread starts processing
                time.sleep(0.1)
                self.logger.info(f"Client thread still alive after delay: {client_thread.is_alive()}")
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting AGI connection: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                else:
                    self.logger.info("AGI server stopped, exiting accept loop")
                    break
    
    def _handle_agi_connection(self, client_socket, address):
        """Handle individual AGI connection"""
        try:
            self.logger.info(f"Starting to handle AGI connection from {address}")
            
            # Read AGI environment variables
            agi_vars = {}
            self.logger.info("Reading AGI environment variables...")
            
            # Read data line by line until empty line
            buffer = ""
            while True:
                try:
                    # Read one character at a time to build lines
                    char = client_socket.recv(1).decode('utf-8')
                    if not char:
                        break
                    
                    buffer += char
                    
                    # Check if we have a complete line
                    if char == '\n':
                        line = buffer.strip()
                        buffer = ""
                        
                        self.logger.info(f"Received line: '{line}'")
                        
                        if not line:  # Empty line marks end of environment variables
                            self.logger.info("Empty line found, end of environment variables")
                            break
                        
                        if ':' in line:
                            key, value = line.split(':', 1)
                            agi_vars[key.strip()] = value.strip()
                            self.logger.info(f"Parsed AGI variable: {key.strip()} = {value.strip()}")
                        
                except Exception as e:
                    self.logger.error(f"Error reading AGI data: {e}")
                    break
            
            self.logger.info(f"AGI variables: {agi_vars}")
            
            # Process the AGI request
            self.logger.info("Processing AGI request...")
            response = self._process_agi_request(agi_vars)
            
            # Send response back to Asterisk
            self.logger.info(f"Sending response to Asterisk: {response}")
            client_socket.send(response.encode())
            
        except Exception as e:
            self.logger.error(f"Error handling AGI connection: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            self.logger.info("Closing AGI connection")
            client_socket.close()
    
    def _process_agi_request(self, agi_vars):
        """Process AGI request and return response"""
        try:
            # Extract call information
            caller_id = agi_vars.get('agi_callerid', 'Unknown')
            extension = agi_vars.get('agi_extension', '1412')
            unique_id = agi_vars.get('agi_uniqueid', str(uuid.uuid4()))
            channel = agi_vars.get('agi_channel', '')
            
            # Log the call
            self.logger.info(f"AGI call received - Caller: {caller_id}, Extension: {extension}, Channel: {channel}")
            self.logger.info(f"AGI variables received: {agi_vars}")
            
            # Store call in database
            self.logger.info(f"Storing call {unique_id} in database...")
            self._store_call_in_db(caller_id, extension, unique_id, channel)
            
            # Emit Socket.IO event for real-time notification
            self.logger.info(f"Notifying Flask app about call {unique_id}...")
            self._notify_flask_app(caller_id, extension, unique_id, channel)
            
            # Return success response to Asterisk
            return "200 result=0\n"
            
        except Exception as e:
            self.logger.error(f"Error processing AGI request: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return "200 result=-1\n"
    
    def _store_call_in_db(self, caller_id, extension, unique_id, channel):
        """Store call information in database"""
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time, sip_channel, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    unique_id, 
                    caller_id, 
                    f'Caller {caller_id}', 
                    'ringing', 
                    'inbound', 
                    datetime.now(),
                    channel,
                    datetime.now()
                ))
                connection.commit()
                self.logger.info(f"Call {unique_id} stored in database")
                
                # Add to active calls for real-time management
                active_calls[unique_id] = {
                    'id': unique_id,
                    'call_id': unique_id,
                    'caller_id': caller_id,
                    'caller_name': f'Caller {caller_id}',
                    'caller_number': caller_id,
                    'status': 'ringing',
                    'direction': 'inbound',
                    'start_time': datetime.now().isoformat(),
                    'sip_channel': channel,
                    'created_at': datetime.now().isoformat(),
                    'source': 'ami'  # Mark as AMI call
                }
                
                self.logger.info(f"Call {unique_id} added to active_calls: {active_calls[unique_id]}")
                self.logger.info(f"Total active calls: {len(active_calls)}")
                
        except Exception as e:
            self.logger.error(f"Error storing call in database: {e}")
        finally:
            if connection:
                connection.close()
    
    def _notify_flask_app(self, caller_id, extension, unique_id, channel):
        """Notify Flask app about incoming call via Socket.IO"""
        try:
            if self.socketio_instance:
                # Emit Socket.IO event for real-time notification
                self.socketio_instance.emit('incoming_call_1412', {
                    'caller_id': caller_id,
                    'extension': extension,
                    'call_id': unique_id,
                    'channel': channel,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Also emit general call events for the calls page
                call_data = {
                    'call_id': unique_id,
                    'caller_id': caller_id,
                    'caller_name': f'Caller {caller_id}',
                    'status': 'ringing',
                    'direction': 'inbound',
                    'start_time': datetime.now().isoformat(),
                    'sip_channel': channel,
                    'created_at': datetime.now().isoformat(),
                    'source': 'ami'
                }
                
                # Emit new call event for calls page
                self.logger.info(f"Emitting 'new_call' event for call {unique_id}")
                self.socketio_instance.emit('new_call', call_data)
                
                # Emit call update event
                self.logger.info(f"Emitting 'call_update' event for call {unique_id}")
                self.socketio_instance.emit('call_update', call_data)
                
                self.logger.info(f"Socket.IO events emitted for AMI call {unique_id}")
            else:
                self.logger.warning("SocketIO instance not available, cannot emit notification")
        except Exception as e:
            self.logger.error(f"Error notifying Flask app: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")


# Initialize AMI connection
try:
    from asterisk_ami_config import AMI_HOST, AMI_PORT, AMI_USERNAME, AMI_SECRET
    ami = AsteriskAMI(
        host=AMI_HOST,
        port=AMI_PORT,
        username=AMI_USERNAME,
        secret=AMI_SECRET
    )
    print(f"AMI configured to connect to {AMI_HOST}:{AMI_PORT}")
except ImportError:
    print("Warning: asterisk_ami_config.py not found. Using default AMI settings.")
    ami = AsteriskAMI(
        host='192.168.1.100',  # Change to your Asterisk server IP
        port=5038,
        username='admin',       # Change to your AMI username
        secret='jm1412'    # Change to your AMI secret
    )

# Simple mock SIP service (replaces the deleted real_sip_integration.py)
class MockSIPService:
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
    
    def initialize(self):
        """Initialize the mock SIP service"""
        self.is_initialized = True
        self.logger.info("Mock SIP service initialized")
    
    def make_call(self, from_number, to_number):
        """Mock making a call"""
        call_id = f"mock_{int(time.time())}"
        self.logger.info(f"Mock call made: {from_number} -> {to_number} (ID: {call_id})")
        return call_id
    
    def answer_call(self, call_id):
        """Mock answering a call"""
        self.logger.info(f"Mock call answered: {call_id}")
        return True
    
    def hangup_call(self, call_id):
        """Mock hanging up a call"""
        self.logger.info(f"Mock call hung up: {call_id}")
        return True
    
    def reject_call(self, call_id, reason='user_rejected'):
        """Mock rejecting a call"""
        self.logger.info(f"Mock call rejected: {call_id} (reason: {reason})")
        return True
    
    def transfer_call(self, call_id, to_number):
        """Mock transferring a call"""
        self.logger.info(f"Mock call transferred: {call_id} -> {to_number}")
        return True
    
    def get_system_status(self):
        """Get mock system status"""
        return {
            'status': 'mock_initialized',
            'version': '1.0.0',
            'uptime': 'mock_uptime'
        }
    
    def simulate_incoming_call(self):
        """Mock simulating an incoming call"""
        self.logger.info("Mock incoming call simulation triggered")
        return True

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1412',
    'database': 'resource_allocation',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Database helper functions
def get_db_connection():
    """Get database connection"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_database():
    """Initialize database tables"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Skip users table creation - it already exists in resource_allocation database
            
            # Create calls table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    call_id VARCHAR(50) UNIQUE NOT NULL,
                    caller_id VARCHAR(20) NOT NULL,
                    caller_name VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'ringing',
                    direction VARCHAR(20) DEFAULT 'inbound',
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_time DATETIME,
                    duration INT,
                    user_id INT,
                    sip_channel VARCHAR(100),
                    recording_path VARCHAR(255),
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Add recording_path column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE calls ADD COLUMN recording_path VARCHAR(255)")
                logger.info("Added recording_path column to calls table")
            except Exception as e:
                # Column might already exist
                logger.debug(f"recording_path column check: {e}")
            
            # Create forwarding_rules table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forwarding_rules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    pattern VARCHAR(50) NOT NULL,
                    priority INT DEFAULT 100,
                    enabled BOOLEAN DEFAULT TRUE,
                    forward_to VARCHAR(20) DEFAULT 'mobile_app',
                    forward_to_users TEXT,
                    schedule_enabled BOOLEAN DEFAULT FALSE,
                    schedule_start TIME,
                    schedule_end TIME,
                    schedule_days TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create incidents table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    incident_id VARCHAR(20) UNIQUE NOT NULL,
                    category_id INT NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    location_name VARCHAR(255) NOT NULL,
                    latitude DECIMAL(10,8) NOT NULL,
                    longitude DECIMAL(11,8) NOT NULL,
                    reported_by INT,
                    status ENUM('reported','assigned','in_progress','resolved','closed') DEFAULT 'reported',
                    priority ENUM('low','medium','high','critical') DEFAULT 'medium',
                    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (reported_by) REFERENCES users(id)
                )
            """)
            
            # Create incident_categories table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incident_categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    priority_level ENUM('low','medium','high','critical') DEFAULT 'medium',
                    response_time_minutes INT DEFAULT 60,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            connection.commit()
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        if connection:
            connection.close()

def init_default_data():
    """Initialize default users and rules"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Skip admin user creation - it already exists in resource_allocation database
            
            # Check if default forwarding rule exists
            cursor.execute("SELECT id FROM forwarding_rules WHERE name = 'Default Forwarding'")
            default_rule = cursor.fetchone()
            
            if not default_rule:
                # Create default forwarding rule
                cursor.execute("""
                    INSERT INTO forwarding_rules (name, pattern, priority, enabled, forward_to, forward_to_users, schedule_enabled, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'Default Forwarding',
                    '*',
                    100,
                    True,
                    'mobile_app',
                    '[]',
                    False,
                    datetime.now()
                ))
                logger.info("Default forwarding rule created")
            
            # Check if incident categories exist
            cursor.execute("SELECT COUNT(*) as count FROM incident_categories")
            categories_count = cursor.fetchone()['count']
            
            if categories_count == 0:
                # Insert default incident categories
                categories = [
                    ('Medical Emergency', 'Health-related incidents requiring immediate medical attention', 'critical', 5),
                    ('Fire Emergency', 'Fire-related incidents and emergencies', 'critical', 5),
                    ('Traffic Accident', 'Road traffic accidents and incidents', 'high', 15),
                    ('Natural Disaster', 'Natural disasters and weather-related emergencies', 'critical', 10),
                    ('Public Safety', 'General public safety concerns and incidents', 'high', 20),
                    ('VOIP System Issue', 'Technical problems with the VOIP system', 'medium', 30),
                    ('Network Problem', 'Network connectivity and infrastructure issues', 'medium', 45),
                    ('Other', 'Other types of incidents not covered by specific categories', 'low', 60)
                ]
                
                for name, description, priority_level, response_time in categories:
                    cursor.execute("""
                        INSERT INTO incident_categories (name, description, priority_level, response_time_minutes)
                        VALUES (%s, %s, %s, %s)
                    """, (name, description, priority_level, response_time))
                
                logger.info("Default incident categories created")
            
            connection.commit()
            logger.info("Default data initialized successfully")
            
    except Exception as e:
        logger.error(f"Default data initialization error: {e}")
        raise
    finally:
        if connection:
            connection.close()

# Global variables for call management
active_calls = {}
call_queue = []
connected_users = {}
call_recordings = {}  # Store call recordings
audio_streams = {}    # Store real-time audio streams for two-way communication

@login_manager.user_loader
def load_user(user_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return SimpleUser(user_data)
    except Exception as e:
        logger.error(f"Error loading user: {e}")
    finally:
        if connection:
            connection.close()
    return None

# Simple user class for Flask-Login
class SimpleUser:
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.role = user_data['role']
        self.first_name = user_data['first_name']
        self.last_name = user_data['last_name']
        self.phone = user_data.get('phone', '')  # Optional field
        self.is_active = user_data.get('is_active', True)
        self.created_at = user_data.get('created_at')
        self.updated_at = user_data.get('updated_at')
        self.is_authenticated = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

# Initialize SIP service
sip_service = MockSIPService(socketio)

# Routes
@app.route('/')
def index():
    """Main index page - redirect to dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get total users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
            
            # Get active users (users who have been updated recently)
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE updated_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)")
            online_users = cursor.fetchone()['count']
            
            # Get total calls today
            cursor.execute("SELECT COUNT(*) as count FROM calls WHERE DATE(start_time) = CURDATE()")
            total_calls_today = cursor.fetchone()['count']
            
            # Get total calls
            cursor.execute("SELECT COUNT(*) as count FROM calls")
            total_calls = cursor.fetchone()['count']
            
            # Get total recordings
            cursor.execute("SELECT COUNT(*) as count FROM calls WHERE recording_path IS NOT NULL")
            total_recordings = cursor.fetchone()['count']
            
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        total_users = 0
        online_users = 0
        total_calls_today = 0
        total_calls = 0
        total_recordings = 0
    finally:
        if connection:
            connection.close()
    
    stats = {
        'active_calls': len(active_calls),
        'total_users': total_users,
        'online_users': online_users,
        'total_calls_today': total_calls_today,
        'total_calls': total_calls,
        'total_recordings': total_recordings
    }
    return render_template('dashboard.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                
                if user_data and check_password_hash(user_data['password_hash'], password):
                    user = SimpleUser(user_data)
                    login_user(user)
                    
                    # Update user last seen timestamp
                    cursor.execute("UPDATE users SET updated_at = %s WHERE id = %s", 
                                 (datetime.now(), user.id))
                    connection.commit()
                    
                    return redirect(url_for('dashboard'))
                    
        except Exception as e:
            logger.error(f"Login error: {e}")
        finally:
            if connection:
                connection.close()
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    if current_user.is_authenticated:
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET updated_at = %s WHERE id = %s", (datetime.now(), current_user.id))
                connection.commit()
        except Exception as e:
            logger.error(f"Logout error: {e}")
        finally:
            if connection:
                connection.close()
        
        logout_user()
    return redirect(url_for('login'))

@app.route('/calls')
@login_required
def calls():
    """Calls management page"""
    return render_template('calls.html')

@app.route('/forwarding-rules')
@login_required
def forwarding_rules():
    """Forwarding rules management page"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM forwarding_rules ORDER BY priority DESC")
            rules = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error loading forwarding rules: {e}")
        rules = []
    finally:
        if connection:
            connection.close()
    
    return render_template('forwarding_rules.html', rules=rules)

@app.route('/users')
@login_required
def users():
    """Users management page"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        users = []
    finally:
        if connection:
            connection.close()
    
    return render_template('users.html', users=users)

@app.route('/phone')
def phone():
    """Phone simulator page"""
    return render_template('phone.html')

@app.route('/test-recorder')
def test_recorder():
    """Recorder.js test page"""
    return render_template('test_recorder.html')

@app.route('/test-phone-simulator')
def test_phone_simulator():
    """Serve the phone simulator test page"""
    return send_from_directory('.', 'test_phone_simulator.html')

@app.route('/test-browser-compatibility')
def test_browser_compatibility():
    """Serve the browser compatibility test page"""
    return send_from_directory('.', 'test_browser_compatibility.html')

@app.route('/test-mediarecorder')
def test_mediarecorder():
    """Serve the MediaRecorder API test page"""
    return send_from_directory('.', 'test_mediarecorder.html')

# API Routes
@app.route('/api/calls', methods=['GET'])
@login_required
def get_calls():
    """Get all calls (active and historical)"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get all calls from database
            cursor.execute("""
                SELECT call_id, caller_id, caller_name, status, direction,
                       start_time, end_time, duration, recording_path,
                       CASE
                           WHEN status = 'ringing' THEN 'incoming'
                           WHEN status = 'answered' THEN 'active'
                           WHEN status IN ('ended', 'rejected', 'missed') THEN 'ended'
                           ELSE status
                       END as display_status
                FROM calls
                ORDER BY start_time DESC
            """)
            db_calls = cursor.fetchall()

            # Combine database calls with active calls
            all_calls = []

            for db_call in db_calls:
                all_calls.append({
                    'id': db_call['call_id'],
                    'call_id': db_call['call_id'],
                    'caller_id': db_call['caller_id'],
                    'caller_name': db_call['caller_name'],
                    'caller_number': db_call['caller_id'],
                    'status': db_call['status'],
                    'display_status': db_call['display_status'],
                    'direction': db_call['direction'],
                    'start_time': db_call['start_time'],
                    'end_time': db_call['end_time'],
                    'duration': db_call['duration'] or 0,
                    'recording_path': db_call['recording_path'],
                    'is_recording': False,
                    'created_at': db_call['start_time']
                })

            # Sort by creation time (newest first)
            all_calls.sort(key=lambda x: x['created_at'], reverse=True)

            return jsonify({
                'success': True,
                'calls': all_calls,
                'count': len(all_calls)
            })

    except Exception as e:
        logger.error(f"Error getting calls: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'calls': [],
            'count': 0
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/calls/public', methods=['GET'])
def get_calls_public():
    """Get all calls (public endpoint for calls page)"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get all calls from database
            cursor.execute("""
                SELECT call_id, caller_id, caller_name, status, direction, 
                       start_time, end_time, duration, recording_path,
                       CASE 
                           WHEN status = 'ringing' THEN 'incoming'
                           WHEN status = 'answered' THEN 'active'
                           WHEN status IN ('ended', 'rejected', 'missed') THEN 'ended'
                           ELSE status
                       END as display_status
                FROM calls 
                ORDER BY start_time DESC
            """)
            db_calls = cursor.fetchall()
            
            # Combine database calls with active calls
            all_calls = []
            
            # Add active calls first
            for call_id, call_data in active_calls.items():
                # Ensure start_time is a string for consistent handling
                start_time = call_data.get('start_time')
                if isinstance(start_time, datetime):
                    start_time = start_time.isoformat()
                elif not start_time:
                    start_time = datetime.now().isoformat()
                
                all_calls.append({
                    'id': call_data['call_id'],
                    'call_id': call_data['call_id'],
                    'caller_id': call_data['caller_id'],
                    'caller_name': call_data['caller_name'],
                    'caller_number': call_data['caller_id'],
                    'status': call_data['status'],
                    'display_status': 'incoming' if call_data['status'] == 'ringing' else 'active',
                    'direction': call_data['direction'],
                    'start_time': start_time,
                    'end_time': call_data.get('end_time'),
                    'duration': call_data.get('duration', 0),
                    'recording_path': call_data.get('recording_path'),
                    'is_recording': call_id in call_recordings and call_recordings[call_id]['is_recording'],
                    'created_at': start_time,
                    'source': call_data.get('source', 'phone_simulator'),  # Include source field
                    'sip_channel': call_data.get('sip_channel')  # Include SIP channel for AMI calls
                })
            
            # Add database calls that aren't in active calls
            for db_call in db_calls:
                if db_call['call_id'] not in active_calls:
                    # Ensure start_time is a string
                    start_time = db_call['start_time']
                    if isinstance(start_time, datetime):
                        start_time = start_time.isoformat()
                    elif not start_time:
                        start_time = datetime.now().isoformat()
                    
                    all_calls.append({
                        'id': db_call['call_id'],
                        'call_id': db_call['call_id'],
                        'caller_id': db_call['caller_id'],
                        'caller_name': db_call['caller_name'],
                        'caller_number': db_call['caller_id'],
                        'status': db_call['status'],
                        'display_status': db_call['display_status'],
                        'direction': db_call['direction'],
                        'start_time': start_time,
                        'end_time': db_call['end_time'],
                        'duration': db_call['duration'] or 0,
                        'recording_path': db_call['recording_path'],
                        'is_recording': False,
                        'created_at': start_time,
                        'source': 'phone_simulator',  # Default source for database calls
                        'sip_channel': None  # No SIP channel for database calls
                    })
            
            # Sort by creation time (newest first) - handle string dates properly
            all_calls.sort(key=lambda x: x['created_at'] if x['created_at'] else '', reverse=True)
            
            return jsonify({
                'success': True,
                'calls': all_calls,
                'count': len(all_calls)
            })
            
    except Exception as e:
        logger.error(f"Error getting calls: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'calls': [],
            'count': 0
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/calls/make', methods=['POST'])
@login_required
def make_call():
    """Make outbound call"""
    try:
        data = request.get_json()
        from_number = data.get('from_number')
        to_number = data.get('to_number')
        
        if not from_number or not to_number:
            return jsonify({'error': 'Missing from_number or to_number'}), 400
        
        call_id = sip_service.make_call(from_number, to_number)
        
        return jsonify({
            'success': True,
            'call_id': call_id,
            'message': 'Call initiated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error making call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/answer', methods=['POST'])
@login_required
def answer_call(call_id):
    """Answer incoming call and automatically start recording"""
    try:
        logger.info(f"Answering call {call_id}")
        
        # Check if call exists in active calls
        if call_id in active_calls:
            # Update call status
            active_calls[call_id]['status'] = 'answered'
            active_calls[call_id]['start_time'] = datetime.now().isoformat()
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'answered', start_time = %s 
                    WHERE call_id = %s
                """, (datetime.now(), call_id))
                connection.commit()
            
            # Automatically start recording when call is answered
            if AUDIO_AVAILABLE:
                try:
                    # Create recordings directory if it doesn't exist
                    os.makedirs("recordings", exist_ok=True)
                    
                    # Initialize recording for this call
                    call_recordings[call_id] = {
                        'audio_frames': [],
                        'is_recording': True,
                        'start_time': datetime.now(),
                        'audio_data': [],
                        'recording_file': f"recordings/call_{call_id}.wav"
                    }
                    
                    # Update call status to show recording is active
                    active_calls[call_id]['recording'] = True
                    active_calls[call_id]['recording_started'] = datetime.now().isoformat()
                    
                    logger.info(f"Call answered and recording automatically started for call {call_id}")
                    
                    # Emit WebSocket update to notify phone simulator that call is answered
                    socketio.emit('call_answered', {
                        'call_id': call_id,
                        'status': 'answered',
                        'recording_started': True
                    }, room=f'call_{call_id}')
                    
                except Exception as recording_error:
                    logger.error(f"Error starting automatic recording: {recording_error}")
            else:
                logger.warning(f"Audio recording not available - call answered without recording for {call_id}")
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            socketio.emit('call_status_update', {
                'call_id': call_id,
                'status': 'answered',
                'timestamp': datetime.now().isoformat()
            }, room='general')
            
            logger.info(f"Call {call_id} answered successfully")
            
            return jsonify({
                'success': True, 
                'message': 'Call answered and recording started automatically',
                'recording_started': AUDIO_AVAILABLE,
                'recording_file': call_recordings[call_id]['recording_file'] if AUDIO_AVAILABLE and call_id in call_recordings else None
            })
        
        # Try SIP service if not in active calls
        elif sip_service.answer_call(call_id):
            return jsonify({'success': True, 'message': 'Call answered'})
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error answering call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-answer-call/<call_id>')
def test_answer_call(call_id):
    """Test endpoint to answer a call without authentication (for testing)"""
    try:
        # Check if call exists in active calls
        if call_id in active_calls:
            # Update call status
            active_calls[call_id]['status'] = 'answered'
            active_calls[call_id]['start_time'] = datetime.now().isoformat()
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'answered', start_time = %s 
                    WHERE call_id = %s
                """, (datetime.now(), call_id))
                connection.commit()
            
            # Automatically start recording when call is answered
            if AUDIO_AVAILABLE:
                try:
                    # Create recordings directory if it doesn't exist
                    os.makedirs("recordings", exist_ok=True)
                    
                    # Initialize recording for this call
                    call_recordings[call_id] = {
                        'audio_frames': [],
                        'is_recording': True,
                        'start_time': datetime.now(),
                        'audio_data': [],
                        'recording_file': f"recordings/call_{call_id}.wav"
                    }
                    
                    # Update call status to show recording is active
                    active_calls[call_id]['recording'] = True
                    active_calls[call_id]['recording_started'] = datetime.now().isoformat()
                    
                    logger.info(f"TEST: Call answered and recording automatically started for call {call_id}")
                    
                    # Emit WebSocket update to notify phone simulator that call is answered
                    socketio.emit('call_answered', {
                        'call_id': call_id,
                        'status': 'answered',
                        'recording_started': True
                    }, room=f'call_{call_id}')
                    
                except Exception as recording_error:
                    logger.error(f"Error starting automatic recording: {recording_error}")
            else:
                logger.warning(f"Audio recording not available - call answered without recording for {call_id}")
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            
            return jsonify({
                'success': True, 
                'message': 'TEST: Call answered and recording started automatically',
                'recording_started': AUDIO_AVAILABLE,
                'recording_file': call_recordings[call_id]['recording_file'] if AUDIO_AVAILABLE and call_id in call_recordings else None
            })
        
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error answering call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-hangup-call/<call_id>')
def test_hangup_call(call_id):
    """Test endpoint to hang up a call without authentication (for testing)"""
    try:
        # Check if call exists in active calls
        if call_id in active_calls:
            # Stop recording if active
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    # Stop recording first
                    call_recordings[call_id]['is_recording'] = False
                    call_recordings[call_id]['end_time'] = datetime.now()
                    
                    # Get recording file path
                    recording_path = call_recordings[call_id]['recording_file']
                    
                    # Log recording details for debugging
                    frames_count = len(call_recordings[call_id]['audio_frames'])
                    total_bytes = sum(len(frame) for frame in call_recordings[call_id]['audio_frames'])
                    logger.info(f"TEST: Stopping recording for call {call_id}: {frames_count} frames, {total_bytes} bytes")
                    
                    # Create WAV file with recorded audio data
                    if call_recordings[call_id]['audio_frames']:
                        # Create WAV file from recorded frames
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            
                            # Combine all audio frames
                            audio_data = b''.join(call_recordings[call_id]['audio_frames'])
                            wf.writeframes(audio_data)
                            
                            logger.info(f"TEST: Recording stopped and saved for call {call_id}: {recording_path} ({len(audio_data)} bytes)")
                    else:
                        # Create a minimal WAV file if no audio data
                        logger.warning(f"TEST: No audio frames recorded for call {call_id}, creating silent file")
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            # Create 1 second of silence
                            sample_size = 2 if not AUDIO_AVAILABLE else pyaudio.get_sample_size(FORMAT)
                            silence = b'\x00' * (RATE * CHANNELS * sample_size)
                            wf.writeframes(silence)
                            logger.info(f"TEST: Recording stopped and saved for call {call_id}: {recording_path} (silent)")
                    
                    # Update database with recording path
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE calls SET recording_path = %s 
                            WHERE call_id = %s
                        """, (recording_path, call_id))
                        connection.commit()
                    
                except Exception as recording_error:
                    logger.error(f"Error stopping recording during hangup: {recording_error}")
            else:
                logger.info(f"TEST: Call {call_id} hung up without active recording")
            
            # Calculate call duration
            start_time = active_calls[call_id].get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration = int((datetime.now() - start_time).total_seconds())
            else:
                duration = 0
            
            # Update call status
            active_calls[call_id]['status'] = 'ended'
            active_calls[call_id]['end_time'] = datetime.now().isoformat()
            active_calls[call_id]['duration'] = duration
            active_calls[call_id]['recording'] = False
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'ended', end_time = %s, duration = %s 
                    WHERE call_id = %s
                """, (datetime.now(), duration, call_id))
                connection.commit()
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            
            # Remove from active calls AFTER recording is saved
            call_data = active_calls.pop(call_id)
            
            # Clean up recording data
            if call_id in call_recordings:
                del call_recordings[call_id]
            
            return jsonify({
                'success': True, 
                'message': 'TEST: Call ended and recording saved automatically',
                'duration': duration,
                'recording_saved': call_id in call_recordings if 'call_id' in locals() else False
            })
        
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error answering call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/reject', methods=['POST'])
@login_required
def reject_call(call_id):
    """Reject incoming call"""
    try:
        logger.info(f"Rejecting call {call_id}")
        
        # Get data from request, handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            reason = data.get('reason', 'user_rejected') if data else 'user_rejected'
        else:
            reason = request.form.get('reason', 'user_rejected')
        
        # Check if call exists in active calls
        if call_id in active_calls:
            # Stop recording if active
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    # Stop recording first
                    call_recordings[call_id]['is_recording'] = False
                    call_recordings[call_id]['end_time'] = datetime.now()
                    
                    # Get recording file path
                    recording_path = call_recordings[call_id]['recording_file']
                    
                    # Create WAV file with recorded audio data
                    if call_recordings[call_id]['audio_frames']:
                        # Create WAV file from recorded frames
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            
                            # Combine all audio frames
                            audio_data = b''.join(call_recordings[call_id]['audio_frames'])
                            wf.writeframes(audio_data)
                            
                            logger.info(f"Recording stopped and saved for rejected call {call_id}: {recording_path} ({len(audio_data)} bytes)")
                    else:
                        # Create a minimal WAV file if no audio data
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            # Create 1 second of silence
                            sample_size = 2 if not AUDIO_AVAILABLE else pyaudio.get_sample_size(FORMAT)
                            silence = b'\x00' * (RATE * CHANNELS * sample_size)
                            wf.writeframes(silence)
                            logger.info(f"Recording stopped and saved for rejected call {call_id}: {recording_path} (silent)")
                    
                    # Update database with recording path
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE calls SET recording_path = %s 
                            WHERE call_id = %s
                        """, (recording_path, call_id))
                        connection.commit()
                    
                except Exception as recording_error:
                    logger.error(f"Error stopping recording during reject: {recording_error}")
            
            # Update call status
            active_calls[call_id]['status'] = 'rejected'
            active_calls[call_id]['end_time'] = datetime.now().isoformat()
            active_calls[call_id]['recording'] = False
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'rejected', end_time = %s 
                    WHERE call_id = %s
                """, (datetime.now(), call_id))
                connection.commit()
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            socketio.emit('call_status_update', {
                'call_id': call_id,
                'status': 'rejected',
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }, room='general')
            
            # Remove from active calls AFTER recording is saved
            call_data = active_calls.pop(call_id)
            
            # Clean up recording data
            if call_id in call_recordings:
                del call_recordings[call_id]
            
            logger.info(f"Call {call_id} rejected successfully with reason: {reason}")
            
            return jsonify({
                'success': True, 
                'message': 'Call rejected and recording saved automatically',
                'recording_saved': True
            })
        
        # Try SIP service if not in active calls
        elif sip_service.reject_call(call_id, reason):
            return jsonify({'success': True, 'message': 'Call rejected'})
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error rejecting call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/transfer', methods=['POST'])
@login_required
def transfer_call(call_id):
    """Transfer call to another number"""
    try:
        data = request.get_json()
        to_number = data.get('to_number')
        
        if not to_number:
            return jsonify({'error': 'Missing to_number'}), 400
        
        # Check if call exists in active calls
        if call_id in active_calls:
            # Stop recording if active
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    # Stop recording first
                    call_recordings[call_id]['is_recording'] = False
                    call_recordings[call_id]['end_time'] = datetime.now()
                    
                    # Get recording file path
                    recording_path = call_recordings[call_id]['recording_file']
                    
                    # Create WAV file with recorded audio data
                    if call_recordings[call_id]['audio_frames']:
                        # Create WAV file from recorded frames
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            
                            # Combine all audio frames
                            audio_data = b''.join(call_recordings[call_id]['audio_frames'])
                            wf.writeframes(audio_data)
                            
                            logger.info(f"Recording stopped and saved for transferred call {call_id}: {recording_path} ({len(audio_data)} bytes)")
                    else:
                        # Create a minimal WAV file if no audio data
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            # Create 1 second of silence
                            sample_size = 2 if not AUDIO_AVAILABLE else pyaudio.get_sample_size(FORMAT)
                            silence = b'\x00' * (RATE * CHANNELS * sample_size)
                            wf.writeframes(silence)
                            logger.info(f"Recording stopped and saved for transferred call {call_id}: {recording_path} (silent)")
                    
                    # Update database with recording path
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE calls SET recording_path = %s 
                            WHERE call_id = %s
                        """, (recording_path, call_id))
                        connection.commit()
                    
                except Exception as recording_error:
                    logger.error(f"Error stopping recording during transfer: {recording_error}")
            
            # Update call status
            active_calls[call_id]['status'] = 'transferred'
            active_calls[call_id]['end_time'] = datetime.now().isoformat()
            active_calls[call_id]['recording'] = False
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'transferred', end_time = %s 
                    WHERE call_id = %s
                """, (datetime.now(), call_id))
                connection.commit()
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            
            # Remove from active calls AFTER recording is saved
            call_data = active_calls.pop(call_id)
            
            # Clean up recording data
            if call_id in call_recordings:
                del call_recordings[call_id]
            
            return jsonify({
                'success': True, 
                'message': f'Call transferred to {to_number} and recording saved automatically',
                'recording_saved': True
            })
        
        # Try SIP service if not in active calls
        elif sip_service.transfer_call(call_id, to_number):
            return jsonify({'success': True, 'message': 'Call transferred'})
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error transferring call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forwarding-rules', methods=['GET'])
@login_required
def get_forwarding_rules():
    """Get all forwarding rules"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM forwarding_rules ORDER BY priority DESC")
            rules = cursor.fetchall()
            
            # Process rules for JSON response
            processed_rules = []
            for rule in rules:
                processed_rule = {
                    'id': rule['id'],
                    'name': rule['name'],
                    'pattern': rule['pattern'],
                    'priority': rule['priority'],
                    'enabled': rule['enabled'],
                    'forward_to': rule['forward_to'],
                    'forward_to_users': json.loads(rule['forward_to_users']) if rule['forward_to_users'] else [],
                    'schedule_enabled': rule['schedule_enabled'],
                    'schedule_start': rule['schedule_start'].isoformat() if rule['schedule_start'] else None,
                    'schedule_end': rule['schedule_end'].isoformat() if rule['schedule_end'] else None,
                    'schedule_days': json.loads(rule['schedule_days']) if rule['schedule_days'] else []
                }
                processed_rules.append(processed_rule)
            
    except Exception as e:
        logger.error(f"Error loading forwarding rules: {e}")
        processed_rules = []
    finally:
        if connection:
            connection.close()
    
    return jsonify({
        'success': True,
        'data': processed_rules
    })

@app.route('/api/forwarding-rules', methods=['POST'])
@login_required
def create_forwarding_rule():
    """Create new forwarding rule"""
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO forwarding_rules (name, pattern, priority, enabled, forward_to, forward_to_users, schedule_enabled, schedule_start, schedule_end, schedule_days, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['name'],
                data['pattern'],
                data.get('priority', 100),
                data.get('enabled', True),
                data['forward_to'],
                json.dumps(data.get('forward_to_users', [])),
                data.get('schedule_enabled', False),
                datetime.strptime(data['schedule_start'], '%H:%M').time() if data.get('schedule_start') else None,
                datetime.strptime(data['schedule_end'], '%H:%M').time() if data.get('schedule_end') else None,
                json.dumps(data.get('schedule_days', [])),
                datetime.utcnow()
            ))
            connection.commit()
        
        return jsonify({'success': True, 'message': 'Rule created successfully'})
    
    except Exception as e:
        logger.error(f"Error creating forwarding rule: {e}")
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/sip/status', methods=['GET'])
@login_required
def get_sip_status():
    """Get SIP system status"""
    try:
        status = sip_service.get_system_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting SIP status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sip/simulate-call', methods=['POST'])
@login_required
def simulate_incoming_call():
    """Manually trigger a simulated incoming call"""
    try:
        sip_service.simulate_incoming_call()
        return jsonify({
            'success': True,
            'message': 'Incoming call simulation triggered'
        })
    except Exception as e:
        logger.error(f"Error simulating incoming call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/simulate-call')
def simulate_call_query():
    """Simple endpoint to simulate a call using query parameter"""
    phone_number = request.args.get('number', '')
    
    if not phone_number:
        return jsonify({
            'success': False,
            'message': 'Please provide a phone number. Use: /simulate-call?number=1234567890'
        })
    
    try:
        # Generate unique call ID
        call_id = f"sim_{int(time.time())}"
        
        # Simulate an incoming call
        call_data = {
            'id': call_id,
            'call_id': call_id,
            'caller_id': phone_number,
            'caller_name': f'Caller {phone_number}',
            'status': 'ringing',
            'direction': 'inbound',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration': None,
            'user_id': None,
            'sip_channel': None
        }
        
        # Create call in database
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                call_id,
                call_data['caller_id'],
                call_data['caller_name'],
                call_data['status'],
                call_data['direction'],
                datetime.now()
            ))
            connection.commit()
        
        # Add to active calls
        active_calls[call_id] = call_data
        
        # Emit real-time update via WebSocket
        socketio.emit('new_call', call_data)
        socketio.emit('call_update', call_data)
        
        logger.info(f"Call simulated successfully: {call_id} from {phone_number}")
        
        return jsonify({
            'success': True,
            'message': f'Call simulated for number {phone_number}',
            'call_data': call_data,
            'call_id': call_id,
            'test_url': f'http://localhost:5000/simulate-call?number={phone_number}'
        })
        
    except Exception as e:
        logger.error(f"Error simulating call: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-call/<phone_number>')
def test_call_endpoint(phone_number):
    """Simple test endpoint to simulate a call for a specific number"""
    try:
        # Check if this is a test number
        if phone_number == "1234567890":  # Your test number
            # Generate unique call ID
            call_id = f"test_{int(time.time())}"
            
            # Simulate an incoming call
            call_data = {
                'id': call_id,
                'call_id': call_id,
                'caller_id': phone_number,
                'caller_name': 'Test Caller',
                'status': 'ringing',
                'direction': 'inbound',
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'duration': None,
                'user_id': None,
                'sip_channel': None
            }
            
            # Create call in database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    call_id,
                    call_data['caller_id'],
                    call_data['caller_name'],
                    call_data['status'],
                    call_data['direction'],
                    datetime.now()
                ))
                connection.commit()
            
            # Add to active calls
            active_calls[call_id] = call_data
            
            # Emit real-time update via WebSocket
            socketio.emit('new_call', call_data)
            socketio.emit('call_update', call_data)
            
            logger.info(f"Test call simulated successfully: {call_id} from {phone_number}")
            
            return jsonify({
                'success': True,
                'message': f'Test call simulated for number {phone_number}',
                'call_data': call_data,
                'call_id': call_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Number {phone_number} is not a test number. Use 1234567890 to simulate a call.'
            })
            
    except Exception as e:
        logger.error(f"Error in test call endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calls/<call_id>/start-recording', methods=['POST'])
@login_required
def start_call_recording(call_id):
    """Start recording a call"""
    try:
        if not AUDIO_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Audio recording not available. Please install pyaudio and numpy.'
            }), 400
            
        if call_id in active_calls:
            # Create recordings directory if it doesn't exist
            os.makedirs("recordings", exist_ok=True)
            
            # Initialize recording for this call
            call_recordings[call_id] = {
                'audio_frames': [],
                'is_recording': True,
                'start_time': datetime.now(),
                'audio_data': [],
                'recording_file': f"recordings/call_{call_id}.wav"
            }
            
            # Update call status
            active_calls[call_id]['recording'] = True
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            
            logger.info(f"Recording started for call {call_id}")
            
            return jsonify({
                'success': True, 
                'message': 'Call recording started',
                'call_id': call_id,
                'recording_file': call_recordings[call_id]['recording_file']
            })
        else:
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error starting call recording: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/stop-recording', methods=['POST'])
@login_required
def stop_call_recording(call_id):
    """Stop recording a call and save the audio"""
    try:
        if not AUDIO_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Audio recording not available. Please install pyaudio and numpy.'
            }), 400
            
        if call_id in active_calls and call_id in call_recordings:
            # Stop recording
            call_recordings[call_id]['is_recording'] = False
            call_recordings[call_id]['end_time'] = datetime.now()
            
            # Get recording file path
            recording_path = call_recordings[call_id]['recording_file']
            actual_duration = 1.0  # Default duration
            
            # Create WAV file with recorded audio data
            if call_recordings[call_id]['audio_frames']:
                try:
                    # Use FFmpeg for proper WebM to WAV conversion
                    import tempfile
                    import subprocess
                    import os
                    
                    # Combine all WebM audio frames
                    webm_audio = b''.join(call_recordings[call_id]['audio_frames'])
                    
                    # Validate WebM data before creating temp file
                    if len(webm_audio) < 100:  # WebM files should be at least 100 bytes
                        logger.warning(f"WebM audio data too small for call {call_id}: {len(webm_audio)} bytes")
                        raise Exception("WebM audio data too small")
                    
                    # Create temporary WebM file
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                        temp_webm.write(webm_audio)
                        temp_webm_path = temp_webm.name
                    
                    try:
                        # Use FFmpeg to convert WebM to WAV
                        ffmpeg_path = r"C:\ffmpeg-2025-08-20-git-4d7c609be3-essentials_build\bin\ffmpeg.exe"
                        
                        # Verify FFmpeg exists
                        if not os.path.exists(ffmpeg_path):
                            raise FileNotFoundError(f"FFmpeg not found at {ffmpeg_path}")
                        
                        # FFmpeg command: convert WebM to WAV with proper audio settings
                        # Added -f webm to force WebM format detection
                        cmd = [
                            ffmpeg_path,
                            '-f', 'webm',                    # Force WebM format
                            '-i', temp_webm_path,            # Input WebM file
                            '-acodec', 'pcm_s16le',          # 16-bit PCM codec
                            '-ac', '1',                       # Mono audio
                            '-ar', '44100',                   # 44.1kHz sample rate
                            '-y',                             # Overwrite output file
                            recording_path                    # Output WAV file
                        ]
                        
                        logger.info(f"Running FFmpeg command for call {call_id}: {' '.join(cmd)}")
                        logger.info(f"Input WebM size: {len(webm_audio)} bytes")
                        
                        # Execute FFmpeg conversion with longer timeout
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=60  # Increased timeout to 60 seconds
                        )
                        
                        if result.returncode == 0:
                            # Conversion successful
                            if os.path.exists(recording_path):
                                file_size = os.path.getsize(recording_path)
                                
                                # Estimate duration based on file size and audio format
                                # WAV: 44.1kHz, 16-bit, mono = 88200 bytes per second
                                estimated_duration = file_size / 88200
                                
                                logger.info(f"FFmpeg conversion successful for call {call_id}")
                                logger.info(f"Recording saved: {recording_path} ({file_size} bytes, ~{estimated_duration:.2f}s)")
                            else:
                                raise Exception("Output file not created by FFmpeg")
                        else:
                            # FFmpeg failed - try alternative approach
                            logger.warning(f"FFmpeg conversion failed for call {call_id}, trying alternative method")
                            
                            # Alternative: Try without forcing format
                            alt_cmd = [
                                ffmpeg_path,
                                '-i', temp_webm_path,            # Input file (let FFmpeg auto-detect)
                                '-acodec', 'pcm_s16le',          # 16-bit PCM codec
                                '-ac', '1',                       # Mono audio
                                '-ar', '44100',                   # 44.1kHz sample rate
                                '-y',                             # Overwrite output file
                                recording_path                    # Output WAV file
                            ]
                            
                            logger.info(f"Trying alternative FFmpeg command: {' '.join(alt_cmd)}")
                            
                            alt_result = subprocess.run(
                                alt_cmd,
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            
                            if alt_result.returncode == 0 and os.path.exists(recording_path):
                                file_size = os.path.getsize(recording_path)
                                estimated_duration = file_size / 88200
                                logger.info(f"Alternative FFmpeg conversion successful for call {call_id}")
                                logger.info(f"Recording saved: {recording_path} ({file_size} bytes, ~{estimated_duration:.2f}s)")
                            else:
                                # Both methods failed
                                error_msg = f"FFmpeg conversion failed: {result.stderr}"
                                if alt_result.stderr:
                                    error_msg += f" | Alternative failed: {alt_result.stderr}"
                                logger.error(error_msg)
                                raise Exception(error_msg)
                        
                    except subprocess.TimeoutExpired:
                        logger.error(f"FFmpeg conversion timed out for call {call_id}")
                        raise Exception("FFmpeg conversion timed out")
                    except FileNotFoundError:
                        logger.error(f"FFmpeg not found at {ffmpeg_path}")
                        raise Exception("FFmpeg executable not found")
                    except Exception as ffmpeg_error:
                        logger.error(f"FFmpeg error for call {call_id}: {ffmpeg_error}")
                        raise Exception(f"FFmpeg error: {ffmpeg_error}")
                    
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_webm_path)
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to clean up temp file: {cleanup_error}")
                            
                except Exception as conversion_error:
                    logger.error(f"Error converting audio for call {call_id}: {conversion_error}")
                    
                    # Emergency fallback: Create minimal WAV file
                    with wave.open(recording_path, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(RATE)
                        # Create 1 second of silence
                        silence = b'\x00' * (RATE * CHANNELS * 2)
                        wf.writeframes(silence)
                    
                    logger.error(f"Emergency fallback: Created silent WAV file for call {call_id}")
                    actual_duration = 1.0
            else:
                # Create a minimal WAV file if no audio data
                logger.warning(f"No audio frames recorded for call {call_id}, creating silent file")
                with wave.open(recording_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(RATE)
                    
                    # Create 1 second of silence as fallback
                    silence = b'\x00' * (RATE * CHANNELS * 2)
                    wf.writeframes(silence)
                    logger.warning(f"Created silent recording file for call {call_id}")
                
                actual_duration = 1.0
            
            # Update call with recording info
            active_calls[call_id]['recording'] = False
            active_calls[call_id]['recording_path'] = recording_path
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET recording_path = %s 
                    WHERE call_id = %s
                """, (recording_path, call_id))
                connection.commit()
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            
            return jsonify({
                'success': True, 
                'message': 'Recording stopped and saved',
                'recording_path': recording_path,
                'audio_frames_count': len(call_recordings[call_id]['audio_frames']),
                'file_size': os.path.getsize(recording_path) if os.path.exists(recording_path) else 0,
                'duration_seconds': actual_duration
            })
            
        else:
            return jsonify({'error': 'Call not found or not recording'}), 404
            
    except Exception as e:
        logger.error(f"Error stopping call recording: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/admin-audio', methods=['POST'])
@login_required
def receive_admin_audio(call_id):
    """Receive audio data from admin and stream to caller"""
    try:
        if call_id in active_calls and call_id in call_recordings:
            data = request.get_json()
            audio_data = data.get('audio_data', '')
            
            if audio_data and call_recordings[call_id]['is_recording']:
                try:
                    # Decode base64 audio data
                    audio_bytes = base64.b64decode(audio_data)
                    
                    # Store admin audio frame for recording
                    call_recordings[call_id]['audio_frames'].append(audio_bytes)
                    
                    # Store in audio streams for real-time communication
                    if call_id not in audio_streams:
                        audio_streams[call_id] = {
                            'caller_audio': [],
                            'admin_audio': [],
                            'last_update': datetime.now()
                        }
                    
                    # Add admin audio to stream
                    audio_streams[call_id]['admin_audio'].append({
                        'data': audio_data,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'admin'
                    })
                    
                    # Keep only last 100 audio frames to prevent memory issues
                    if len(audio_streams[call_id]['admin_audio']) > 100:
                        audio_streams[call_id]['admin_audio'] = audio_streams[call_id]['admin_audio'][-100:]
                    
                    logger.debug(f"Received admin audio frame for call {call_id}: {len(audio_bytes)} bytes")
                    
                    # Emit audio to caller (real-time streaming)
                    socketio.emit('admin_audio_received', {
                        'call_id': call_id,
                        'audio_data': audio_data,
                        'source': 'admin',
                        'timestamp': datetime.now().isoformat()
                    }, room=f'call_{call_id}')
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Admin audio received and streamed to caller',
                        'frames_count': len(call_recordings[call_id]['audio_frames']),
                        'total_bytes': sum(len(frame) for frame in call_recordings[call_id]['audio_frames']),
                        'streamed': True
                    })
                except Exception as decode_error:
                    logger.error(f"Error decoding admin audio data: {decode_error}")
                    return jsonify({'error': 'Invalid audio data format'}), 400
            else:
                return jsonify({'error': 'Call not recording or invalid audio data'}), 400
        else:
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error receiving admin audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/audio', methods=['POST'])
@login_required
def receive_call_audio(call_id):
    """Receive audio data from the caller during the call and stream to admin"""
    try:
        if call_id in active_calls and call_id in call_recordings:
            data = request.get_json()
            audio_data = data.get('audio_data', '')
            for_recording = data.get('for_recording', False)
            
            if audio_data and call_recordings[call_id]['is_recording']:
                try:
                    # Decode base64 audio data
                    audio_bytes = base64.b64decode(audio_data)
                    
                    # Log audio frame details for debugging
                    logger.info(f"Received audio frame for call {call_id}: {len(audio_bytes)} bytes, for_recording: {for_recording}")
                    
                    # Store audio frame for recording
                    call_recordings[call_id]['audio_frames'].append(audio_bytes)
                    
                    # Store in audio streams for real-time communication
                    if call_id not in audio_streams:
                        audio_streams[call_id] = {
                            'caller_audio': [],
                            'admin_audio': [],
                            'last_update': datetime.now()
                        }
                    
                    # Add caller audio to stream
                    audio_streams[call_id]['caller_audio'].append({
                        'data': audio_data,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'caller'
                    })
                    
                    # Keep only last 100 audio frames to prevent memory issues
                    if len(audio_streams[call_id]['caller_audio']) > 100:
                        audio_streams[call_id]['caller_audio'] = audio_streams[call_id]['caller_audio'][-100:]
                    
                    # Log recording progress
                    if for_recording:
                        frames_count = len(call_recordings[call_id]['audio_frames'])
                        total_bytes = sum(len(frame) for frame in call_recordings[call_id]['audio_frames'])
                        if frames_count % 10 == 0:  # Log every 10 frames for debugging
                            logger.info(f"Recording progress for call {call_id}: {frames_count} frames, {total_bytes} bytes")
                    
                    logger.debug(f"Received caller audio frame for call {call_id}: {len(audio_bytes)} bytes")
                    
                    # Emit audio to admin (real-time streaming)
                    socketio.emit('caller_audio_received', {
                        'call_id': call_id,
                        'audio_data': audio_data,
                        'source': 'caller',
                        'timestamp': datetime.now().isoformat()
                    }, room=f'call_{call_id}')
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Caller audio received and streamed to admin',
                        'frames_count': len(call_recordings[call_id]['audio_frames']),
                        'total_bytes': sum(len(frame) for frame in call_recordings[call_id]['audio_frames']),
                        'streamed': True,
                        'for_recording': for_recording
                    })
                except Exception as decode_error:
                    logger.error(f"Error decoding caller audio data: {decode_error}")
                    return jsonify({'error': 'Invalid audio data format'}), 400
            else:
                if not audio_data:
                    logger.warning(f"Empty audio data received for call {call_id}")
                if not call_recordings[call_id]['is_recording']:
                    logger.warning(f"Call {call_id} is not recording")
                return jsonify({'error': 'Call not recording or invalid audio data'}), 400
        else:
            if call_id not in active_calls:
                logger.warning(f"Call {call_id} not found in active calls")
            if call_id not in call_recordings:
                logger.warning(f"Call {call_id} not found in call recordings")
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error receiving caller audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/generate-test-audio', methods=['POST'])
@login_required
def generate_test_audio(call_id):
    """Generate test audio data for phone simulator testing"""
    try:
        if call_id in active_calls and call_id in call_recordings:
            # Generate 500ms of test audio (sine wave at 440Hz)
            import math
            
            # Audio parameters
            sample_rate = 44100
            duration = 0.5  # 500ms instead of 1 second for more frequent updates
            frequency = 440  # A4 note
            amplitude = 0.3
            
            # Generate samples
            num_samples = int(sample_rate * duration)
            test_audio = []
            
            for i in range(num_samples):
                # Generate sine wave
                sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
                # Convert to 16-bit integer
                int_sample = int(sample * 32767)
                # Convert to bytes (little-endian)
                test_audio.extend([int_sample & 0xFF, (int_sample >> 8) & 0xFF])
            
            test_audio_bytes = bytes(test_audio)
            
            # Store test audio frame for recording
            call_recordings[call_id]['audio_frames'].append(test_audio_bytes)
            
            # Log progress every 50 frames to avoid spam
            frames_count = len(call_recordings[call_id]['audio_frames'])
            if frames_count % 50 == 0:
                total_bytes = sum(len(frame) for frame in call_recordings[call_id]['audio_frames'])
                logger.info(f"Generated test audio for call {call_id}: {frames_count} frames, {total_bytes} bytes")
            
            return jsonify({
                'success': True,
                'message': 'Test audio generated and stored',
                'frames_count': len(call_recordings[call_id]['audio_frames']),
                'total_bytes': sum(len(frame) for frame in call_recordings[call_id]['audio_frames']),
                'test_audio_size': len(test_audio_bytes),
                'audio_duration_ms': duration * 1000
            })
        else:
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error generating test audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/play-audio', methods=['GET'])
@login_required
def play_call_audio(call_id):
    """Play back recorded call audio"""
    try:
        if call_id in active_calls and 'recording_path' in active_calls[call_id]:
            recording_path = active_calls[call_id]['recording_path']
            
            if os.path.exists(recording_path):
                # Return the audio file
                return send_file(recording_path, mimetype='audio/wav')
            else:
                return jsonify({'error': 'Recording file not found'}), 404
        else:
            return jsonify({'error': 'Call not found or no recording'}), 404
            
    except Exception as e:
        logger.error(f"Error playing call audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/join-audio-room', methods=['POST'])
@login_required
def join_call_audio_room(call_id):
    """Join the audio room for a specific call"""
    try:
        if call_id in active_calls:
            # Join the call's audio room
            join_room(f'call_{call_id}')
            
            return jsonify({
                'success': True, 
                'message': f'Joined audio room for call {call_id}',
                'room': f'call_{call_id}'
            })
        else:
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error joining audio room: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug/active-calls')
def debug_active_calls():
    """Debug endpoint to check active calls"""
    return jsonify({
        'success': True,
        'active_calls_count': len(active_calls),
        'active_calls': active_calls,
        'call_queue_count': len(call_queue)
    })

@app.route('/test-system')
def test_system():
    """Test endpoint to check system status"""
    try:
        # Check database connection
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM calls")
            calls_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM users")
            users_count = cursor.fetchone()['count']
        
        # Check audio capabilities
        audio_status = "Available" if AUDIO_AVAILABLE else "Not Available"
        
        # Check active calls
        active_calls_count = len(active_calls)
        
        return jsonify({
            'success': True,
            'system_status': 'Running',
            'database': 'Connected',
            'audio_recording': audio_status,
            'active_calls': active_calls_count,
            'total_calls': calls_count,
            'total_users': users_count,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System test error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/test-recordings')
def test_recordings():
    """Test endpoint to check recordings"""
    try:
        import os
        
        # Check if recordings directory exists
        recordings_dir = "recordings"
        recordings_exist = os.path.exists(recordings_dir)
        
        # List recording files
        recording_files = []
        if recordings_exist:
            recording_files = [f for f in os.listdir(recordings_dir) if f.endswith('.wav')]
        
        # Get calls with recording paths from database
        connection = get_db_connection()
        recorded_calls = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT call_id, caller_id, caller_name, status, recording_path, 
                       start_time, end_time, duration 
                FROM calls 
                WHERE recording_path IS NOT NULL 
                ORDER BY start_time DESC
            """)
            recorded_calls = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'recordings_directory_exists': recordings_exist,
            'recording_files_count': len(recording_files),
            'recording_files': recording_files,
            'recorded_calls_count': len(recorded_calls),
            'recorded_calls': recorded_calls,
            'audio_available': AUDIO_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking recordings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/test-audio-recording')
def test_audio_recording():
    """Test endpoint to create a simple test audio file"""
    try:
        # Create recordings directory
        os.makedirs("recordings", exist_ok=True)
        
        # Create a test audio file with a simple tone
        test_file = "recordings/test_audio.wav"
        
        # Generate a simple sine wave tone (440 Hz for 2 seconds)
        import math
        sample_rate = 44100
        duration = 2  # seconds
        frequency = 440  # Hz (A note)
        
        # Generate audio samples
        samples = []
        for i in range(int(sample_rate * duration)):
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
            samples.append(sample)
        
        # Convert to bytes
        audio_data = b''.join([sample.to_bytes(2, byteorder='little', signed=True) for sample in samples])
        
        # Create WAV file
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        
        file_size = os.path.getsize(test_file)
        
        return jsonify({
            'success': True,
            'message': 'Test audio file created successfully',
            'file_path': test_file,
            'file_size': file_size,
            'duration': duration,
            'frequency': frequency,
            'sample_rate': sample_rate,
            'samples_count': len(samples),
            'audio_available': AUDIO_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Error creating test audio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    if request.sid in connected_users:
        user_id = connected_users[request.sid]
        # Update user status
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET is_online = FALSE WHERE id = %s", (user_id,))
                connection.commit()
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
        finally:
            if connection:
                connection.close()
        del connected_users[request.sid]

@socketio.on('authenticate')
def handle_authentication(data):
    """Handle user authentication via WebSocket"""
    try:
        user_id = data.get('user_id')
        token = data.get('token')
        
        if user_id and token:
            connected_users[request.sid] = user_id
            # Update user status
            try:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE users SET is_online = TRUE, last_seen = %s WHERE id = %s", 
                                 (datetime.utcnow(), user_id))
                    connection.commit()
            except Exception as e:
                logger.error(f"Error updating user status: {e}")
            finally:
                if connection:
                    connection.close()
            
            join_room(f'user_{user_id}')
            join_room('general')
            
            emit('authenticated', {'user_id': user_id})
            emit('user_connected', {
                'user_id': user_id,
                'username': 'User',  # You could fetch the username here
                'timestamp': datetime.utcnow().isoformat()
            }, room='general')
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        emit('auth_error', {'message': 'Authentication failed'})

@socketio.on('accept_call')
def handle_accept_call(data):
    """Handle call acceptance from mobile app"""
    try:
        call_id = data.get('call_id')
        user_id = data.get('user_id')
        
        if call_id and user_id:
            if sip_service.answer_call(call_id):
                emit('call_accepted', {
                    'call_id': call_id,
                    'accepted_by': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, room='general')
        
    except Exception as e:
        logger.error(f"Error accepting call: {e}")

@socketio.on('reject_call')
def handle_reject_call(data):
    """Handle call rejection from mobile app"""
    try:
        call_id = data.get('call_id')
        user_id = data.get('user_id')
        reason = data.get('reason', 'user_rejected')
        
        if call_id and user_id:
            if sip_service.hangup_call(call_id):
                emit('call_rejected', {
                    'call_id': call_id,
                    'rejected_by': user_id,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat()
                }, room='general')
        
    except Exception as e:
        logger.error(f"Error rejecting call: {e}")

@socketio.on('join_call_room')
def handle_join_call_room(data):
    """Handle joining a call's audio room"""
    try:
        call_id = data.get('call_id')
        if call_id and call_id in active_calls:
            join_room(f'call_{call_id}')
            
            # Initialize audio stream for this call if not exists
            if call_id not in audio_streams:
                audio_streams[call_id] = {
                    'caller_audio': [],
                    'admin_audio': [],
                    'last_update': datetime.now()
                }
            
            emit('joined_call_room', {
                'call_id': call_id,
                'message': f'Joined audio room for call {call_id}',
                'audio_streams_ready': True
            })
        else:
            emit('error', {'message': 'Call not found'})
    except Exception as e:
        logger.error(f"Error joining call room: {e}")
        emit('error', {'message': str(e)})

@socketio.on('leave_call_room')
def handle_leave_call_room(data):
    """Handle leaving a call's audio room"""
    try:
        call_id = data.get('call_id')
        if call_id:
            leave_room(f'call_{call_id}')
            emit('left_call_room', {
                'call_id': call_id,
                'message': f'Left audio room for call {call_id}'
            })
    except Exception as e:
        logger.error(f"Error leaving call room: {e}")
        emit('error', {'message': str(e)})

@socketio.on('call_audio_data')
def handle_call_audio_data(data):
    """Handle incoming audio data during a call"""
    try:
        call_id = data.get('call_id')
        audio_data = data.get('audio_data')
        source = data.get('source', 'caller')
        
        if call_id and audio_data and call_id in active_calls:
            # Forward audio to other participants in the call
            if source == 'caller':
                # Caller audio goes to admin
                emit('call_audio_received', {
                    'call_id': call_id,
                    'audio_data': audio_data,
                    'source': 'caller',
                    'timestamp': datetime.now().isoformat()
                }, room=f'call_{call_id}', include_self=False)
            elif source == 'admin':
                # Admin audio goes to caller
                emit('admin_audio_received', {
                    'call_id': call_id,
                    'audio_data': audio_data,
                    'source': 'admin',
                    'timestamp': datetime.now().isoformat()
                }, room=f'call_{call_id}', include_self=False)
            
            # Store audio if recording is active
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    # Decode and store audio frame
                    audio_bytes = base64.b64decode(audio_data)
                    call_recordings[call_id]['audio_frames'].append(audio_bytes)
                    
                    logger.debug(f"Stored {source} audio frame for call {call_id}: {len(audio_bytes)} bytes")
                except Exception as e:
                    logger.error(f"Error storing audio frame: {e}")
        else:
            emit('error', {'message': 'Invalid call audio data'})
            
    except Exception as e:
        logger.error(f"Error handling call audio data: {e}")
        emit('error', {'message': str(e)})

@socketio.on('call_hangup_from_phone')
def handle_call_hangup_from_phone(data):
    """Handle hangup event from phone simulator"""
    try:
        call_id = data.get('call_id')
        source = data.get('source', 'phone_simulator')
        
        if call_id and call_id in active_calls:
            logger.info(f"Call hangup initiated by {source} for call {call_id}")
            
            # Emit event to all clients in the call room
            emit('call_hangup_from_phone', {
                'call_id': call_id,
                'source': source,
                'timestamp': datetime.now().isoformat()
            }, room=f'call_{call_id}')
            
            # Also emit to general room for admin interface updates
            emit('call_hangup_from_phone', {
                'call_id': call_id,
                'source': source,
                'timestamp': datetime.now().isoformat()
            }, room='general')
            
            logger.info(f"Call hangup event broadcasted for call {call_id}")
        else:
            logger.warning(f"Call hangup event for non-existent call: {call_id}")
            
    except Exception as e:
        logger.error(f"Error handling call hangup from phone: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_audio_streams')
def handle_get_audio_streams(data):
    """Get current audio streams for a call"""
    try:
        call_id = data.get('call_id')
        if call_id and call_id in audio_streams:
            emit('audio_streams_update', {
                'call_id': call_id,
                'caller_audio_count': len(audio_streams[call_id]['caller_audio']),
                'admin_audio_count': len(audio_streams[call_id]['admin_audio']),
                'last_update': audio_streams[call_id]['last_update'].isoformat()
            })
        else:
            emit('error', {'message': 'Audio streams not found for this call'})
    except Exception as e:
        logger.error(f"Error getting audio streams: {e}")
        emit('error', {'message': str(e)})

@app.route('/api/calls/<call_id>/toggle-recording', methods=['POST'])
@login_required
def toggle_call_recording(call_id):
    """Manually toggle recording on/off for a call"""
    try:
        if not AUDIO_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Audio recording not available. Please install pyaudio and numpy.'
            }), 400
            
        if call_id in active_calls:
            # Check if recording is currently active
            is_recording = call_id in call_recordings and call_recordings[call_id]['is_recording']
            
            if is_recording:
                # Stop recording
                call_recordings[call_id]['is_recording'] = False
                call_recordings[call_id]['end_time'] = datetime.now()
                
                # Get recording file path
                recording_path = call_recordings[call_id]['recording_file']
                
                # Create WAV file with recorded audio data
                if call_recordings[call_id]['audio_frames']:
                    try:
                        # Use FFmpeg for proper WebM to WAV conversion
                        import tempfile
                        import subprocess
                        import os
                        
                        # Combine all WebM audio frames
                        webm_audio = b''.join(call_recordings[call_id]['audio_frames'])
                        
                        # Create temporary WebM file
                        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                            temp_webm.write(webm_audio)
                            temp_webm_path = temp_webm.name
                        
                        try:
                            # Use FFmpeg to convert WebM to WAV
                            ffmpeg_path = r"C:\ffmpeg-2025-08-20-git-4d7c609be3-essentials_build\bin\ffmpeg.exe"
                            
                            # FFmpeg command: convert WebM to WAV with proper audio settings
                            cmd = [
                                ffmpeg_path,
                                '-i', temp_webm_path,           # Input WebM file
                                '-acodec', 'pcm_s16le',         # 16-bit PCM codec
                                '-ac', '1',                      # Mono audio
                                '-ar', '44100',                  # 44.1kHz sample rate
                                '-y',                            # Overwrite output file
                                recording_path                   # Output WAV file
                            ]
                            
                            logger.info(f"Running FFmpeg command for toggle recording: {' '.join(cmd)}")
                            
                            # Execute FFmpeg conversion
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                timeout=30  # 30 second timeout
                            )
                            
                            if result.returncode == 0:
                                # Conversion successful
                                if os.path.exists(recording_path):
                                    file_size = os.path.getsize(recording_path)
                                    
                                    # Estimate duration based on file size and audio format
                                    # WAV: 44.1kHz, 16-bit, mono = 88200 bytes per second
                                    estimated_duration = file_size / 88200
                                    
                                    logger.info(f"FFmpeg conversion successful for toggle recording call {call_id}")
                                    logger.info(f"Toggle recording saved: {recording_path} ({file_size} bytes, ~{estimated_duration:.2f}s)")
                                else:
                                    raise Exception("Output file not created by FFmpeg")
                            else:
                                # FFmpeg failed
                                error_msg = f"FFmpeg conversion failed: {result.stderr}"
                                logger.error(error_msg)
                                raise Exception(error_msg)
                            
                        except subprocess.TimeoutExpired:
                            logger.error(f"FFmpeg conversion timed out for toggle recording call {call_id}")
                            raise Exception("FFmpeg conversion timed out")
                        except FileNotFoundError:
                            logger.error(f"FFmpeg not found at {ffmpeg_path}")
                            raise Exception("FFmpeg executable not found")
                        except Exception as ffmpeg_error:
                            logger.error(f"FFmpeg error for toggle recording call {call_id}: {ffmpeg_error}")
                            raise Exception(f"FFmpeg error: {ffmpeg_error}")
                            
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_webm_path)
                            except Exception as cleanup_error:
                                logger.warning(f"Failed to clean up temp file: {cleanup_error}")
                                
                    except Exception as conversion_error:
                        logger.error(f"Error converting audio for toggle recording call {call_id}: {conversion_error}")
                        
                        # Emergency fallback: Create minimal WAV file
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(2)  # 16-bit
                            wf.setframerate(RATE)
                            # Create 1 second of silence
                            silence = b'\x00' * (RATE * CHANNELS * 2)
                            wf.writeframes(silence)
                        
                        logger.error(f"Emergency fallback: Created silent WAV file for toggle recording call {call_id}")
                else:
                    # Create a minimal WAV file if no audio data
                    with wave.open(recording_path, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(RATE)
                        # Create 1 second of silence
                        silence = b'\x00' * (RATE * CHANNELS * 2)
                        wf.writeframes(silence)
                        logger.info(f"Toggle recording stopped for call {call_id}: {recording_path} (silent)")
                
                # Update database with recording path
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE calls SET recording_path = %s 
                        WHERE call_id = %s
                    """, (recording_path, call_id))
                    connection.commit()
                
                # Update call status
                active_calls[call_id]['recording'] = False
                
                # Emit WebSocket update
                socketio.emit('call_update', active_calls[call_id])
                
                return jsonify({
                    'success': True, 
                    'message': 'Recording stopped manually',
                    'recording_active': False,
                    'recording_path': recording_path
                })
            else:
                # Start recording
                # Create recordings directory if it doesn't exist
                os.makedirs("recordings", exist_ok=True)
                
                # Initialize recording for this call
                call_recordings[call_id] = {
                    'audio_frames': [],
                    'is_recording': True,
                    'start_time': datetime.now(),
                    'audio_data': [],
                    'recording_file': f"recordings/call_{call_id}.wav"
                }
                
                # Update call status
                active_calls[call_id]['recording'] = True
                active_calls[call_id]['recording_started'] = datetime.now().isoformat()
                
                # Emit WebSocket update
                socketio.emit('call_update', active_calls[call_id])
                
                logger.info(f"Manual recording started for call {call_id}")
                
                return jsonify({
                    'success': True, 
                    'message': 'Recording started manually',
                    'recording_active': True,
                    'recording_file': call_recordings[call_id]['recording_file']
                })
        else:
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error toggling call recording: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/hangup', methods=['POST'])
@login_required
def hangup_call(call_id):
    """Hang up call"""
    try:
        # Use the unified call termination function
        result = terminate_call(call_id, 'admin_hangup')
        
        if result['success']:
            # Emit WebSocket event to notify all clients
            socketio.emit('call_ended', {
                'call_id': call_id,
                'status': 'ended',
                'reason': 'admin_hangup',
                'timestamp': datetime.now().isoformat()
            }, room='general')
            
            return jsonify(result)
        else:
            # Try SIP service if not in active calls
            if sip_service.hangup_call(call_id):
                return jsonify({'success': True, 'message': 'Call ended via SIP service'})
            else:
                return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error hanging up call: {e}")
        return jsonify({'error': str(e)}), 500

def save_call_recording(call_id):
    """Save recording for a call when it ends"""
    try:
        if call_id in call_recordings and call_recordings[call_id]['is_recording']:
            # Stop recording
            call_recordings[call_id]['is_recording'] = False
            call_recordings[call_id]['end_time'] = datetime.now()
            
            # Get recording file path
            recording_path = call_recordings[call_id]['recording_file']
            
            # Log recording details for debugging
            frames_count = len(call_recordings[call_id]['audio_frames'])
            total_bytes = sum(len(frame) for frame in call_recordings[call_id]['audio_frames'])
            logger.info(f"Auto-saving recording for call {call_id}: {frames_count} frames, {total_bytes} bytes")
            
            # Create WAV file with recorded audio data
            if call_recordings[call_id]['audio_frames']:
                try:
                    # Use FFmpeg for proper WebM to WAV conversion
                    import tempfile
                    import subprocess
                    import os
                    
                    # Combine all WebM audio frames
                    webm_audio = b''.join(call_recordings[call_id]['audio_frames'])
                    
                    # Validate WebM data before creating temp file
                    if len(webm_audio) < 100:  # WebM files should be at least 100 bytes
                        logger.warning(f"WebM audio data too small for call {call_id}: {len(webm_audio)} bytes")
                        raise Exception("WebM audio data too small")
                    
                    # Create temporary WebM file
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                        temp_webm.write(webm_audio)
                        temp_webm_path = temp_webm.name
                    
                    try:
                        # Use FFmpeg to convert WebM to WAV
                        ffmpeg_path = r"C:\ffmpeg-2025-08-20-git-4d7c609be3-essentials_build\bin\ffmpeg.exe"
                        
                        # Verify FFmpeg exists
                        if not os.path.exists(ffmpeg_path):
                            raise FileNotFoundError(f"FFmpeg not found at {ffmpeg_path}")
                        
                        # FFmpeg command: convert WebM to WAV with proper audio settings
                        # Added -f webm to force WebM format detection
                        cmd = [
                            ffmpeg_path,
                            '-f', 'webm',                    # Force WebM format
                            '-i', temp_webm_path,            # Input WebM file
                            '-acodec', 'pcm_s16le',          # 16-bit PCM codec
                            '-ac', '1',                       # Mono audio
                            '-ar', '44100',                   # 44.1kHz sample rate
                            '-y',                             # Overwrite output file
                            recording_path                    # Output WAV file
                        ]
                        
                        logger.info(f"Running FFmpeg command for call {call_id}: {' '.join(cmd)}")
                        logger.info(f"Input WebM size: {len(webm_audio)} bytes")
                        
                        # Execute FFmpeg conversion with longer timeout
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=60  # Increased timeout to 60 seconds
                        )
                        
                        if result.returncode == 0:
                            # Conversion successful
                            if os.path.exists(recording_path):
                                file_size = os.path.getsize(recording_path)
                                
                                # Estimate duration based on file size and audio format
                                # WAV: 44.1kHz, 16-bit, mono = 88200 bytes per second
                                estimated_duration = file_size / 88200
                                
                                logger.info(f"FFmpeg conversion successful for call {call_id}")
                                logger.info(f"Recording saved: {recording_path} ({file_size} bytes, ~{estimated_duration:.2f}s)")
                            else:
                                raise Exception("Output file not created by FFmpeg")
                        else:
                            # FFmpeg failed - try alternative approach
                            logger.warning(f"FFmpeg conversion failed for call {call_id}, trying alternative method")
                            
                            # Alternative: Try without forcing format
                            alt_cmd = [
                                ffmpeg_path,
                                '-i', temp_webm_path,            # Input file (let FFmpeg auto-detect)
                                '-acodec', 'pcm_s16le',          # 16-bit PCM codec
                                '-ac', '1',                       # Mono audio
                                '-ar', '44100',                   # 44.1kHz sample rate
                                '-y',                             # Overwrite output file
                                recording_path                    # Output WAV file
                            ]
                            
                            logger.info(f"Trying alternative FFmpeg command: {' '.join(alt_cmd)}")
                            
                            alt_result = subprocess.run(
                                alt_cmd,
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            
                            if alt_result.returncode == 0 and os.path.exists(recording_path):
                                file_size = os.path.getsize(recording_path)
                                estimated_duration = file_size / 88200
                                logger.info(f"Alternative FFmpeg conversion successful for call {call_id}")
                                logger.info(f"Recording saved: {recording_path} ({file_size} bytes, ~{estimated_duration:.2f}s)")
                            else:
                                # Both methods failed
                                error_msg = f"FFmpeg conversion failed: {result.stderr}"
                                if alt_result.stderr:
                                    error_msg += f" | Alternative failed: {alt_result.stderr}"
                                logger.error(error_msg)
                                raise Exception(error_msg)
                        
                    except subprocess.TimeoutExpired:
                        logger.error(f"FFmpeg conversion timed out for call {call_id}")
                        raise Exception("FFmpeg conversion timed out")
                    except FileNotFoundError:
                        logger.error(f"FFmpeg not found at {ffmpeg_path}")
                        raise Exception("FFmpeg executable not found")
                    except Exception as ffmpeg_error:
                        logger.error(f"FFmpeg error for call {call_id}: {ffmpeg_error}")
                        raise Exception(f"FFmpeg error: {ffmpeg_error}")
                    
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_webm_path)
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to clean up temp file: {cleanup_error}")
                        
                except Exception as conversion_error:
                    logger.error(f"Error converting audio for call {call_id}: {conversion_error}")
                    
                    # Emergency fallback: Create minimal WAV file
                    with wave.open(recording_path, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(RATE)
                        # Create 1 second of silence
                        silence = b'\x00' * (RATE * CHANNELS * 2)
                        wf.writeframes(silence)
                    
                    logger.error(f"Emergency fallback: Created silent WAV file for call {call_id}")
                    
            else:
                # Create a minimal WAV file if no audio data
                logger.warning(f"No audio frames recorded for call {call_id}, creating silent file")
                with wave.open(recording_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(RATE)
                    # Create 1 second of silence
                    silence = b'\x00' * (RATE * CHANNELS * 2)
                    wf.writeframes(silence)
                    logger.info(f"Recording auto-saved for call {call_id}: {recording_path} (silent)")
            
            # Update database with recording path
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET recording_path = %s 
                    WHERE call_id = %s
                """, (recording_path, call_id))
                connection.commit()
            
            return True
        else:
            logger.info(f"No active recording to save for call {call_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error auto-saving recording for call {call_id}: {e}")
        return False

def terminate_call(call_id, reason='user_terminated'):
    """Terminate a call from any source and ensure recording is saved"""
    try:
        if call_id in active_calls:
            logger.info(f"Terminating call {call_id} with reason: {reason}")
            
            # Auto-save recording if active
            recording_saved = False
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    recording_saved = save_call_recording(call_id)
                    logger.info(f"Recording saved for call {call_id}: {recording_saved}")
                except Exception as recording_error:
                    logger.error(f"Error saving recording for call {call_id}: {recording_error}")
                    recording_saved = False
            
            # Calculate call duration
            start_time = active_calls[call_id].get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration = int((datetime.now() - start_time).total_seconds())
            else:
                duration = 0
            
            # Update call status
            active_calls[call_id]['status'] = 'ended'
            active_calls[call_id]['end_time'] = datetime.now().isoformat()
            active_calls[call_id]['duration'] = duration
            active_calls[call_id]['recording'] = False
            
            try:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE calls SET status = 'ended', end_time = %s, duration = %s 
                        WHERE call_id = %s
                    """, (datetime.now(), duration, call_id))
                    connection.commit()
                    logger.info(f"Database updated for call {call_id}")
            except Exception as db_error:
                logger.error(f"Error updating database for call {call_id}: {db_error}")
            
            # Emit WebSocket update
            try:
                socketio.emit('call_update', active_calls[call_id])
                socketio.emit('call_ended', {
                    'call_id': call_id,
                    'status': 'ended',
                    'reason': reason,
                    'duration': duration,
                    'recording_saved': recording_saved,
                    'timestamp': datetime.now().isoformat()
                }, room='general')
                logger.info(f"WebSocket events emitted for call {call_id}")
            except Exception as ws_error:
                logger.error(f"Error emitting WebSocket events for call {call_id}: {ws_error}")
            
            # Remove from active calls AFTER recording is saved
            call_data = active_calls.pop(call_id)
            
            # Clean up recording data
            if call_id in call_recordings:
                del call_recordings[call_id]
            
            logger.info(f"Call {call_id} terminated by {reason}. Recording saved: {recording_saved}, Duration: {duration}s")
            
            return {
                'success': True,
                'message': f'Call terminated ({reason}) and recording saved automatically',
                'duration': duration,
                'recording_saved': recording_saved,
                'reason': reason
            }
        else:
            logger.warning(f"Call {call_id} not found for termination")
            return {
                'success': False,
                'error': 'Call not found'
            }
            
    except Exception as e:
        logger.error(f"Error terminating call {call_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/api/calls/<call_id>/phone-hangup', methods=['POST'])
def phone_hangup_call(call_id):
    """Handle hangup request from phone simulator (no authentication required)"""
    try:
        logger.info(f"Phone hangup request received for call {call_id}")
        
        # Use the unified call termination function
        result = terminate_call(call_id, 'phone_simulator_hangup')
        
        if result['success']:
            logger.info(f"Call {call_id} terminated successfully by phone simulator")
            
            # Emit WebSocket event to notify admin side
            socketio.emit('call_hangup_from_phone', {
                'call_id': call_id,
                'source': 'phone_simulator',
                'timestamp': datetime.now().isoformat(),
                'recording_saved': result.get('recording_saved', False),
                'duration': result.get('duration', 0)
            }, room='general')
            
            return jsonify(result)
        else:
            logger.warning(f"Failed to terminate call {call_id}: {result.get('error', 'Unknown error')}")
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error handling phone hangup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/phone-audio', methods=['POST'])
def receive_phone_audio(call_id):
    """Receive audio data from phone simulator (no authentication required)"""
    try:
        if call_id in active_calls and call_id in call_recordings:
            data = request.get_json()
            audio_data = data.get('audio_data', '')
            for_recording = data.get('for_recording', False)
            is_complete_file = data.get('is_complete_file', False)
            
            if audio_data and call_recordings[call_id]['is_recording']:
                try:
                    # Decode base64 audio data
                    audio_bytes = base64.b64decode(audio_data)
                    
                    # Log audio frame details for debugging
                    logger.info(f"Received phone audio frame for call {call_id}: {len(audio_bytes)} bytes, for_recording: {for_recording}, is_complete_file: {is_complete_file}")
                    
                    # Store audio frame for recording
                    call_recordings[call_id]['audio_frames'].append(audio_bytes)
                    
                    # Store in audio streams for real-time communication
                    if call_id not in audio_streams:
                        audio_streams[call_id] = {
                            'caller_audio': [],
                            'admin_audio': [],
                            'last_update': datetime.now()
                        }
                    
                    # Add caller audio to stream
                    audio_streams[call_id]['caller_audio'].append({
                        'data': audio_data,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'caller'
                    })
                    
                    # Keep only last 100 audio frames to prevent memory issues
                    if len(audio_streams[call_id]['caller_audio']) > 100:
                        audio_streams[call_id]['caller_audio'] = audio_streams[call_id]['caller_audio'][-100:]
                    
                    # Log recording progress
                    if for_recording:
                        frames_count = len(call_recordings[call_id]['audio_frames'])
                        total_bytes = sum(len(frame) for frame in call_recordings[call_id]['audio_frames'])
                        if frames_count % 5 == 0 or is_complete_file:  # Log every 5 frames or complete files
                            logger.info(f"Phone recording progress for call {call_id}: {frames_count} frames, {total_bytes} bytes, complete_file: {is_complete_file}")
                    
                    logger.debug(f"Received phone audio frame for call {call_id}: {len(audio_bytes)} bytes")
                    
                    # Emit audio to admin (real-time streaming)
                    socketio.emit('caller_audio_received', {
                        'call_id': call_id,
                        'audio_data': audio_data,
                        'source': 'caller',
                        'timestamp': datetime.now().isoformat()
                    }, room=f'call_{call_id}')
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Phone audio received and stored for recording',
                        'frames_count': len(call_recordings[call_id]['audio_frames']),
                        'total_bytes': sum(len(frame) for frame in call_recordings[call_id]['audio_frames']),
                        'stored': True,
                        'for_recording': for_recording,
                        'is_complete_file': is_complete_file
                    })
                except Exception as decode_error:
                    logger.error(f"Error decoding phone audio data: {decode_error}")
                    return jsonify({'error': 'Invalid audio data format'}), 400
            else:
                if not audio_data:
                    logger.warning(f"Empty audio data received from phone for call {call_id}")
                if not call_recordings[call_id]['is_recording']:
                    logger.warning(f"Call {call_id} is not recording")
                return jsonify({'error': 'Call not recording or invalid audio data'}), 400
        else:
            if call_id not in active_calls:
                logger.warning(f"Call {call_id} not found in active calls")
            if call_id not in call_recordings:
                logger.warning(f"Call {call_id} not found in call recordings")
            return jsonify({'error': 'Call not found'}), 404
            
    except Exception as e:
        logger.error(f"Error receiving phone audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/get-latest-recording', methods=['GET'])
def get_latest_recording(call_id):
    """Get the latest recording for a specific call ID"""
    try:
        # Check if call exists and has a recording
        if call_id in active_calls and 'recording_path' in active_calls[call_id]:
            recording_path = active_calls[call_id]['recording_path']
            
            if os.path.exists(recording_path):
                # Return the audio file
                return send_file(recording_path, mimetype='audio/wav')
            else:
                return jsonify({'error': 'Recording file not found'}), 404
        else:
            # Check database for recording path
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT recording_path FROM calls 
                    WHERE call_id = %s AND recording_path IS NOT NULL
                    ORDER BY start_time DESC LIMIT 1
                """, (call_id,))
                result = cursor.fetchone()
                
                if result and result['recording_path']:
                    recording_path = result['recording_path']
                    
                    if os.path.exists(recording_path):
                        # Return the audio file
                        return send_file(recording_path, mimetype='audio/wav')
                    else:
                        return jsonify({'error': 'Recording file not found'}), 404
                else:
                    return jsonify({'error': 'No recording found for this call'}), 404
                    
    except Exception as e:
        logger.error(f"Error getting latest recording for call {call_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/calls/<call_id>/final-recording', methods=['POST'])
def final_recording_mix(call_id):
    """Receive final recording data from admin interface and create mixed recording"""
    try:
        if call_id not in call_recordings:
            return jsonify({'success': False, 'error': 'Call not found'}), 404
        
        data = request.get_json()
        admin_audio = data.get('admin_audio', '')
        caller_audio = data.get('caller_audio', '')
        admin_frames = data.get('admin_frames', 0)
        caller_frames = data.get('caller_frames', 0)
        admin_bytes = data.get('admin_bytes', 0)
        caller_bytes = data.get('caller_bytes', 0)
        
        logger.info(f"Final recording data received for call {call_id}:")
        logger.info(f"  Admin: {admin_frames} frames, {admin_bytes} bytes")
        logger.info(f"  Caller: {caller_frames} frames, {caller_bytes} bytes")
        
        if not admin_audio or not caller_audio:
            return jsonify({'success': False, 'error': 'Missing audio data'}), 400
        
        try:
            # Decode base64 audio data
            admin_bytes = base64.b64decode(admin_audio)
            caller_bytes = base64.b64decode(caller_audio)
            
            # Create temporary files for both audio streams
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as admin_temp:
                admin_temp.write(admin_bytes)
                admin_temp_path = admin_temp.name
            
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as caller_temp:
                caller_temp.write(caller_bytes)
                caller_temp_path = caller_temp.name
            
            # Create mixed recording using FFmpeg
            output_path = f"recordings/call_{call_id}_mixed.wav"
            
            # FFmpeg command to mix both audio streams
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', admin_temp_path,      # Admin audio input
                '-i', caller_temp_path,     # Caller audio input
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[mixed]',
                '-map', '[mixed]',
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '44100',
                '-y',  # Overwrite output file
                output_path
            ]
            
            logger.info(f"Running FFmpeg command for mixed recording: {' '.join(ffmpeg_cmd)}")
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Clean up temporary files
            try:
                os.unlink(admin_temp_path)
                os.unlink(caller_temp_path)
            except Exception as e:
                logger.warning(f"Could not clean up temp files: {e}")
            
            if result.returncode == 0:
                # Get file size
                file_size = os.path.getsize(output_path)
                duration = file_size / (44100 * 2)  # 44.1kHz, 16-bit, mono
                
                logger.info(f"Mixed recording created successfully: {output_path}")
                logger.info(f"File size: {file_size} bytes, Duration: {duration:.2f} seconds")
                
                # Update call recording info
                call_recordings[call_id]['mixed_recording_path'] = output_path
                call_recordings[call_id]['mixed_recording_size'] = file_size
                call_recordings[call_id]['mixed_recording_duration'] = duration
                
                return jsonify({
                    'success': True,
                    'message': 'Mixed recording created successfully',
                    'file_path': output_path,
                    'file_size': file_size,
                    'duration': duration,
                    'admin_frames': admin_frames,
                    'caller_frames': caller_frames,
                    'total_frames': admin_frames + caller_frames
                })
            else:
                logger.error(f"FFmpeg failed for mixed recording: {result.stderr}")
                return jsonify({
                    'success': False,
                    'error': f'FFmpeg conversion failed: {result.stderr}'
                }), 500
                
        except Exception as e:
            logger.error(f"Error creating mixed recording: {e}")
            return jsonify({
                'success': False,
                'error': f'Error creating mixed recording: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in final recording endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/incidents', methods=['POST'])
def create_incident_report():
    """Create a new incident report from a call"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['call_id', 'title', 'category_id', 'description', 'priority', 'location_name', 'latitude', 'longitude']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Generate unique incident ID
        import uuid
        incident_id = f"INC_{uuid.uuid4().hex[:8].upper()}"
        
        # Get current user ID if authenticated
        reported_by = None
        if current_user.is_authenticated:
            reported_by = current_user.id
        
        # Create incident record
        incident_data = {
            'incident_id': incident_id,
            'call_id': data['call_id'],
            'category_id': int(data['category_id']),
            'title': data['title'],
            'description': data['description'],
            'priority': data['priority'],
            'location_name': data['location_name'],
            'latitude': float(data['latitude']),
            'longitude': float(data['longitude']),
            'reported_by': reported_by
        }
        
        # Insert into database
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO incidents (incident_id, call_id, category_id, title, description, priority, 
                                     location_name, latitude, longitude, reported_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                incident_data['incident_id'],
                incident_data['call_id'],
                incident_data['category_id'],
                incident_data['title'],
                incident_data['description'],
                incident_data['priority'],
                incident_data['location_name'],
                incident_data['latitude'],
                incident_data['longitude'],
                incident_data['reported_by']
            ))
            connection.commit()
            db_incident_id = cursor.lastrowid
        
        logger.info(f"Incident report created: ID {incident_id} for call {data['call_id']}")
        
        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'db_id': db_incident_id,
            'message': 'Incident report created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating incident report: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create incident report'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/test-recording-save/<call_id>')
def test_recording_save(call_id):
    """Test endpoint to manually save recording for a call"""
    try:
        if call_id in call_recordings:
            logger.info(f"TEST: Manually saving recording for call {call_id}")
            
            # Force save recording
            recording_saved = save_call_recording(call_id)
            
            if recording_saved:
                return jsonify({
                    'success': True,
                    'message': f'Recording saved successfully for call {call_id}',
                    'recording_saved': True
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save recording'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': f'No recording data found for call {call_id}'
            }), 404
            
    except Exception as e:
        logger.error(f"Error in test recording save: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calls/<call_id>/mark-done', methods=['POST'])
@login_required
def mark_call_done(call_id):
    """Mark an answered call as done (completed)"""
    try:
        logger.info(f"Marking call {call_id} as done")
        
        # Check if call exists in active calls
        if call_id in active_calls:
            # Check if call is in answered state
            if active_calls[call_id]['status'] != 'answered':
                return jsonify({'error': 'Call must be answered before marking as done'}), 400
            
            # Stop recording if active
            if call_id in call_recordings and call_recordings[call_id]['is_recording']:
                try:
                    # Stop recording first
                    call_recordings[call_id]['is_recording'] = False
                    call_recordings[call_id]['end_time'] = datetime.now()
                    
                    # Get recording file path
                    recording_path = call_recordings[call_id]['recording_file']
                    
                    # Create WAV file with recorded audio data
                    if call_recordings[call_id]['audio_frames']:
                        # Create WAV file from recorded frames
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            
                            # Combine all audio frames
                            audio_data = b''.join(call_recordings[call_id]['audio_frames'])
                            wf.writeframes(audio_data)
                            
                            logger.info(f"Recording stopped and saved for completed call {call_id}: {recording_path} ({len(audio_data)} bytes)")
                    else:
                        # Create a minimal WAV file if no audio data
                        with wave.open(recording_path, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            if AUDIO_AVAILABLE and FORMAT:
                                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                            else:
                                wf.setsampwidth(2)  # Default to 16-bit
                            wf.setframerate(RATE)
                            # Create 1 second of silence
                            sample_size = 2 if not AUDIO_AVAILABLE else pyaudio.get_sample_size(FORMAT)
                            silence = b'\x00' * (RATE * CHANNELS * sample_size)
                            wf.writeframes(silence)
                            logger.info(f"Recording stopped and saved for completed call {call_id}: {recording_path} (silent)")
                    
                    # Update database with recording path
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE calls SET recording_path = %s 
                            WHERE call_id = %s
                        """, (recording_path, call_id))
                        connection.commit()
                    
                except Exception as recording_error:
                    logger.error(f"Error stopping recording during mark done: {recording_error}")
            
            # Calculate call duration
            start_time = active_calls[call_id].get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration = int((datetime.now() - start_time).total_seconds())
            else:
                duration = 0
            
            # Update call status
            active_calls[call_id]['status'] = 'completed'
            active_calls[call_id]['end_time'] = datetime.now().isoformat()
            active_calls[call_id]['duration'] = duration
            active_calls[call_id]['recording'] = False
            
            # Update database
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE calls SET status = 'completed', end_time = %s, duration = %s 
                    WHERE call_id = %s
                """, (datetime.now(), duration, call_id))
                connection.commit()
            
            # Emit WebSocket update
            socketio.emit('call_update', active_calls[call_id])
            socketio.emit('call_status_update', {
                'call_id': call_id,
                'status': 'completed',
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }, room='general')
            
            # Remove from active calls AFTER recording is saved
            call_data = active_calls.pop(call_id)
            
            # Clean up recording data
            if call_id in call_recordings:
                del call_recordings[call_id]
            
            logger.info(f"Call {call_id} marked as done successfully. Duration: {duration}s")
            
            return jsonify({
                'success': True, 
                'message': 'Call marked as done and recording saved automatically',
                'duration': duration,
                'recording_saved': True
            })
        else:
            return jsonify({'error': 'Call not found'}), 404
    
    except Exception as e:
        logger.error(f"Error marking call as done: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/<call_id>/recording-info', methods=['GET'])
def get_recording_info(call_id):
    """Get recording information for a call"""
    try:
        # Check if call exists and has a recording
        if call_id in active_calls and 'recording_path' in active_calls[call_id]:
            recording_path = active_calls[call_id]['recording_path']
            
            if os.path.exists(recording_path):
                file_size = os.path.getsize(recording_path)
                # Estimate duration based on file size and audio format
                # WAV: 44.1kHz, 16-bit, mono = 88200 bytes per second
                estimated_duration = file_size / 88200
                
                return jsonify({
                    'success': True,
                    'file_size': file_size,
                    'duration': estimated_duration,
                    'file_path': recording_path,
                    'format': 'WAV',
                    'sample_rate': 44100,
                    'channels': 1
                })
            else:
                return jsonify({'error': 'Recording file not found'}), 404
        else:
            # Check database for recording path
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT recording_path FROM calls 
                    WHERE call_id = %s AND recording_path IS NOT NULL
                    ORDER BY start_time DESC LIMIT 1
                """, (call_id,))
                result = cursor.fetchone()
                
                if result and result['recording_path']:
                    recording_path = result['recording_path']
                    
                    if os.path.exists(recording_path):
                        file_size = os.path.getsize(recording_path)
                        # Estimate duration based on file size and audio format
                        estimated_duration = file_size / 88200
                        
                        return jsonify({
                            'success': True,
                            'file_size': file_size,
                            'duration': estimated_duration,
                            'file_path': recording_path,
                            'format': 'WAV',
                            'sample_rate': 44100,
                            'channels': 1
                        })
                    else:
                        return jsonify({'error': 'Recording file not found'}), 404
                else:
                    return jsonify({'error': 'No recording found for this call'}), 404
                    
    except Exception as e:
        logger.error(f"Error getting recording info for call {call_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/incident-categories', methods=['GET'])
def get_incident_categories():
    """Get all incident categories"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM incident_categories ORDER BY name")
            categories = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'categories': categories
            })
            
    except Exception as e:
        logger.error(f"Error getting incident categories: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/incident-categories/<int:category_id>', methods=['GET'])
def get_incident_category(category_id):
    """Get a specific incident category by ID"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM incident_categories WHERE id = %s", (category_id,))
            category = cursor.fetchone()
            
            if category:
                return jsonify({
                    'success': True,
                    'category': {
                        'id': category['id'],
                        'name': category['name'],
                        'description': category['description'],
                        'priority': category['priority_level'],
                        'response_time': f"{category['response_time_minutes']} minutes"
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Category not found'
                }), 404
            
    except Exception as e:
        logger.error(f"Error getting incident category: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/asterisk/incoming', methods=['POST'])
def asterisk_incoming():
    """Handle incoming calls from Asterisk AGI"""
    try:
        # Get call details from Asterisk
        caller_id = request.form.get('callerid', 'Unknown')
        extension = request.form.get('extension', '100')
        unique_id = request.form.get('uniqueid', str(uuid.uuid4()))
        
        # Create a new call record
        call_id = f"asterisk_{unique_id}"
        
        # Log the incoming call
        logger.info(f"Incoming call from Asterisk: {caller_id} -> {extension} (ID: {call_id})")
        
        # Store call in database
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (call_id, caller_id, caller_id, 'ringing', 'incoming', datetime.now()))
                connection.commit()
        except Exception as e:
            logger.error(f"Error storing call in database: {e}")
        finally:
            if connection:
                connection.close()
        
        # Return AGI response to Asterisk
        response = f"""200 result=1
AGIEnv: {caller_id}
AGIEnv: {extension}
AGIEnv: {call_id}
"""
        return response, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error handling Asterisk incoming call: {e}")
        return "500 Error", 500

@app.route('/asterisk/status', methods=['POST'])
def asterisk_status():
    """Handle call status updates from Asterisk"""
    try:
        call_id = request.form.get('call_id')
        status = request.form.get('status')  # answered, ended, etc.
        
        if call_id and status:
            # Update call status in database
            try:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    if status == 'answered':
                        cursor.execute("""
                            UPDATE calls SET status = %s, answered_time = %s 
                            WHERE call_id = %s
                        """, (status, datetime.now(), call_id))
                    elif status in ['ended', 'missed']:
                        cursor.execute("""
                            UPDATE calls SET status = %s, end_time = %s 
                            WHERE call_id = %s
                        """, (status, datetime.now(), call_id))
                    else:
                        cursor.execute("""
                            UPDATE calls SET status = %s WHERE call_id = %s
                        """, (status, call_id))
                    connection.commit()
            except Exception as e:
                logger.error(f"Error updating call status: {e}")
            finally:
                if connection:
                    connection.close()
            
            logger.info(f"Call {call_id} status updated to: {status}")
        
        return "200 OK", 200
        
    except Exception as e:
        logger.error(f"Error handling Asterisk status update: {e}")
        return "500 Error", 500

@app.route('/asterisk/extension1412', methods=['POST'])
def asterisk_extension_1412():
    """Handle calls to extension 1412 - Flask VOIP System"""
    try:
        # Handle both AGI and regular POST requests
        if request.content_type and 'text/plain' in request.content_type:
            # AGI request - parse the raw data
            agi_data = request.get_data(as_text=True)
            logger.info(f"AGI request received: {agi_data}")
            
            # Parse AGI environment variables
            agi_vars = {}
            for line in agi_data.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    agi_vars[key.strip()] = value.strip()
            
            caller_id = agi_vars.get('agi_callerid', 'Unknown')
            extension = agi_vars.get('agi_extension', '1412')
            unique_id = agi_vars.get('agi_uniqueid', str(uuid.uuid4()))
            channel = agi_vars.get('agi_channel', '')
        else:
            # Regular POST request
            caller_id = request.form.get('callerid', 'Unknown')
            extension = request.form.get('extension', '1412')
            unique_id = request.form.get('uniqueid', str(uuid.uuid4()))
            channel = request.form.get('channel', '')
        
        # Create a new call record
        call_id = f"asterisk_1412_{unique_id}"
        
        # Log the incoming call to extension 1412
        logger.info(f"Incoming call to extension 1412: {caller_id} -> {extension} (ID: {call_id})")
        
        # Store call in database
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time, extension)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (call_id, caller_id, caller_id, 'ringing', 'incoming', datetime.now(), extension))
                connection.commit()
        except Exception as e:
            logger.error(f"Error storing call in database: {e}")
        finally:
            if connection:
                connection.close()
        
        # Emit socket event for real-time call notification
        socketio.emit('incoming_call_1412', {
            'call_id': call_id,
            'caller_id': caller_id,
            'extension': extension,
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        })
        
        # Return AGI response to Asterisk with instructions
        response = f"""200 result=1
AGIEnv: {caller_id}
AGIEnv: {extension}
AGIEnv: {call_id}
AGIEnv: {channel}
"""
        return response, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error handling extension 1412 call: {e}")
        return "500 Error", 500

@app.route('/asterisk/answer_call', methods=['POST'])
def asterisk_answer_call():
    """Answer a call using AMI"""
    try:
        call_id = request.form.get('call_id')
        channel = request.form.get('channel')
        
        if not channel:
            return jsonify({'success': False, 'error': 'Channel required'}), 400
        
        # Answer the call using AMI
        result = ami.send_action('SetVar', {
            'Channel': channel,
            'Variable': 'ANSWERED',
            'Value': '1'
        })
        
        if result and 'Success' in result:
            # Update call status in database
            try:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE calls SET status = %s, answered_time = %s 
                        WHERE call_id = %s
                    """, ('answered', datetime.now(), call_id))
                    connection.commit()
            except Exception as e:
                logger.error(f"Error updating call status: {e}")
            finally:
                if connection:
                    connection.close()
            
            logger.info(f"Call {call_id} answered successfully")
            return jsonify({'success': True, 'message': 'Call answered'})
        else:
            logger.error(f"Failed to answer call {call_id}")
            return jsonify({'success': False, 'error': 'Failed to answer call'}), 500
            
    except Exception as e:
        logger.error(f"Error answering call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/asterisk/hangup_call', methods=['POST'])
def asterisk_hangup_call():
    """Hangup a call using AMI"""
    try:
        call_id = request.form.get('call_id')
        channel = request.form.get('channel')
        
        if not channel:
            return jsonify({'success': False, 'error': 'Channel required'}), 400
        
        # Hangup the call using AMI
        result = ami.hangup_channel(channel)
        
        if result and 'Success' in result:
            # Update call status in database
            try:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE calls SET status = %s, end_time = %s 
                            WHERE call_id = %s
                    """, ('ended', datetime.now(), call_id))
                    connection.commit()
            except Exception as e:
                logger.error(f"Error updating call status: {e}")
            finally:
                if connection:
                    connection.close()
            
            logger.info(f"Call {call_id} hung up successfully")
            return jsonify({'success': True, 'message': 'Call hung up'})
        else:
            logger.error(f"Failed to hangup call {call_id}")
            return jsonify({'success': False, 'error': 'Failed to hangup call'}), 500
            
    except Exception as e:
        logger.error(f"Error hanging up call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/extension1412')
@login_required
def extension_1412_page():
    """Page for managing extension 1412 calls"""
    return render_template('extension1412.html')

@app.route('/test-agi-call', methods=['POST'])
def test_agi_call():
    """Test endpoint to simulate an AGI call for testing purposes"""
    try:
        # Generate test call data
        import uuid
        test_call_id = f"test_agi_{uuid.uuid4().hex[:8]}"
        test_caller_id = f"555-TEST-{uuid.uuid4().hex[:4]}"
        test_caller_name = f"Test Caller {uuid.uuid4().hex[:4]}"
        
        # Create call data similar to what AGI server would send
        call_data = {
            'call_id': test_call_id,
            'caller_id': test_caller_id,
            'caller_name': test_caller_name,
            'extension': '1412',
            'channel': 'SIP/test-123',
            'timestamp': datetime.now().isoformat(),
            'source': 'ami',
            'status': 'ringing',
            'display_status': 'incoming'
        }
        
        # Store in database
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO calls (call_id, caller_id, caller_name, status, direction, start_time, extension, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (test_call_id, test_caller_id, test_caller_name, 'ringing', 'incoming', datetime.now(), '1412', 'ami'))
                connection.commit()
        except Exception as e:
            logger.error(f"Error storing test call in database: {e}")
        finally:
            if connection:
                connection.close()
        
        # Emit WebSocket event
        socketio.emit('incoming_call_1412', call_data)
        
        logger.info(f"Test AGI call created: {test_call_id}")
        return jsonify({
            'success': True, 
            'message': 'Test AGI call created successfully',
            'call_data': call_data
        })
        
    except Exception as e:
        logger.error(f"Error creating test AGI call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize AGI server
agi_server = AGIServer(host='0.0.0.0', port=5001, logger=logger, socketio_instance=socketio)

# Initialize application
def init_app():
    """Initialize the application"""
    try:
        # Initialize database
        init_database()
        
        # Initialize default data
        init_default_data()
        
        # Initialize SIP service
        try:
            sip_service.initialize()
        except Exception as e:
            logger.warning(f"SIP service initialization failed: {e}")
        
        # Start AGI server
        try:
            logger.info("Attempting to start AGI server...")
            if agi_server.start():
                logger.info("AGI server started successfully")
                logger.info(f"AGI server listening on {agi_server.host}:{agi_server.port}")
            else:
                logger.error("Failed to start AGI server")
        except Exception as e:
            logger.error(f"AGI server initialization failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

if __name__ == '__main__':
    init_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 