import json
import pymysql
from urllib.parse import unquote_plus
import os
from decimal import Decimal

# Database config (use environment variables in production)
DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME = os.environ["DB_NAME"]

# Custom JSON encoder that converts Decimal to float
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    qs = event.get("queryStringParameters") or {}
    name = qs.get("name")

    if not name:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": "Missing required query parameter: name"})
        }

    needle = unquote_plus(name).strip().lower()

    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            query = "SELECT id, item_number, name, description, available_quantity, unit_price FROM ITEM WHERE LOWER(name) LIKE %s"
            cursor.execute(query, (f"%{needle}%",))
            results = cursor.fetchall()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(results, cls=DecimalEncoder)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": str(e)})
        }

    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
