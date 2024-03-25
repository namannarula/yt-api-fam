# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create and switch to a new user
RUN useradd -m myuser
USER myuser

# Collect static files
# RUN python manage.py collectstatic --noinput

# Run Gunicorn
CMD gunicorn --bind 0.0.0.0:5001 app:app
