import json #parse/produce JSON.
import os #read environment variables.
import uuid #read environment variables.
import pymysql #connect to MySQL RDS.
import boto3 #AWS SDK (for EventBridge).
import urllib.request #make HTTP calls to Inventory + Payment APIs.

# ENV VARIABLES 
DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME = os.environ["DB_NAME"]

PAYMENT_API_URL = os.environ["PAYMENT_API_URL"]
INVENTORY_API_URL = os.environ["INVENTORY_API_URL"]   # e.g. .../items
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]

events_client = boto3.client("events")


# It gets the item’s full information from your Inventory service.
def get_inventory_item(item_id):
    url = f"{INVENTORY_API_URL}/{item_id}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        raise Exception(f"Inventory API failed for item {item_id}: {str(e)}")


# Helper: Payment POST 
def call_payment_service(payment_payload, amount):
    body = {
        "cardNumber": payment_payload.get("cardNumber"),
        "expirationDate": payment_payload.get("expirationDate"),
        "cvvCode": payment_payload.get("cvvCode"),
        "cardHolderName": payment_payload.get("cardHolderName"),
        "amount": amount,
    }

    # Create the HTTP POST request
    req = urllib.request.Request(
        PAYMENT_API_URL,
        data=json.dumps(body).encode("utf-8"), # Convert Python dict → JSON string, Convert JSON string → bytes
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    # Send the request and receive the response
    with urllib.request.urlopen(req) as resp:
        resp_data = resp.read().decode("utf-8")
        return json.loads(resp_data)


# DB Connection
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


# MAIN LAMBDA HANDLER
def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
    }

    try:
        raw_body = event.get("body", {})
        if isinstance(raw_body, str):
            body = json.loads(raw_body or "{}")
        else:
            body = raw_body or {}
        customer_name = body["customerName"]
        customer_email = body["customerEmail"]
        shipping = body["shipping"]
        payment = body["payment"]
        items = body["items"]
        
        # INVENTORY VALIDATION (before payment)
        total_amount = 0.0

        for item in items:
            item_id = item["itemId"]
            qty = item["quantity"]

            inv = get_inventory_item(item_id)

            # Check quantity
            available = inv["available_quantity"]
            if qty > available:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({
                        "error": f"Item {inv['name']} has only {available} left"
                    })
                }

            # Add to total order amount
            price = float(inv["unit_price"])
            total_amount += price * qty

        # PAYMENT CALL (synchronous)
        payment_response = call_payment_service(payment, total_amount)
        payment_token = payment_response["paymentToken"]
        payment_status = payment_response["status"]

        if payment_status != "CONFIRMED":
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Payment failed"})
            }

        # DB INSERTS (order + order line items)
        conn = get_connection()

        try:
            with conn.cursor() as cur: #Opens a database cursor (like a “worker” that executes SQL).
                # Get payment_info.id from token
                # You need the id to insert into the order table (payment_info_id_fk)
                cur.execute(
                    "SELECT id FROM PAYMENT_INFO WHERE payment_token = %s",
                    (payment_token,)
                )
                row = cur.fetchone()
                if not row:
                    raise Exception("Payment row missing for token " + payment_token)
                payment_info_id = row["id"]

                # Create order_token
                order_token = str(uuid.uuid4())

                # CUSTOMER_ORDER (shipping_info_id_fk = NULL)
                cur.execute("""
                    INSERT INTO CUSTOMER_ORDER
                    (order_token, customer_name, customer_email,
                     shipping_info_id_fk, payment_info_id_fk, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    order_token,
                    customer_name,
                    customer_email,
                    None,             # shipping is handled later
                    payment_info_id,
                    "New"
                ))
                order_id = cur.lastrowid

                # Insert line items
                for item in items:
                    item_id = item["itemId"]
                    item_name = item["itemName"]
                    qty = item["quantity"]

                    cur.execute("""
                        INSERT INTO CUSTOMER_ORDER_LINE_ITEM
                        (item_id, item_name, quantity, customer_order_id_fk)
                        VALUES (%s, %s, %s, %s)
                    """, (item_id, item_name, qty, order_id))

                conn.commit() #Transaction is saved permanently to the database.        

        except Exception as db_err:
            conn.rollback()
            raise db_err
        finally:
            conn.close()

        # SEND SHIPPING EVENT (asynchronous)
        shipping_address = {
            "line1": shipping.get("addressLine1"),
            "line2": shipping.get("addressLine2"),
            "city": shipping.get("city"),
            "state": shipping.get("state"),
            "postal_code": shipping.get("postalCode"),
            "country": shipping.get("country", "USA")
        }

        events_client.put_events(
            Entries=[{
                "Source": "com.shop.order",
                "DetailType": "order.created",
                "EventBusName": EVENT_BUS_NAME,
                "Detail": json.dumps({
                    "business_id": order_id,
                    "shipping_address": shipping_address,
                    "items": items
                })
            }]
        )

        # RETURN RESPONSE
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "orderId": order_id,
                "orderToken": order_token,
                "paymentToken": payment_token,
                "totalAmount": total_amount,
                "status": "New"
            })
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)})
        }
