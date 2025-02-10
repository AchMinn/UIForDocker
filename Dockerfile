# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

# Create directories for templates and static files
RUN mkdir -p templates static

# Expose port 5000
EXPOSE 5000

# Mount Docker socket
VOLUME /run/docker.sock

# Run the application
CMD ["python", "app.py"]