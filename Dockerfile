FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install dependencies using uv
RUN uv sync

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "python", "main.py"] 