#!/usr/bin/env python3
"""
Deployment helper script for Render deployment
This script helps prepare your code for deployment
"""

import os
import subprocess
import sys
import json

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def check_git_status():
    """Check if git is initialized and has commits"""
    print("🔍 Checking Git status...")
    
    # Check if git is initialized
    if not os.path.exists('.git'):
        print("❌ Git not initialized. Please run: git init")
        return False
    
    # Check if there are commits
    result = run_command("git log --oneline -1", "Checking for commits")
    if not result:
        print("❌ No commits found. Please make at least one commit")
        return False
    
    print("✅ Git repository is ready")
    return True

def check_files_exist():
    """Check if required deployment files exist"""
    print("🔍 Checking deployment files...")
    
    required_files = [
        'app_production.py',
        'requirements_production.txt',
        'render.yaml',
        'templates/',
        'static/'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files exist")
    return True

def create_env_file():
    """Create a .env file template for local testing"""
    print("🔧 Creating .env file template...")
    
    env_content = """# Local development environment variables
# Copy this to .env and fill in your values

# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=1412
DB_NAME=resource_allocation

# Asterisk AMI Configuration
ASTERISK_AMI_HOST=127.0.0.1
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USERNAME=admin
ASTERISK_AMI_SECRET=admin

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production

# For Render deployment, add:
# DATABASE_URL=postgresql://user:password@host:port/database
"""
    
    with open('.env.template', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env.template file")
    print("📝 Edit this file with your local values and rename to .env")

def show_deployment_steps():
    """Show the deployment steps"""
    print("\n🚀 DEPLOYMENT STEPS:")
    print("=" * 50)
    
    steps = [
        "1. Push your code to GitHub:",
        "   git add .",
        "   git commit -m 'Prepare for Render deployment'",
        "   git push origin main",
        "",
        "2. Sign up at render.com",
        "",
        "3. Create a new Web Service:",
        "   - Connect your GitHub repo",
        "   - Use requirements_production.txt",
        "   - Start command: gunicorn --worker-class eventlet -w 1 app_production:app --bind 0.0.0.0:$PORT",
        "",
        "4. Create PostgreSQL database on Render",
        "",
        "5. Add environment variables:",
        "   - DATABASE_URL (from PostgreSQL)",
        "   - SECRET_KEY (auto-generated)",
        "   - ASTERISK_AMI_* variables",
        "",
        "6. Update your extensions.conf with the Render URL",
        "",
        "7. Test the deployment!"
    ]
    
    for step in steps:
        print(step)

def main():
    """Main deployment helper function"""
    print("🚀 Flask VOIP System - Render Deployment Helper")
    print("=" * 50)
    
    # Check prerequisites
    if not check_git_status():
        print("\n❌ Please fix Git issues before proceeding")
        return
    
    if not check_files_exist():
        print("\n❌ Please create missing files before proceeding")
        return
    
    # Create environment file template
    create_env_file()
    
    # Show deployment steps
    show_deployment_steps()
    
    print("\n🎯 Ready to deploy!")
    print("📚 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions")
    print("🔗 Visit: https://render.com to get started")

if __name__ == "__main__":
    main()
