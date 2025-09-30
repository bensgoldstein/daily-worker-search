# Deployment Guide - AI-powered Daily Worker Search Database

This guide covers deploying the application securely with authentication and cost controls.

## Authentication Setup

### 1. Generate Password Hash

Never store plaintext passwords! Generate a hash for your shared password:

```bash
python auth.py yourpassword
```

This will output a hash like: `5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8`

### 2. Configure Secrets

Create `.streamlit/secrets.toml` (never commit this file!):

```toml
# Application password (shared by all users)
APP_PASSWORD_HASH = "your_hash_here"

# API Keys
PINECONE_API_KEY = "your_key"
PINECONE_HOST = "your_host"
GEMINI_API_KEY = "your_key"

# Usage limits
MAX_SEARCHES_PER_HOUR = 100
MAX_SEARCHES_PER_DAY = 500
MAX_PDF_DOWNLOADS_PER_DAY = 50
DAILY_COST_LIMIT = 5.0
```

## Deployment Options

### Option 1: Streamlit Community Cloud (Recommended for Starting)

**Cost**: Free for public repos
**Setup Difficulty**: Easy

1. Push code to GitHub (without secrets!)
2. Go to share.streamlit.io
3. Deploy from your GitHub repo
4. Add secrets in Streamlit Cloud dashboard
5. Set app to "private" in settings

**Pros**: 
- Free hosting
- Easy setup
- Built-in secrets management

**Cons**: 
- Limited to 1GB memory
- Must be in public GitHub repo

### Option 2: Google Cloud Run

**Cost**: ~$5-20/month with light usage
**Setup Difficulty**: Medium

1. Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD streamlit run app.py --server.port $PORT
```

2. Deploy:
```bash
gcloud run deploy daily-worker-search \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

3. Set up Google Identity-Aware Proxy for authentication

**Pros**: 
- Scales to zero (no cost when not in use)
- Professional authentication
- Good performance

### Option 3: Heroku

**Cost**: $5-7/month (Eco dyno)
**Setup Difficulty**: Easy

1. Create `Procfile`:
```
web: sh setup.sh && streamlit run app.py
```

2. Create `setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "[server]\nport = $PORT\n" > ~/.streamlit/config.toml
```

3. Deploy:
```bash
heroku create your-app-name
heroku config:set ADMIN_PASSWORD_HASH=your_hash
git push heroku main
```

**Pros**: 
- Simple deployment
- Good for small apps
- Easy to set spending limits

## Cost Control Strategies

### 1. API Rate Limiting

The auth.py module includes basic rate limiting. Additional controls:

- Limit searches per user per hour
- Limit PDF downloads per day
- Monitor Pinecone usage

### 2. Monitoring Setup

Add usage tracking to track costs:

```python
# In app.py, after each search:
if 'daily_searches' not in st.session_state:
    st.session_state.daily_searches = 0
st.session_state.daily_searches += 1

if st.session_state.daily_searches > 100:
    st.error("Daily search limit reached")
    st.stop()
```

### 3. Cost Alerts

- **Pinecone**: Set up usage alerts in dashboard
- **Google Cloud**: Set budget alerts
- **Heroku**: Use Heroku billing alerts

### 4. Password Distribution

Share the password securely:
- Send via secure channel (not email)
- Change password quarterly
- Monitor total usage across all users

## Security Best Practices

1. **Never commit secrets**
   - Add `.streamlit/secrets.toml` to `.gitignore`
   - Use environment variables in production

2. **Use strong passwords**
   - Minimum 12 characters
   - Mix of letters, numbers, symbols

3. **Regular monitoring**
   - Review usage logs weekly
   - Watch for unusual patterns
   - Change password if suspicious activity

4. **Backup configuration**
   - Keep secure backup of password hash
   - Document deployment settings

## Quick Start Deployment

For fastest deployment with good security:

1. Generate a strong password and create hash
2. Deploy to Streamlit Community Cloud
3. Add secrets via dashboard
4. Share password with trusted researchers only
5. Monitor usage daily for first week

## Estimated Costs

With authentication and limited users (5-10 researchers):

- **Hosting**: $0-20/month
- **Pinecone**: $0-10/month (with free tier)
- **Gemini API**: $0-5/month (with limits)
- **Total**: $0-35/month

Without authentication (public access):
- Could easily exceed $100+/month

## Support

For deployment help or access requests, contact:
© 2025 Benjamin Goldstein