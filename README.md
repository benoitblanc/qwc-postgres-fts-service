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

Install dependencies and run service:

    uv run src/server.py

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/volumes/config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

With config path:

    CONFIG_PATH=/PATH/TO/CONFIGS/ uv run src/server.py

Testing
-------

Run all tests:

    uv run src/test.py
