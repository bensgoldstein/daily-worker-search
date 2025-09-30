# Deployment Guide for Newspaper RAG

This guide covers deploying the Newspaper RAG system for online access.

## Prerequisites

1. **Pinecone Account**: Sign up at https://www.pinecone.io/
2. **OpenAI API Key**: Get from https://platform.openai.com/
3. **Streamlit Cloud Account**: Sign up at https://streamlit.io/cloud
4. **GitHub Repository**: To host your code

## Step 1: Prepare Your Data Locally

1. **Organize your newspaper files**:
   ```bash
   newspapers/
   ├── New_York_Times_1920-05-15_1.txt
   ├── Chicago_Tribune_1945-08-15_12.txt
   └── ...
   ```

2. **Process the files**:
   ```bash
   python process_newspapers.py \
     --input-dir ./newspapers \
     --output-dir ./processed_data \
     --batch-size 100
   ```

3. **Verify the output**:
   - `processed_data/processed_chunks.pkl`
   - `processed_data/bm25_index.pkl`
   - `processed_data/processing_stats.json`

## Step 2: Set Up Pinecone

1. **Create a Pinecone index**:
   - Log into Pinecone console
   - Create new index with:
     - Name: `newspaper-rag`
     - Dimensions: `384`
     - Metric: `cosine`

2. **Note your credentials**:
   - API Key
   - Environment (e.g., `gcp-starter`)

## Step 3: Configure Environment

1. **Create `.env` file** from template:
   ```bash
   cp .env.template .env
   ```

2. **Fill in your credentials**:
   ```env
   PINECONE_API_KEY=your_key_here
   PINECONE_ENVIRONMENT=gcp-starter
   OPENAI_API_KEY=your_openai_key
   ```

## Step 4: Deploy to Streamlit Cloud

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial newspaper RAG system"
   git remote add origin https://github.com/yourusername/newspaper-rag.git
   git push -u origin main
   ```

2. **Configure Streamlit Cloud**:
   - Go to https://streamlit.io/cloud
   - Click "New app"
   - Select your repository
   - Set branch: `main`
   - Set main file path: `app.py`

3. **Add Secrets**:
   In Streamlit Cloud settings, add your secrets:
   ```toml
   PINECONE_API_KEY = "your_key_here"
   PINECONE_ENVIRONMENT = "gcp-starter"
   OPENAI_API_KEY = "your_openai_key"
   ```

4. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete

## Step 5: Test Your Deployment

1. Visit your app URL: `https://yourusername-newspaper-rag-app-xxxxx.streamlit.app`
2. Try searching for historical events or topics
3. Test date filtering

## Alternative Deployment Options

### Option 1: Heroku

1. **Create `Procfile`**:
   ```
   web: streamlit run app.py --server.port $PORT
   ```

2. **Deploy**:
   ```bash
   heroku create newspaper-rag-app
   heroku config:set PINECONE_API_KEY=your_key
   heroku config:set OPENAI_API_KEY=your_key
   git push heroku main
   ```

### Option 2: AWS EC2

1. **Launch EC2 instance** (Ubuntu 20.04+)
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx
   pip3 install -r requirements.txt
   ```

3. **Run with systemd**:
   Create `/etc/systemd/system/newspaper-rag.service`:
   ```ini
   [Unit]
   Description=Newspaper RAG Streamlit App
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/newspaper-rag
   Environment="PATH=/home/ubuntu/.local/bin:/usr/bin"
   ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port 8501
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Configure Nginx** as reverse proxy

## Monitoring and Maintenance

1. **Monitor Pinecone usage** in the console
2. **Set up alerts** for API limits
3. **Regular backups** of BM25 index
4. **Update embeddings** when adding new newspapers

## Troubleshooting

### Common Issues:

1. **"API key not found"**: Check your environment variables
2. **"Index not found"**: Verify Pinecone index name matches config
3. **"Out of memory"**: Reduce batch size in processing
4. **Slow searches**: Check Pinecone index statistics

### Debug Mode:

Set in `.env`:
```env
LOG_LEVEL=DEBUG
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use environment-specific configs**
3. **Implement rate limiting** for public deployments
4. **Regular security updates**
5. **Monitor for suspicious activity**

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review Pinecone documentation
3. Check Streamlit Cloud documentation