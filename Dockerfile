FROM python:3.12-slim

# Avoid writing .pyc files and buffer outputs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs with user ID 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

# Ensure directories exist and are owned by user 1000
RUN mkdir -p /app/data/pdfs /app/data/faiss_index && chown -R user:user /app

# Copy requirements and install
COPY --chown=user:user backend/requirements.txt /app/requirements.txt

USER user

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application files directly into /app
COPY --chown=user:user backend/ /app/

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
