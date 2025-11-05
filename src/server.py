import logging

from flask import Flask, jsonify, request
from flask_restx import Api, Resource
from qwc_services_core.auth import auth_manager, optional_auth
from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.tenant_handler import TenantHandler

from search_service import PostgresFTSClient

# Flask application
app = Flask(__name__)
api = Api(
    app,
    version="1.0",
    title="Postgres Fulltext Search API",
    description="API for QWC Postgres Fulltext Search service",
    default_label="Postgres Fulltext Search operations",
    doc="/api/",
)

auth = auth_manager(app, api)

# create tenant handler
tenant_handler = TenantHandler(app.logger)

logging.getLogger().setLevel(logging.DEBUG if app.debug else logging.INFO)


def search_handler():
    """Get or create a SearchService instance for a tenant."""
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler("postgresFts", "postgresfts", tenant)
    if handler is None:
        config_handler = RuntimeConfig("postgresFts", app.logger)
        config = config_handler.tenant_config(tenant)
        handler = tenant_handler.register_handler(
            "postgresfts", tenant, PostgresFTSClient(tenant, app.logger, config)
        )
    return handler


@api.route("/search/", "/")
class SearchResult(Resource):
    @api.doc("search")
    @api.param("searchtext", "Search string")
    @optional_auth
    def get(self):
        """Search for searchtext and return the results"""
        searchtext = request.args.get("searchtext")
        if not searchtext:
            return {"error": "Missing search string"}

        handler = search_handler()
        result = handler.search(searchtext)

        return result


@app.route("/ready", methods=["GET"])
def ready():
    """readyness probe endpoint"""
    return jsonify({"status": "OK"})


@app.route("/healthz", methods=["GET"])
def healthz():
    """liveness probe endpoint"""
    return jsonify({"status": "OK"})


# local webserver
if __name__ == "__main__":
    print("Starting Postgres Fulltext Search service...")
    app.run(host="localhost", port=5050, debug=True)
