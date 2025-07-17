# Use official Python base image
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libgeos-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port Render will use
EXPOSE 8080

# Start Dash via Gunicorn
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8080"]
