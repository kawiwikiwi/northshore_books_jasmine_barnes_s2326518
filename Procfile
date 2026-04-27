web: gunicorn config.wsgi:application
release: python manage.py migrate
release: python manage.py migrate && python manage.py tailwind build