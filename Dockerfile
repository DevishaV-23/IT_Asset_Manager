# Use the same Python version as render.yaml
FROM python:3.11.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2 (Postgres)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make sure the start script is executable
RUN chmod +x start.sh

# Expose the port Flask runs on
EXPOSE 5000

# Start the application
CMD ["./start.sh"]