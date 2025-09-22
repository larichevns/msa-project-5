FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY job_client.py .

# Create logs directory
RUN mkdir -p /app/logs

# Run the client
CMD ["python", "job_client.py"]