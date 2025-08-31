#!/usr/bin/env python3
"""
Production-ready Flask VOIP System for Render deployment
Supports both local MySQL and remote PostgreSQL databases
"""

import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime, timedelta
import threading
import time
import base64
from io import BytesIO
import subprocess
import uuid
import json

# Database imports
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - supports both local and remote
def get_database_config():
    """Get database configuration based on environment"""
    if os.getenv('DATABASE_URL'):
        # Render PostgreSQL
        return {
            'type': 'postgresql',
            'url': os.getenv('DATABASE_URL')
        }
    else:
        # Local MySQL
        return {
            'type': 'mysql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', '1412'),
            'database': os.getenv('DB_NAME', 'resource_allocation'),
            'charset': 'utf8mb4'
        }

# Database connection function
def get_db_connection():
    """Get database connection based on configuration"""
    config = get_database_config()
    
    try:
        if config['type'] == 'postgresql':
            if not POSTGRES_AVAILABLE:
                raise Exception("PostgreSQL driver not available")
            
            connection = psycopg2.connect(
                config['url'],
                cursor_factory=RealDictCursor
            )
            return connection
            
        elif config['type'] == 'mysql':
            if not MYSQL_AVAILABLE:
                raise Exception("MySQL driver not available")
            
            connection = pymysql.connect(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                charset=config['charset'],
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
            
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Asterisk Manager Interface (AMI) integration
class AsteriskAMI:
    def __init__(self):
        self.host = os.getenv('ASTERISK_AMI_HOST', '127.0.0.1')
        self.port = int(os.getenv('ASTERISK_AMI_PORT', '5038'))
        self.username = os.getenv('ASTERISK_AMI_USERNAME', 'admin')
        self.secret = os.getenv('ASTERISK_AMI_SECRET', 'admin')
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

# Initialize AMI
ami = AsteriskAMI()

# Database initialization
def init_database():
    """Initialize database tables"""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Create calls table if it doesn't exist
            if get_database_config()['type'] == 'postgresql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS calls (
                        id SERIAL PRIMARY KEY,
                        call_id VARCHAR(50) UNIQUE NOT NULL,
                        caller_id VARCHAR(20) NOT NULL,
                        caller_name VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'ringing',
                        direction VARCHAR(20) DEFAULT 'inbound',
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        duration INTEGER,
                        user_id INTEGER,
                        sip_channel VARCHAR(100),
                        recording_path VARCHAR(255),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create users table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        full_name VARCHAR(100),
                        role VARCHAR(20) DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                # MySQL version
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
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            
            connection.commit()
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        if connection:
            connection.close()

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('dashboard.html')

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

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    try:
        # Test database connection
        connection = get_db_connection()
        connection.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Initialize database on startup
@app.before_first_request
def setup():
    """Setup function called before first request"""
    try:
        init_database()
        logger.info("Application setup completed")
    except Exception as e:
        logger.error(f"Application setup failed: {e}")

if __name__ == '__main__':
    # For local development
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
else:
    # For production (Render)
    init_database()
