# 🚀 Installation Guide

## Prerequisites

- Python 3.9 or higher
- pip package manager
- (Optional) Docker for Redis
- (Optional) CUDA-capable GPU for faster ML inference

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd policygenie-pro
```

### 2. Create Virtual Environment

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** Installation may take 10-15 minutes due to large ML models.

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- **OPENAI_API_KEY** (required)
- **ANTHROPIC_API_KEY** (optional)

### 5. Create Data Directories

```bash
mkdir -p data/{uploads,processed,chroma_db,faiss_index}
```

### 6. (Optional) Start Redis for Caching

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis redis:latest

# Or install Redis natively
```

### 7. Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000

### 8. Start the Streamlit UI (New Terminal)

```bash
# Activate venv first
source venv/bin/activate  # or venv\Scripts\activate on Windows

streamlit run streamlit_app.py
```

UI will be available at: http://localhost:8501

## Verification

### Test API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123,
  "cache": {...},
  "services": {
    "api": "operational",
    "llm": "operational",
    "vector_db": "operational",
    "cache": "operational"
  }
}
```

### Test API Documentation

Visit http://localhost:8000/docs for interactive API documentation

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution:** Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: CUDA out of memory

**Solution:** Reduce batch size or disable GPU
```python
# In fraud_service.py and risk_service.py
self.device = "cpu"  # Force CPU usage
```

### Issue: Redis connection failed

**Solution:** Redis is optional. System will use in-memory cache if Redis unavailable.

### Issue: File upload fails

**Solution:** Check file size (<10MB) and format (PDF only)

## Production Deployment

### Using Docker

```bash
# Build image
docker build -t policygenie-ai .

# Run container
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  policygenie-ai
```

### Using Gunicorn

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Environment Variables for Production

```env
# Set in production
SECRET_KEY=<generate-strong-key>
LOG_LEVEL=WARNING
ENABLE_CACHING=true
REDIS_HOST=<redis-hostname>
```

## Next Steps

1. Upload sample policy documents
2. Test risk assessment with demo data
3. Explore API documentation
4. Review architecture docs
5. Run example scenarios

## Support

For issues:
- Check logs in console
- Review API error responses
- Contact support team
