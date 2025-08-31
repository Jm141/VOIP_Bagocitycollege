-- VOIP System Database Tables
-- This script creates all necessary tables for the VOIP call management system
-- Excludes the users table as requested

-- Database creation (uncomment if you want to create the database)
-- CREATE DATABASE IF NOT EXISTS voip CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE voip;

-- Calls table - stores all call information
CREATE TABLE IF NOT EXISTS calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    call_id VARCHAR(50) UNIQUE NOT NULL COMMENT 'Unique call identifier',
    caller_id VARCHAR(20) NOT NULL COMMENT 'Phone number of the caller',
    caller_name VARCHAR(100) COMMENT 'Name of the caller',
    status VARCHAR(20) DEFAULT 'ringing' COMMENT 'Call status: ringing, answered, ended, rejected, missed, completed, transferred',
    direction VARCHAR(20) DEFAULT 'inbound' COMMENT 'Call direction: inbound, outbound',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When the call started',
    end_time DATETIME NULL COMMENT 'When the call ended',
    duration INT NULL COMMENT 'Call duration in seconds',
    user_id INT NULL COMMENT 'ID of the user who handled the call',
    sip_channel VARCHAR(100) NULL COMMENT 'SIP channel information',
    recording_path VARCHAR(255) NULL COMMENT 'Path to the recorded audio file',
    notes TEXT NULL COMMENT 'Additional notes about the call',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Record last update timestamp',
    
    INDEX idx_call_id (call_id),
    INDEX idx_caller_id (caller_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_recording_path (recording_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Stores all call information and recordings';

-- Forwarding rules table - manages call forwarding logic
CREATE TABLE IF NOT EXISTS forwarding_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT 'Name of the forwarding rule',
    pattern VARCHAR(50) NOT NULL COMMENT 'Phone number pattern to match',
    priority INT DEFAULT 100 COMMENT 'Rule priority (lower numbers = higher priority)',
    enabled BOOLEAN DEFAULT TRUE COMMENT 'Whether the rule is active',
    forward_to VARCHAR(20) DEFAULT 'mobile_app' COMMENT 'Where to forward calls: mobile_app, voicemail, specific_number',
    forward_to_users TEXT NULL COMMENT 'JSON array of user IDs to forward to',
    schedule_enabled BOOLEAN DEFAULT FALSE COMMENT 'Whether time-based scheduling is enabled',
    schedule_start TIME NULL COMMENT 'Start time for the schedule',
    schedule_end TIME NULL COMMENT 'End time for the schedule',
    schedule_days TEXT NULL COMMENT 'JSON array of days (0=Sunday, 1=Monday, etc.)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Rule creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Rule last update timestamp',
    
    INDEX idx_pattern (pattern),
    INDEX idx_priority (priority),
    INDEX idx_enabled (enabled),
    INDEX idx_schedule_enabled (schedule_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Manages call forwarding rules and schedules';

-- Incidents table - stores incident reports from calls
CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    call_id VARCHAR(255) NOT NULL COMMENT 'ID of the call this incident relates to',
    title VARCHAR(255) NOT NULL COMMENT 'Title of the incident',
    category_id INT NOT NULL COMMENT 'Category ID for the incident type',
    description TEXT NOT NULL COMMENT 'Detailed description of the incident',
    priority VARCHAR(50) NOT NULL COMMENT 'Incident priority: low, medium, high, critical',
    location_name VARCHAR(255) NOT NULL COMMENT 'Human-readable location name',
    latitude DECIMAL(10, 8) NOT NULL COMMENT 'GPS latitude coordinate',
    longitude DECIMAL(11, 8) NOT NULL COMMENT 'GPS longitude coordinate',
    caller_number VARCHAR(50) NULL COMMENT 'Phone number of the caller',
    status VARCHAR(50) DEFAULT 'open' COMMENT 'Incident status: open, in_progress, resolved, closed',
    assigned_to INT NULL COMMENT 'User ID assigned to handle this incident',
    resolution_notes TEXT NULL COMMENT 'Notes about how the incident was resolved',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Incident creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Incident last update timestamp',
    resolved_at DATETIME NULL COMMENT 'When the incident was resolved',
    
    INDEX idx_call_id (call_id),
    INDEX idx_category_id (category_id),
    INDEX idx_priority (priority),
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_created_at (created_at),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Stores incident reports generated from calls';

-- Incident categories table - predefined categories for incidents
CREATE TABLE IF NOT EXISTS incident_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT 'Category name',
    description TEXT NULL COMMENT 'Category description',
    color VARCHAR(7) DEFAULT '#007bff' COMMENT 'Hex color code for UI display',
    icon VARCHAR(50) NULL COMMENT 'FontAwesome icon class',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the category is active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Category creation timestamp',
    
    UNIQUE KEY uk_name (name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Predefined categories for incident classification';

-- Call recordings metadata table - stores detailed recording information
CREATE TABLE IF NOT EXISTS call_recordings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    call_id VARCHAR(50) NOT NULL COMMENT 'ID of the call this recording belongs to',
    file_path VARCHAR(255) NOT NULL COMMENT 'Path to the audio file',
    file_name VARCHAR(255) NOT NULL COMMENT 'Name of the audio file',
    file_size BIGINT NOT NULL COMMENT 'File size in bytes',
    duration DECIMAL(10, 2) NULL COMMENT 'Recording duration in seconds',
    format VARCHAR(20) DEFAULT 'WAV' COMMENT 'Audio format: WAV, MP3, etc.',
    sample_rate INT DEFAULT 44100 COMMENT 'Audio sample rate in Hz',
    channels INT DEFAULT 1 COMMENT 'Number of audio channels',
    bit_depth INT DEFAULT 16 COMMENT 'Audio bit depth',
    quality VARCHAR(20) DEFAULT 'standard' COMMENT 'Audio quality level',
    is_mixed BOOLEAN DEFAULT FALSE COMMENT 'Whether this is a mixed recording (admin + caller)',
    admin_audio_frames INT DEFAULT 0 COMMENT 'Number of admin audio frames recorded',
    caller_audio_frames INT DEFAULT 0 COMMENT 'Number of caller audio frames recorded',
    recording_start DATETIME NULL COMMENT 'When recording started',
    recording_end DATETIME NULL COMMENT 'When recording ended',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Recording creation timestamp',
    
    UNIQUE KEY uk_call_id (call_id),
    INDEX idx_file_path (file_path),
    INDEX idx_duration (duration),
    INDEX idx_is_mixed (is_mixed),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Detailed metadata for call recordings';

-- Call statistics table - stores aggregated call statistics
CREATE TABLE IF NOT EXISTS call_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL COMMENT 'Date for the statistics',
    total_calls INT DEFAULT 0 COMMENT 'Total number of calls for the day',
    answered_calls INT DEFAULT 0 COMMENT 'Number of calls that were answered',
    missed_calls INT DEFAULT 0 COMMENT 'Number of calls that were missed',
    rejected_calls INT DEFAULT 0 COMMENT 'Number of calls that were rejected',
    total_duration INT DEFAULT 0 COMMENT 'Total call duration in seconds',
    avg_duration DECIMAL(10, 2) DEFAULT 0 COMMENT 'Average call duration in seconds',
    recordings_count INT DEFAULT 0 COMMENT 'Number of calls with recordings',
    incidents_count INT DEFAULT 0 COMMENT 'Number of incidents created',
    peak_hour INT NULL COMMENT 'Hour with most calls (0-23)',
    peak_calls INT DEFAULT 0 COMMENT 'Number of calls during peak hour',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Statistics creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Statistics last update timestamp',
    
    UNIQUE KEY uk_date (date),
    INDEX idx_date (date),
    INDEX idx_total_calls (total_calls),
    INDEX idx_peak_hour (peak_hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Daily aggregated call statistics';

-- System logs table - stores system events and activities
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(20) NOT NULL COMMENT 'Log level: INFO, WARNING, ERROR, DEBUG',
    category VARCHAR(50) NOT NULL COMMENT 'Log category: calls, recordings, system, security',
    message TEXT NOT NULL COMMENT 'Log message content',
    details JSON NULL COMMENT 'Additional structured data',
    user_id INT NULL COMMENT 'ID of the user who triggered the event',
    ip_address VARCHAR(45) NULL COMMENT 'IP address of the client',
    user_agent TEXT NULL COMMENT 'User agent string',
    call_id VARCHAR(50) NULL COMMENT 'Related call ID if applicable',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Log entry timestamp',
    
    INDEX idx_level (level),
    INDEX idx_category (category),
    INDEX idx_user_id (user_id),
    INDEX idx_call_id (call_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System activity and error logs';

-- SIP channels table - stores SIP channel information
CREATE TABLE IF NOT EXISTS sip_channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id VARCHAR(100) NOT NULL COMMENT 'SIP channel identifier',
    call_id VARCHAR(50) NULL COMMENT 'Associated call ID',
    channel_name VARCHAR(100) NULL COMMENT 'Human-readable channel name',
    channel_type VARCHAR(50) NULL COMMENT 'Channel type: SIP, IAX, etc.',
    state VARCHAR(50) NULL COMMENT 'Channel state: Down, Ring, Up, Busy',
    caller_id_num VARCHAR(20) NULL COMMENT 'Caller ID number',
    caller_id_name VARCHAR(100) NULL COMMENT 'Caller ID name',
    dialed_number VARCHAR(20) NULL COMMENT 'Number that was dialed',
    context VARCHAR(50) NULL COMMENT 'SIP context',
    extension VARCHAR(20) NULL COMMENT 'SIP extension',
    priority INT DEFAULT 1 COMMENT 'Channel priority',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the channel is currently active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Channel creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Channel last update timestamp',
    
    UNIQUE KEY uk_channel_id (channel_id),
    INDEX idx_call_id (call_id),
    INDEX idx_state (state),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SIP channel information and status';

-- Insert default incident categories
INSERT INTO incident_categories (name, description, color, icon) VALUES
('Medical Emergency', 'Medical emergencies requiring immediate attention', '#dc3545', 'fa-ambulance'),
('Fire Emergency', 'Fire-related emergencies', '#fd7e14', 'fa-fire'),
('Traffic Accident', 'Road traffic accidents and incidents', '#ffc107', 'fa-car-crash'),
('Natural Disaster', 'Natural disasters like floods, earthquakes', '#6f42c1', 'fa-volcano'),
('Public Safety', 'General public safety concerns', '#20c997', 'fa-shield-alt'),
('VOIP System Issue', 'Problems with the VOIP system itself', '#0d6efd', 'fa-phone'),
('Network Problem', 'Network connectivity issues', '#6c757d', 'fa-wifi'),
('Other', 'Miscellaneous incidents not covered by other categories', '#6c757d', 'fa-question-circle')
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    color = VALUES(color),
    icon = VALUES(icon);

-- Insert default forwarding rule
INSERT INTO forwarding_rules (name, pattern, priority, enabled, forward_to, forward_to_users, schedule_enabled, created_at) VALUES
('Default Forwarding', '*', 100, TRUE, 'mobile_app', '[]', FALSE, NOW())
ON DUPLICATE KEY UPDATE
    priority = VALUES(priority),
    enabled = VALUES(enabled),
    forward_to = VALUES(forward_to);

-- Create indexes for better performance
CREATE INDEX idx_calls_composite ON calls(status, start_time, recording_path);
CREATE INDEX idx_incidents_composite ON incidents(status, priority, created_at);
CREATE INDEX idx_recordings_composite ON call_recordings(call_id, file_path, created_at);

-- Add comments to existing tables if they don't have them
ALTER TABLE calls COMMENT = 'Stores all call information and recordings';
ALTER TABLE forwarding_rules COMMENT = 'Manages call forwarding rules and schedules';
ALTER TABLE incidents COMMENT = 'Stores incident reports generated from calls';
ALTER TABLE incident_categories COMMENT = 'Predefined categories for incident classification';
ALTER TABLE call_recordings COMMENT = 'Detailed metadata for call recordings';
ALTER TABLE call_statistics COMMENT = 'Daily aggregated call statistics';
ALTER TABLE system_logs COMMENT = 'System activity and error logs';
ALTER TABLE sip_channels COMMENT = 'SIP channel information and status';

-- Show table creation summary
SELECT 
    TABLE_NAME as 'Table Name',
    TABLE_ROWS as 'Estimated Rows',
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)',
    TABLE_COMMENT as 'Description'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME NOT IN ('users')
ORDER BY TABLE_NAME; 