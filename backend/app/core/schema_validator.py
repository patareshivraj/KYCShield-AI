import json
import os
from jsonschema import validate
from fastapi.encoders import jsonable_encoder

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "docs", "schemas", "v1")

class SchemaValidator:
    @staticmethod
    def _load_schema(schema_name: str):
        path = os.path.join(SCHEMA_DIR, f"{schema_name}.schema.json")
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def validate_response(schema_name: str, data: dict):
        schema = SchemaValidator._load_schema(schema_name)
        # Using fastAPI encoder to ensure datetime objects are strings, etc.
        data_encoded = jsonable_encoder(data)
        validate(instance=data_encoded, schema=schema)
        return data_encoded
