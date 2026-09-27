import os

import psycopg
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        application=os.environ["APP_NAME"],
        domain=os.environ["DOMAIN"],
        status="ok",
    )


@app.get("/health/database")
def database_health():
    try:
        with psycopg.connect(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            connect_timeout=3,
        ):
            return jsonify(database=os.environ["DB_NAME"], status="ok")
    except Exception as error:
        return jsonify(database="error", detail=str(error), status="error"), 503
