import json
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from uuid import UUID

from qwc_services_core.database import DatabaseEngine
from sqlalchemy.sql import text as sql_text


class PostgresFTSClient:
    """PostgresFTSClient class"""

    def __init__(self, tenant, logger, config):
        """Constructor

        :param str tenant: Tenant ID
        :param Logger logger: Application logger
        """
        self.logger = logger
        self.tenant = tenant
        self.config = config
        self.default_search_limit = self.config.get("search_result_limit", 50)
        self.db_engine = DatabaseEngine()
        self.resources = self.load_resources()

    def search(self, searchtext):
        results = OrderedDict()
        for key, document in self.resources.get("documents", []).items():
            self.logger.info(f"Search for document {document['name']}")
            columns = (", ").join(
                self.escape_column_names(
                    [document["primary_key"]] + document["columns"]
                )
            )
            columns += """,
                ST_AsGeoJSON("{geom}") AS json_geom,
                ST_Extent("{geom}") AS bbox
            """.format(
                geom=document.get("geometry_column", "geom")
            )
            sql = sql_text(
                (
                    """
                SELECT {columns}
                FROM "{schema}"."{table}"
                WHERE ts @@ websearch_to_tsquery('{text_search_config}', '{search_string}')
                GROUP BY "{primary_key}"
                ORDER BY ts_rank(ts, websearch_to_tsquery('{text_search_config}', '{search_string}')) DESC
                LIMIT {search_result_limit};
            """
                ).format(
                    columns=columns,
                    schema=document["schema"],
                    table=document["table"],
                    primary_key=document["primary_key"],
                    text_search_config=document.get("text_search_config", "english"),
                    search_string=searchtext,
                    search_result_limit=self.default_search_limit,
                )
            )
            self.logger.debug(f"SQL Query : {sql}")
            results[key] = []
            with self.db_engine.db_engine(document["db_url"]).connect() as conn:
                try:
                    result = conn.execute(sql).mappings()
                    for row in result:
                        row_result = self._feature_from_query(
                            row, document["primary_key"]
                        )
                        results[key].append(row_result)
                    self.logger.debug(f"SQL Result for document {key} : {results[key]}")
                except Exception as e:
                    self.logger.error(f"Error for document {key} on query {sql}: {e}")
        return results

    def _feature_from_query(self, row, primary_key):
        """Build GeoJSON Feature from query result row.

        :param obj row: Row result from query
        """
        result = OrderedDict()
        for key, val in row.items():
            if key == "json_geom":
                geom = json.loads(val)
            elif key == "bbox":
                bbox = self.parse_box2d(val)
            elif key == primary_key:
                # Ensure UUID primary key is JSON serializable
                pk = str(val)
            elif isinstance(val, date):
                result[key] = val.isoformat()
            elif isinstance(val, Decimal):
                result[key] = float(val)
            elif isinstance(val, UUID):
                result[key] = str(val)
            else:
                result[key] = val

        return {
            "type": "Feature",
            "id": pk,
            "geometry": geom,
            "bbox": bbox,
            "properties": result,
        }

    def escape_column_names(self, columns):
        """Return escaped column names by converting them to
        quoted identifiers.

        :param list(str) columns: Column names
        """
        return ['"%s"' % column for column in columns]

    def load_resources(self):
        """Load service resources from config.

        :param RuntimeConfig config: Config handler
        """
        # collect service resources
        documents = {}
        self.logger.debug("Loading documents resources...")
        config_db_url = self.config.get("db_url")
        if config_db_url:
            qwc_config_schema = self.config.get("qwc_config_schema", "qwc_config")
            fts_documents_table = self.config.get(
                "fts_documents_table", "fts_documents"
            )
            sql = sql_text(
                """
                SELECT name, text_search_config, db_url, schema, "table", primary_key, columns, geometry_column
                FROM {table}
            """.format(
                    table=f'"{qwc_config_schema}"."{fts_documents_table}"'
                )
            )
            self.logger.debug(
                f"Query get documents resources from ConfigDB. Query {sql}"
            )
            try:
                with self.db_engine.db_engine(config_db_url).connect() as connection:
                    result = connection.execute(sql).mappings()
                    for row in result:
                        document = {}
                        document["name"] = row.name
                        document["text_search_config"] = row.text_search_config
                        document["db_url"] = row.db_url
                        document["schema"] = row.schema
                        document["table"] = row.table
                        document["primary_key"] = row.primary_key
                        document["columns"] = row.columns
                        document["geometry_column"] = row.geometry_column
                        documents[document["name"]] = document
            except Exception as e:
                self.logger.error(
                    f"Error to get documents resources from ConfigDB. Query {sql}: {e}"
                )
                documents = {}
            self.logger.info(f"Get documents resources from ConfigDB: {documents}")
        else:
            for document in self.config.resources().get("documents", []):
                documents[document["name"]] = document

        return {"documents": documents}

    def parse_box2d(self, box2d):
        """Parse Box2D string and return bounding box
        as [<minx>,<miny>,<maxx>,<maxy>].

        :param str box2d: Box2D string
        """
        bbox = None

        if box2d is None:
            # bounding box is empty
            return None

        # extract coords from Box2D string
        # e.g. "BOX(950598.12 6003950.34,950758.567 6004010.8)"
        # truncate brackets and split into coord pairs
        parts = box2d[4:-1].split(",")
        if len(parts) == 2:
            # split coords, e.g. "950598.12 6003950.34"
            minx, miny = parts[0].split(" ")
            maxx, maxy = parts[1].split(" ")
            bbox = [float(minx), float(miny), float(maxx), float(maxy)]

        return bbox
