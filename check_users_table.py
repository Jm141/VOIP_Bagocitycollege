#!/usr/bin/env python3
"""
Check Users Table Structure
Examines the users table to see what fields are available
"""

import pymysql

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1412',
    'database': 'resource_allocation',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def check_users_table():
    """Check the structure of the users table"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            
            # Check table structure
            print("🔍 Users Table Structure:")
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   {col['Field']:<20} {col['Type']:<25} {col['Null']:<10} {col['Key']:<10}")
            
            # Check if there are any users
            print(f"\n👥 Checking for existing users:")
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            print(f"   Total users: {result['count']}")
            
            if result['count'] > 0:
                print(f"\n📋 Sample user data (first user):")
                cursor.execute("SELECT * FROM users LIMIT 1")
                user = cursor.fetchone()
                for key, value in user.items():
                    if key == 'password_hash':
                        # Mask password hash for security
                        masked_value = value[:10] + "..." if value and len(value) > 10 else "None"
                        print(f"   {key:<20}: {masked_value}")
                    else:
                        print(f"   {key:<20}: {value}")
            
        connection.close()
        
    except Exception as e:
        print(f"❌ Error checking users table: {e}")

if __name__ == "__main__":
    check_users_table() 