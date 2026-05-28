# Microservice Backend

A Python microservice architecture with two independent services — **Inventory** and **Payment** — communicating asynchronously via Redis Streams.

---

## Architecture Overview

```
┌─────────────────┐         HTTP          ┌──────────────────┐
│   Client / UI   │ ─────────────────────▶│  Inventory API   │
│  (port 3000)    │                       │   (port 8000)    │
└─────────────────┘                       └──────────────────┘
        │                                          │
        │ HTTP POST /orders                        │ Redis (products)
        ▼                                          ▼
┌──────────────────┐                      ┌──────────────────┐
│  Payment API     │                      │ Inventory        │
│  (port 8001)     │──▶ GET /products/{id}│ Consumer         │
└──────────────────┘                      └──────────────────┘
        │                                          ▲
        │ Redis Stream: order_completed             │
        └──────────────────────────────────────────┘
        │
        │ Redis Stream: refund_order (if product missing)
        ▼
┌──────────────────┐
│  Payment         │
│  Consumer        │
└──────────────────┘
```

---

## Services

### 1. Inventory Service (`inventory/`)

Manages products stored in Redis.

**API — runs on `http://localhost:8000`**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| POST | `/products` | Create a new product |
| GET | `/products/{pk}` | Get a single product by ID |
| DELETE | `/products/{pk}` | Delete a product |

**Product schema:**
```json
{
  "id": "01JXXXXXXXXXXXXXX",
  "name": "Product Name",
  "price": 29.99,
  "quantity": 100
}
```

**Consumer (`consumer.py`)** listens on the `order_completed` Redis stream. When an order is completed by the payment service, the consumer:
1. Looks up the product by `product_id`
2. Decrements its `quantity` by the ordered amount
3. Saves the updated product back to Redis
4. If the product no longer exists, publishes a `refund_order` event

---

### 2. Payment Service (`payement/`)

Handles order creation and lifecycle.

**API — runs on `http://localhost:8001`**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Create a new order |
| GET | `/orders/{pk}` | Get an order by ID |

**Request body for `POST /orders`:**
```json
{
  "id": "01JXXXXXXXXXXXXXX",
  "quantity": 2
}
```

**Order schema:**
```json
{
  "pk": "01JXXXXXXXXXXXXXX",
  "product_id": "01JXXXXXXXXXXXXXX",
  "price": 29.99,
  "fee": 5.998,
  "total": 35.988,
  "quantity": 2,
  "status": "pending"
}
```

**Order lifecycle:**
1. `POST /orders` → order created with status `pending`
2. Background task waits 5 seconds (simulates processing)
3. Status updated to `completed` → event published to `order_completed` Redis stream
4. Inventory consumer picks it up and decrements product stock

**Consumer (`consumer.py`)** listens on the `refund_order` Redis stream. When inventory cannot find a product, the consumer:
1. Looks up the order by `pk`
2. Sets its status to `refunded`
3. Saves it back to Redis

---

## Redis Streams (Event Bus)

| Stream | Published by | Consumed by | Purpose |
|--------|-------------|-------------|---------|
| `order_completed` | Payment API | Inventory Consumer | Trigger stock deduction |
| `refund_order` | Inventory Consumer | Payment Consumer | Trigger order refund when product is missing |

---

## Setup & Running

### Prerequisites
- Python 3.8+
- A Redis instance (credentials go in each service's `.env` file)

### Environment Variables

Both services use a `.env` file:
```env
REDIS_HOST=your-redis-host
REDIS_PORT=your-redis-port
REDIS_PASSWORD=your-redis-password
```

### Install Dependencies

```bash
# Inventory
cd inventory
pip install -r requirements.txt

# Payment
cd payement
pip install -r requirements.txt
```

### Run All Services

Open **4 separate terminals**:

```bash
# Terminal 1 — Inventory API
cd inventory
uvicorn main:app --reload

# Terminal 2 — Inventory Consumer
cd inventory
python consumer.py

# Terminal 3 — Payment API
cd payement
uvicorn main:app --reload --port=8001

# Terminal 4 — Payment Consumer
cd payement
python consumer.py
```

---

## Example Usage

**1. Create a product:**
```bash
POST http://localhost:8000/products
Content-Type: application/json

{
  "name": "Laptop",
  "price": 999.99,
  "quantity": 50
}
```

**2. List products to get an ID:**
```bash
GET http://localhost:8000/products
```

**3. Place an order:**
```bash
POST http://localhost:8001/orders
Content-Type: application/json

{
  "id": "<product_id_from_step_2>",
  "quantity": 1
}
```

**4. Check the order status:**
```bash
GET http://localhost:8001/orders/<order_pk>
```
After ~5 seconds the status changes from `pending` → `completed` and the product stock is decremented automatically.
