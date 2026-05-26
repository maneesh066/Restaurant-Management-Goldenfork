# Use the official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Expose port 8000 for the app
EXPOSE 8000

# Run the Django application using Gunicorn bound to 0.0.0.0:8000
CMD python manage.py migrate && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 goldenfork.wsgi:application
