# Dockerfile for your FastAPI app
FROM python:3.10-slim

WORKDIR /app

# --- FIX: Remove proxy variables that break Groq client ---
ENV HTTP_PROXY=
ENV HTTPS_PROXY=
ENV http_proxy=
ENV https_proxy=

# copy and install dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of your app
COPY . .

# Do not expose secrets; .env should NOT be committed to public repo
EXPOSE 8000

# Start the app using uvicorn (FastAPI)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
