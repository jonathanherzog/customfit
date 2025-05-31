web: gunicorn --timeout 20 --chdir src customfit.wsgi:application --workers $WEB_CONCURRENCY
worker: cd src && celery -A customfit worker -B --concurrency 4 --max-memory-per-child 100000 --loglevel=INFO
