# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY . .

# Ensure stdout and stderr are unbuffered
ENV PYTHONUNBUFFERED=1

# Set the default command to run the bot
CMD ["python", "-m", "inn_check_bot"]
