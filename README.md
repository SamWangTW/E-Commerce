# 🛍️ The Snack Shop — E-Commerce Web Application

A full-stack e-commerce web application for purchasing snacks online, built with **React** on the frontend and **AWS Lambda + API Gateway + RDS (MySQL)** on the backend. Developed as part of **CSE 5234**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Frontend Pages & Components](#frontend-pages--components)
- [Backend — AWS Lambda Functions](#backend--aws-lambda-functions)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [AWS Architecture](#aws-architecture)

---

## Overview

The Snack Shop allows customers to:
- Browse a product inventory fetched from AWS RDS via Lambda
- Search for items by name
- Add items to a cart and go through a multi-step checkout flow (shipping → payment → confirmation)
- View a final order confirmation

Order processing is handled by AWS Lambda functions that validate inventory, process payments, create shipping records, and persist orders to a MySQL database hosted on Amazon RDS. Post-order events (e.g. shipping creation) are triggered via **Amazon EventBridge**.

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 19 | UI framework |
| React Router DOM 7 | Client-side routing |
| React Bootstrap 2 + Bootstrap 5 | UI components & styling |
| Axios | HTTP requests to API Gateway |
| Styled Components | Component-level CSS |
| React Icons | Icon library |

### Backend (AWS)
| Technology | Purpose |
|---|---|
| AWS Lambda (Python) | Serverless business logic |
| AWS API Gateway | REST API endpoints |
| Amazon RDS (MySQL 8.0) | Relational database |
| Amazon EventBridge | Event-driven shipping trigger |
| PyMySQL | Python MySQL connector in Lambda |
| Boto3 | AWS SDK for EventBridge |

---

## Project Structure

```
E-Commerce/
├── public/                    # Static assets (images, favicon)
├── src/
│   ├── App.js                 # Root router — all page routes defined here
│   ├── styles.css             # Global styles
│   ├── components/
│   │   ├── home.js            # Home page with image carousel
│   │   ├── navBar.js          # Top navigation bar
│   │   ├── footer.js          # Footer with links
│   │   ├── carousel.js        # Auto-advancing image carousel
│   │   ├── AboutUs.js         # About Us page with team bios
│   │   ├── ContactUs.js       # Contact page with FAQ accordion
│   │   └── shop/
│   │       ├── purchase.js    # Product listing / shop page
│   │       ├── paymentEntry.js   # Payment form
│   │       ├── shippingEntry.js  # Shipping address form
│   │       ├── viewOrder.js      # Order review page
│   │       └── confirmation.js   # Order confirmation page
├── lambda/
│   ├── InventoryGet.py           # GET all inventory items
│   ├── InventoryItemByIdGet.py   # GET a single item by ID
│   ├── InventoryItemsGet.py      # GET items by name (search)
│   ├── OrderPost.py              # POST — full order processing orchestrator
│   ├── PaymentPost.py            # POST — process & record payment
│   └── ShippingPost.py           # POST — create shipping record (triggered by EventBridge)
├── data/
│   ├── shopdb_ITEM.sql
│   ├── shopdb_CUSTOMER_ORDER.sql
│   ├── shopdb_CUSTOMER_ORDER_LINE_ITEM.sql
│   ├── shopdb_PAYMENT_INFO.sql
│   └── shopdb_SHIPPING_INFO.sql
├── package.json
└── README.md
```

---

## Frontend Pages & Components

| Route | Component | Description |
|---|---|---|
| `/` | `Home` | Landing page with auto-advancing product image carousel |
| `/purchase` | `Purchase` | Browse all inventory items fetched from Lambda |
| `/purchase/shippingEntry` | `ShippingEntry` | Collect customer shipping address |
| `/purchase/paymentEntry` | `PaymentEntry` | Collect credit card details |
| `/purchase/viewOrder` | `ViewOrder` | Review order summary before submitting |
| `/purchase/viewConfirmation` | `Confirmation` | Order confirmation with token |
| `/about` | `AboutUs` | Team bios page |
| `/contact` | `ContactUs` | Contact info and collapsible FAQ |

---

## Backend — AWS Lambda Functions

All Lambda functions connect to **Amazon RDS (MySQL)** via environment variables and are exposed through **AWS API Gateway**.

### `InventoryGet.py`
- **Trigger:** `GET /inventory`
- Returns all items from the `ITEM` table.

### `InventoryItemByIdGet.py`
- **Trigger:** `GET /inventory/items/{id}`
- Returns a single inventory item by its primary key ID.

### `InventoryItemsGet.py`
- **Trigger:** `GET /inventory/items?name={query}`
- Returns items whose names match the provided search query (case-insensitive `LIKE` search).

### `OrderPost.py`
- **Trigger:** `POST /orders`
- Main order orchestration function. It:
  1. Validates inventory availability for all items in the cart
  2. Calculates the total order amount
  3. Calls the **Payment service** (`PaymentPost`) via HTTP
  4. Persists the order and line items to `CUSTOMER_ORDER` and `CUSTOMER_ORDER_LINE_ITEM`
  5. Publishes an event to **Amazon EventBridge** to trigger shipping creation

**Request body:**
```json
{
  "customerName": "Jane Doe",
  "customerEmail": "jane@example.com",
  "shipping": { "line1": "...", "city": "...", "state": "...", "postal_code": "..." },
  "payment": { "cardNumber": "...", "expirationDate": "...", "cvvCode": "...", "cardHolderName": "..." },
  "items": [{ "itemId": 1, "quantity": 2 }]
}
```

### `PaymentPost.py`
- **Trigger:** Called internally by `OrderPost.py` via HTTP POST
- Simulates payment processing, stores only the last 4 digits of the card, and returns a `paymentToken`.

### `ShippingPost.py`
- **Trigger:** Amazon EventBridge event (published by `OrderPost.py`)
- Creates a shipping record in the `SHIPPING_INFO` table with status `Pending` and a unique `shippingToken`.

---

## Database Schema

The database is `shopdb`, hosted on **Amazon RDS MySQL 8.0**. SQL dumps are available in the `data/` directory.

### `ITEM`
| Column | Type | Description |
|---|---|---|
| `ID` | INT (PK) | Auto-increment primary key |
| `ITEM_NUMBER` | INT (UNIQUE) | Product number |
| `NAME` | VARCHAR(255) | Product name |
| `DESCRIPTION` | VARCHAR(500) | Product description |
| `IMAGE` | VARCHAR(1024) | Image URL/path |
| `AVAILABLE_QUANTITY` | INT | Stock quantity (≥ 0) |
| `UNIT_PRICE` | DECIMAL(10,2) | Price per unit (≥ 0) |
| `CATEGORY` | VARCHAR(100) | Product category |

### `CUSTOMER_ORDER`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment primary key |
| `order_token` | CHAR(36) (UNIQUE) | UUID order identifier |
| `customer_name` | VARCHAR(100) | Customer's name |
| `customer_email` | VARCHAR(255) | Customer's email |
| `shipping_info_id_fk` | INT (FK) | References `SHIPPING_INFO` |
| `payment_info_id_fk` | INT (FK) | References `PAYMENT_INFO` |
| `status` | VARCHAR(255) | Order status (default: `New`) |

### `CUSTOMER_ORDER_LINE_ITEM`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment primary key |
| `item_id` | INT | References `ITEM` |
| `item_name` | VARCHAR(255) | Snapshot of item name at purchase |
| `quantity` | INT | Quantity ordered |
| `customer_order_id_fk` | INT (FK) | References `CUSTOMER_ORDER` |

### `PAYMENT_INFO`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment primary key |
| `payment_token` | CHAR(36) (UNIQUE) | UUID payment identifier |
| `payment_method` | VARCHAR(50) | e.g., `CreditCard` |
| `card_last4` | CHAR(4) | Last 4 digits of card |
| `provider_txn_id` | VARCHAR(100) | Simulated provider transaction ID |
| `amount` | DECIMAL(10,2) | Charged amount |
| `currency` | CHAR(3) | e.g., `USD` |
| `status` | VARCHAR(50) | e.g., `CONFIRMED` |

### `SHIPPING_INFO`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment primary key |
| `business_id` | VARCHAR(50) | Internal business reference |
| `shipping_token` | CHAR(36) (UNIQUE) | UUID shipping identifier |
| `address_line1` | VARCHAR(255) | Street address |
| `address_line2` | VARCHAR(255) | Apt/Suite (optional) |
| `city` | VARCHAR(100) | City |
| `state` | VARCHAR(100) | State |
| `postal_code` | VARCHAR(20) | ZIP code |
| `country` | VARCHAR(100) | Country (default: `USA`) |
| `packet_count` | INT | Number of packages |
| `packet_weight` | DECIMAL(10,2) | Total weight |
| `status` | VARCHAR(50) | e.g., `Pending` |

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- npm

### Install & Run

```bash
npm install
npm start
```

The app will run locally at `http://localhost:3000`.

### Build for Production

```bash
npm run build
```

---

## Environment Variables

Each Lambda function requires the following environment variables configured in the **AWS Lambda console**:

| Variable | Description |
|---|---|
| `DB_HOST` | RDS endpoint (e.g. `shopdb.xxxx.us-east-1.rds.amazonaws.com`) |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Database name (e.g. `shopdb`) |
| `PAYMENT_API_URL` | API Gateway URL for the Payment Lambda (`OrderPost` only) |
| `INVENTORY_API_URL` | API Gateway URL for the Inventory Lambda (`OrderPost` only) |
| `EVENT_BUS_NAME` | EventBridge bus name (`OrderPost` only) |

---

## AWS Architecture

```
React Frontend (S3 / Local)
        │
        ▼
AWS API Gateway
   ├── GET  /inventory              → InventoryGet.py
   ├── GET  /inventory/items?name=  → InventoryItemsGet.py
   ├── GET  /inventory/items/{id}   → InventoryItemByIdGet.py
   └── POST /orders                 → OrderPost.py
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                       PaymentPost.py        Amazon EventBridge
                       (HTTP POST)                  │
                              │                     ▼
                              │             ShippingPost.py
                              │
                    All Lambdas ──► Amazon RDS (MySQL — shopdb)
```

---

## References

- [React Bootstrap](https://react-bootstrap.netlify.app/)
- [AWS Lambda Python Docs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [PyMySQL](https://pymysql.readthedocs.io/)
- [Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html)
