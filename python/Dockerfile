# Use official Python image (Debian-based) instead of Alpine
FROM python:3.9-slim

WORKDIR /app

# Copy application files
COPY . .

# Ensure pip is installed (only needed if base image is minimal)
RUN apt-get update && apt-get install -y python3-pip && pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set up user and permissions
RUN addgroup --system mercari && adduser --system trainee --ingroup mercari
RUN chown -R trainee:mercari /app

USER trainee

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload", "--port", "9000"]
