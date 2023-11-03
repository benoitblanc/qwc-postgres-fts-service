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
        self.resources = self.load_resources()
        self.db_engine = DatabaseEngine()

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
                WHERE ts @@ to_tsquery('{text_search_config}', '{search_string}')
                GROUP BY "{primary_key}"
                ORDER BY ts_rank(ts, to_tsquery('{text_search_config}', '{search_string}')) DESC
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
            conn = self.db_engine.db_engine(document["db_url"]).connect()
            results[key] = []
            try:
                result = conn.execute(sql)
                for row in result:
                    row_result = self._feature_from_query(row, document["primary_key"])
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
        for attr in row._mapping:
            value = row[attr]
            if attr == "json_geom":
                geom = json.loads(value)
            elif attr == "bbox":
                bbox = self.parse_box2d(value)
            elif attr == primary_key:
                # Ensure UUID primary key is JSON serializable
                pk = str(value)
            elif isinstance(value, date):
                result[attr] = value.isoformat()
            elif isinstance(value, Decimal):
                result[attr] = float(value)
            elif isinstance(value, UUID):
                result[attr] = str(value)
            else:
                result[attr] = value

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
