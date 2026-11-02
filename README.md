# Notes Board

A small Flask website for CCEN 448 Lab Exercise 6. Users can register, log in, and keep private notes stored in SQLite.

## Features

- Flask server with session based authentication
- Passwords stored as salted hashes
- SQLite database for accounts and notes
- Each account can view and delete only its own notes
- CSRF tokens on POST forms

## Run on Ubuntu

Install Python, pip, venv, and SQLite. From the project directory run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p data
export SECRET_KEY="replace-with-a-long-random-value"
.venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8080 app:app
```

Open `http://<instance-ip>:8080`. For a persistent service, keep the database directory writable and set a unique `SECRET_KEY` in the service environment. Do not commit secrets or the generated SQLite database.

## Database and authentication versus Exercise 5

This site needs a Python/Flask server to handle routes, verify credentials, manage sessions, and query/update SQLite. It also needs persistent writable storage for the database and a secret key for signed sessions.

Exercise 5 used static S3 website hosting, which serves files such as HTML, CSS, and JavaScript. S3 does not execute Flask/Python code, maintain server-side login sessions, or run a local database. To add those dynamic features to an S3 site, a separate backend plus database and identity services would be required.
