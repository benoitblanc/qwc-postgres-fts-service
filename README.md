QWC Postgres Fulltext Search Service
====================================

Setup
-----

Configuration
-------------

Usage
-----

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

Base URL:

    http://localhost:5050/

Service API:

    http://localhost:5050/api/

Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 --system-site-packages .venv

Without system packages:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements/requirements.txt

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/volumes/config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

Start local service:

    python server.py

Testing
-------

Run all tests:

    python test.py
