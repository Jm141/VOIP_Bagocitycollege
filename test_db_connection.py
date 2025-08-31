#!/usr/bin/env python3
"""
Database Connection Test Script for VOIP System
Tests MySQL connection and verifies table structure
"""

import pymysql
import sys
from datetime import datetime

# Database configuration (same as in app_direct_mysql.py)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1412',
    'database': 'resource_allocation',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def test_connection():
    """Test basic database connection"""
    print("🔌 Testing Database Connection...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✅ Database connection successful!")
        
        # Test basic query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            print(f"📊 MySQL Version: {result['version']}")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_database_exists():
    """Test if the voip database exists"""
    print("\n🗄️ Testing Database Existence...")
    try:
        # Connect without specifying database
        config_without_db = DB_CONFIG.copy()
        del config_without_db['database']
        
        connection = pymysql.connect(**config_without_db)
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE 'resource_allocation'")
            result = cursor.fetchone()
            
            if result:
                print("✅ resource_allocation database exists")
            else:
                print("❌ resource_allocation database does not exist")
                print("💡 Creating resource_allocation database...")
                cursor.execute("CREATE DATABASE IF NOT EXISTS resource_allocation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print("✅ resource_allocation database created successfully")
                
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def test_tables():
    """Test if all required tables exist"""
    print("\n📋 Testing Table Structure...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get list of all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"   - {table_name}")
            
            # Check specific required tables
            required_tables = [
                'calls', 'forwarding_rules', 'incidents', 'incident_categories',
                'call_recordings', 'call_statistics', 'system_logs', 'sip_channels'
            ]
            
            print(f"\n🔍 Checking required tables:")
            for table in required_tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                result = cursor.fetchone()
                if result:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} - MISSING")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing tables: {e}")
        return False

def test_table_structure():
    """Test the structure of key tables"""
    print("\n🏗️ Testing Table Structure...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            
            # Test calls table structure
            print("\n📞 Calls Table Structure:")
            cursor.execute("DESCRIBE calls")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   {col['Field']:<20} {col['Type']:<20} {col['Null']:<10} {col['Key']:<10}")
            
            # Test incidents table structure
            print("\n🚨 Incidents Table Structure:")
            cursor.execute("DESCRIBE incidents")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   {col['Field']:<20} {col['Type']:<20} {col['Null']:<10} {col['Key']:<10}")
                
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing table structure: {e}")
        return False

def test_data_operations():
    """Test basic data operations"""
    print("\n💾 Testing Data Operations...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            
            # Test insert
            print("   📝 Testing INSERT...")
            test_call_data = {
                'call_id': f'test_{int(datetime.now().timestamp())}',
                'caller_id': '555-TEST',
                'caller_name': 'Test Caller',
                'status': 'test',
                'direction': 'inbound'
            }
            
            cursor.execute("""
                INSERT INTO calls (call_id, caller_id, caller_name, status, direction)
                VALUES (%(call_id)s, %(caller_id)s, %(caller_name)s, %(status)s, %(direction)s)
            """, test_call_data)
            
            # Test select
            print("   🔍 Testing SELECT...")
            cursor.execute("SELECT * FROM calls WHERE call_id = %s", (test_call_data['call_id'],))
            result = cursor.fetchone()
            if result:
                print(f"   ✅ Retrieved test call: {result['caller_name']}")
            else:
                print("   ❌ Failed to retrieve test call")
            
            # Test update
            print("   ✏️ Testing UPDATE...")
            cursor.execute("UPDATE calls SET status = 'completed' WHERE call_id = %s", (test_call_data['call_id'],))
            
            # Test delete
            print("   🗑️ Testing DELETE...")
            cursor.execute("DELETE FROM calls WHERE call_id = %s", (test_call_data['call_id'],))
            
            connection.commit()
            print("   ✅ All data operations successful!")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing data operations: {e}")
        return False

def test_performance():
    """Test database performance with sample queries"""
    print("\n⚡ Testing Database Performance...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            
            # Test simple count query
            start_time = datetime.now()
            cursor.execute("SELECT COUNT(*) as count FROM calls")
            result = cursor.fetchone()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds() * 1000
            print(f"   📊 Calls count: {result['count']} (took {duration:.2f}ms)")
            
            # Test indexed query
            start_time = datetime.now()
            cursor.execute("SELECT * FROM calls ORDER BY start_time DESC LIMIT 10")
            results = cursor.fetchall()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds() * 1000
            print(f"   📋 Latest 10 calls: {len(results)} records (took {duration:.2f}ms)")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing performance: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 VOIP Database Connection Test")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_connection),
        ("Database Existence", test_database_exists),
        ("Table Structure", test_tables),
        ("Table Details", test_table_structure),
        ("Data Operations", test_data_operations),
        ("Performance", test_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database is ready for use.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the database configuration.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 