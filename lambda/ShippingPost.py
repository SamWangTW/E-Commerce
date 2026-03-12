import json
import uuid
import pymysql
import os
from datetime import datetime

# connect to RDS
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']

def lambda_handler(event, context):
    try:
        # parse EventBridge event
        detail = event['detail']
        business_id = detail['business_id']
        address = detail['shipping_address']
        items = detail.get('items', [])

        packet_count = len(items)
        packet_weight = 1.0

        # generate shipping token
        shipping_token = str(uuid.uuid1())

        # connect to MySQL
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO SHIPPING_INFO
                (business_id, shipping_token, address_line1, address_line2, city, state, postal_code, country,
                 packet_count, packet_weight, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    business_id,
                    shipping_token,
                    address['line1'],
                    address.get('line2'),
                    address['city'],
                    address.get('state'),
                    address.get('postal_code'),
                    address.get('country', 'USA'),
                    packet_count,
                    packet_weight,
                    'Pending',  # default status
                    datetime.now()
                ))
                connection.commit()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'shippingToken': shipping_token,
                'status': 'CREATED'
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
