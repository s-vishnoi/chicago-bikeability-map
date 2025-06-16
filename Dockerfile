# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for Gunicorn
EXPOSE 8000

# Command to run the app using Gunicorn
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8000"]
