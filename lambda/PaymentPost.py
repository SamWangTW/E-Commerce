import json
import pymysql
import os
import uuid
from datetime import datetime

# Database connection info via Lambda environment variables
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        card_number = body.get('cardNumber')
        expiration_date = body.get('expirationDate')
        cvv_code = body.get('cvvCode')
        card_holder = body.get('cardHolderName')
        amount = body.get('amount', 0.0)

        # Derive safe info (don't store sensitive details)
        card_last4 = card_number[-4:] if card_number else None
        payment_method = "CreditCard"
        currency = "USD"
        status = "CONFIRMED"
        payment_token = str(uuid.uuid4())

        # Simulate sending to a payment provider (dummy logic)
        provider_txn_id = f"TXN-{uuid.uuid4()}"

        # Store payment record in MySQL
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )

        with connection.cursor() as cursor:
            sql = """
                INSERT INTO PAYMENT_INFO
                (payment_token, payment_method, card_last4, provider_txn_id, amount, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                payment_token,
                payment_method,
                card_last4,
                provider_txn_id,
                amount,
                currency,
                status
            ))
            connection.commit()

        connection.close()

        # Response to caller (Order Processing Service)
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'paymentToken': payment_token,
                'status': status
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

