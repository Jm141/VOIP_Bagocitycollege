# 🚀 Render Deployment Guide for Flask VOIP System

## Overview
This guide will help you deploy your Flask VOIP system to Render, making it accessible from anywhere and solving the network connectivity issues with Asterisk.

## ✅ What This Deployment Will Solve

1. **Network Connectivity**: Your Flask app will be accessible from anywhere via public URL
2. **Asterisk Integration**: Asterisk can now reach your Flask app without network restrictions
3. **Professional Hosting**: Reliable, scalable infrastructure on Render
4. **Cost-Effective**: Free tier available for development and testing

## 📋 Prerequisites

1. **GitHub Account**: To host your code
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Code Ready**: Your Flask app should be working locally

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Code

1. **Update your extensions.conf** (Already done):
   ```conf
   exten => 1412,n,AGI(http://YOUR_RENDER_URL/asterisk/extension1412)
   ```

2. **Use the production app**: `app_production.py` instead of `app_direct_mysql.py`

3. **Use production requirements**: `requirements_production.txt`

### Step 2: Push to GitHub

1. **Initialize Git** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Render deployment"
   ```

2. **Create GitHub repository** and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git branch -M main
   git push -u origin main
   ```

### Step 3: Deploy on Render

1. **Sign in to Render** and click "New +"

2. **Select "Web Service"**

3. **Connect your GitHub repository**

4. **Configure the service**:
   - **Name**: `voip-system`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements_production.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 app_production:app --bind 0.0.0.0:$PORT`

5. **Add Environment Variables**:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key-here
   ASTERISK_AMI_HOST=10.198.215.71
   ASTERISK_AMI_PORT=5038
   ASTERISK_AMI_USERNAME=admin
   ASTERISK_AMI_SECRET=admin
   ```

6. **Click "Create Web Service"**

### Step 4: Set Up Database

1. **Create PostgreSQL Database** on Render:
   - Click "New +" → "PostgreSQL"
   - Name: `voip-db`
   - Plan: Free
   - Click "Create Database"

2. **Copy Database URL** and add to environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

### Step 5: Update Asterisk Configuration

1. **Get your Render URL** (e.g., `https://voip-system.onrender.com`)

2. **Update extensions.conf**:
   ```conf
   exten => 1412,n,AGI(http://voip-system.onrender.com/asterisk/extension1412)
   ```

3. **Reload Asterisk dialplan**:
   ```
   dialplan reload
   ```

## 🔧 Configuration Files

### render.yaml (Auto-deployment)
```yaml
services:
  - type: web
    name: voip-system
    env: python
    plan: free
    buildCommand: pip install -r requirements_production.txt
    startCommand: gunicorn --worker-class eventlet -w 1 app_production:app --bind 0.0.0.0:$PORT
    envVars:
      - key: FLASK_ENV
        value: production
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

databases:
  - name: voip-db
    databaseName: voip_system
    user: voip_user
    plan: free
```

### app_production.py
- Production-ready Flask app
- Supports both MySQL and PostgreSQL
- Environment-based configuration
- Health check endpoints

## 🧪 Testing Your Deployment

1. **Health Check**: Visit `https://YOUR_APP.onrender.com/health`

2. **Test Call**: Call extension 1412 from your softphone

3. **Monitor Logs**: Check Render logs for any errors

4. **Database**: Verify calls are being stored

## 🔍 Troubleshooting

### Common Issues:

1. **Build Failures**:
   - Check `requirements_production.txt`
   - Ensure all dependencies are compatible

2. **Database Connection**:
   - Verify `DATABASE_URL` environment variable
   - Check database is running

3. **Asterisk Connection**:
   - Verify Render URL is accessible
   - Check firewall settings

4. **WebSocket Issues**:
   - Ensure `eventlet` worker is used
   - Check CORS settings

### Debug Commands:

```bash
# Check Render logs
render logs voip-system

# Test database connection
curl https://YOUR_APP.onrender.com/health

# Test AGI endpoint
curl -X POST https://YOUR_APP.onrender.com/asterisk/extension1412 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "callerid=1234567890&extension=1412"
```

## 📊 Monitoring & Scaling

1. **Free Tier Limits**:
   - 750 hours/month
   - Sleeps after 15 minutes of inactivity
   - 512 MB RAM, 0.1 CPU

2. **Upgrade Options**:
   - Starter: $7/month (always on, 512 MB RAM)
   - Standard: $25/month (1 GB RAM, 0.5 CPU)

3. **Custom Domain**: Add your own domain name

## 🎯 Benefits After Deployment

1. **Global Access**: Your VOIP system accessible from anywhere
2. **No Network Issues**: Asterisk can reach your Flask app
3. **Professional Hosting**: Reliable infrastructure
4. **Easy Scaling**: Upgrade resources as needed
5. **SSL Certificate**: Automatic HTTPS
6. **CDN**: Global content delivery

## 🚀 Next Steps

1. **Deploy to Render** using this guide
2. **Test the integration** with Asterisk
3. **Monitor performance** and logs
4. **Scale up** if needed
5. **Add custom domain** for production use

## 📞 Support

- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **Render Community**: [community.render.com](https://community.render.com)
- **GitHub Issues**: For code-related problems

---

**Happy Deploying! 🎉**
