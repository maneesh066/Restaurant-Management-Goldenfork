web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn goldenfork.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4
