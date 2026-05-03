FROM python:3.11-slim

# Install system requirements for Postgres and ML libs
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start Gunicorn on Hugging Face's port 7860
CMD python manage.py migrate && gunicorn startup_predictor.wsgi:application --bind 0.0.0.0:7860