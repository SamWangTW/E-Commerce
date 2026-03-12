import json
import pymysql
import decimal
import os

def default_converter(o):
    if isinstance(o, decimal.Decimal):
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def lambda_handler(event, context):
    """
    Lambda function to return all available items in the inventory from MySQL,
    ensuring all column names are lowercase.
    """

    db_host = os.environ['DB_HOST']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_name = os.environ['DB_NAME']

    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ID, ITEM_NUMBER, NAME, DESCRIPTION, IMAGE, AVAILABLE_QUANTITY, UNIT_PRICE 
                FROM ITEM;
            """)
            items = cursor.fetchall()

            # Convert column names to lowercase
            items = [{k.lower(): v for k, v in row.items()} for row in items]

    finally:
        connection.close()

    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(items, default=default_converter)
    }

    return response
