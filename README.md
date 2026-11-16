# LendTrack

A lightweight **Customer Success & Loan Collections Dashboard** built with Flask, SQLite and Chart.js.

## Features
- Lender onboarding tracker
- Query/ticket management table
- Collections analytics with bar chart
- Simple, single‑page UI (HTML + Chart.js)
- Sample data included via `init_db.py`

## How to run locally
```bash
# create virtual env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py   # populate sample DB
python app.py       # start server (default http://localhost:5001)
```

## Deploy
Replace the Flask dev server with a production WSGI server (Gunicorn, uWSGI) and configure a reverse proxy.

## License
MIT – feel free to fork and extend.
