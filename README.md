# Northshore Books — Setup & Usage

This README explains how to set up and run the Northshore Books Django project locally.

## Prerequisites

- Python 3.10+ (the project was developed using Python 3.11/3.14)
- MySQL server (or change to SQLite in `config/settings.py` for local testing)
- Node.js & npm (required for Tailwind CSS build)
- Git (optional)

## Install Python dependencies

Create and activate a virtual environment, then install requirements:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Install Node packages for Tailwind

Tailwind assets live under `theme/static_src` — install node deps there:

```bash
cd theme/static_src
npm install
cd ../..
```

## Configuration

This project reads sensitive configuration from environment variables via `python-dotenv` (loaded in `config/settings.py`). A safe workflow:

1. Copy `.env.example` to `.env` and fill in real values (do NOT commit `.env`):

```bash
cp .env.example .env
# edit .env and set SECRET_KEY, DB_PASSWORD, etc.
```

Example variables (already present in `.env.example`):

```
SECRET_KEY=replace-with-a-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.mysql
DB_NAME=northshore_books
DB_USER=root
DB_PASSWORD=your_db_password_here
DB_HOST=127.0.0.1
DB_PORT=3306
```

Notes:
- The project will fall back to sensible defaults when environment variables are not set, but you should always provide a strong `SECRET_KEY` in production.
- `.env` is included in `.gitignore` by default; commit only `.env.example`.
- `DEBUG` is parsed as a boolean (e.g. `True`/`False` or `1`/`0`).
- `ALLOWED_HOSTS` can be a comma-separated list (e.g. `example.com,api.example.com`).

If you don't have `python-dotenv` installed yet, it is listed in `requirements.txt` and can be installed with `pip install -r requirements.txt`.

## Database setup

Run migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

## Running the Tailwind watcher (development)

In one terminal run:

```bash
python manage.py tailwind start
```

This watches and rebuilds CSS during development.

## Running the Django development server

In another terminal run:

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

## Running tests

To run the Django tests for the `books` app:

```bash
python manage.py test books
```

## API Endpoints

- `GET /api/books/` — list books (supports `q`, `author`, `page`, `page_size`)
- `POST /api/books/` — create book (admin only, JSON payload)
- `GET/PUT/PATCH/DELETE /api/books/<id>/` — book detail operations (writes require admin)

Responses use JSON and API supports pagination and filtering.

## Security recommendations

- Set `DEBUG=False` in production and add your hosts to `ALLOWED_HOSTS`.
- Move `SECRET_KEY` and DB credentials to environment variables.
- Enable HTTPS and set `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` in production.
- Consider adding rate-limiting to auth endpoints (login/register) and fail2ban for the server.

## Notes

- Media files are served from the `media/` folder in DEBUG mode (see `config/urls.py`).
- Tailwind integration relies on the `django-tailwind` app; ensure Node and npm are installed.


