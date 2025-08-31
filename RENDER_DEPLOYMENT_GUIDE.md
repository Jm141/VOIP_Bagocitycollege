# Render Deployment Guide for VOIP System

## Overview
This guide covers deploying the VOIP system to Render.com, a cloud platform that supports Python applications.

## Recent Fixes Applied

### 1. Build Dependencies Issue
**Problem**: The build was failing with `Cannot import 'setuptools.build_meta'` error.

**Solution**: 
- Created `requirements_production.txt` with compatible dependencies
- Removed problematic packages that require compilation (`pyaudio`, `numpy`, `pydub`)
- Added essential build tools (`setuptools`, `wheel`)

### 2. Application Selection
**Problem**: `render.yaml` was pointing to `app_direct_mysql.py` which has heavy audio dependencies.

**Solution**: 
- Updated to use `app_production.py` which is designed for production deployment
- This app gracefully handles missing audio libraries

### 3. Python Version Mismatch
**Problem**: `render.yaml` specified Python 3.9.16 but Render was using 3.13.4.

**Solution**: 
- Updated Python version to 3.13.4 in `render.yaml`

## Current Configuration

### render.yaml
```yaml
services:
  - type: web
    name: voip-system
    env: python
    plan: free
    buildCommand: pip install -r requirements_production.txt
    startCommand: gunicorn --worker-class eventlet -w 1 app_production:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.4
      - key: FLASK_ENV
        value: production
      - key: DATABASE_URL
        value: postgresql://voip_user:voip_password@voip-db.internal:5432/voip_system
      - key: SECRET_KEY
        generateValue: true
      - key: ASTERISK_AMI_HOST
        value: 10.198.215.71
      - key: ASTERISK_AMI_PORT
        value: 5038
      - key: ASTERISK_AMI_USERNAME
        value: admin
      - key: ASTERISK_AMI_SECRET
        value: admin
```

### requirements_production.txt
```
Flask==2.3.3
Flask-SocketIO==5.3.6
Flask-Login==0.6.3
PyMySQL==1.1.0
python-socketio==5.8.0
eventlet==0.33.3
setuptools>=65.0.0
wheel>=0.38.0
gunicorn>=21.2.0
psycopg2-binary>=2.9.7
python-dotenv>=1.0.0
```

## Deployment Steps

1. **Commit and Push Changes**
   ```bash
   git add .
   git commit -m "Fix Render deployment issues"
   git push origin main
   ```

2. **Deploy on Render**
   - Connect your GitHub repository to Render
   - Render will automatically detect the `render.yaml` configuration
   - The build should now succeed with the production requirements

3. **Monitor Deployment**
   - Check the build logs for any remaining issues
   - Verify the application starts successfully
   - Test the health check endpoint: `/health`

## What's Different in Production

### Audio Features
- **Local Development**: Full audio recording and playback capabilities
- **Production**: Audio features are gracefully disabled (no errors)

### Database
- **Local Development**: MySQL database
- **Production**: PostgreSQL database (Render's default)

### Dependencies
- **Local Development**: Full feature set with audio libraries
- **Production**: Core functionality without system-dependent audio packages

## Troubleshooting

### Build Still Fails
1. Check that `requirements_production.txt` is being used
2. Verify Python version compatibility
3. Check for any remaining problematic dependencies

### Application Won't Start
1. Check the start command in `render.yaml`
2. Verify `app_production.py` exists and has no syntax errors
3. Check the application logs for runtime errors

### Database Connection Issues
1. Verify the `DATABASE_URL` environment variable
2. Check that the PostgreSQL database is created and accessible
3. Ensure the database user has proper permissions

## Next Steps

After successful deployment:
1. Test the basic functionality (login, dashboard)
2. Verify Asterisk AMI integration works
3. Test call handling to extension 1412
4. Monitor performance and logs

## Support

If you encounter issues:
1. Check the Render deployment logs
2. Verify all configuration files are correct
3. Test locally with the production requirements
4. Check the application logs for runtime errors
