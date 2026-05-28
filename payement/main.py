# ─────────────────────────────────────────────
# Payment Service  –  runs on port 8001
#
# Responsibilities:
#   • Accept order requests from the frontend
#   • Fetch the product price from the Inventory service
#   • Persist orders in Redis
#   • After a simulated delay, mark the order "completed"
#     and publish an event to the "order_completed" stream
#     so the Inventory consumer can decrement stock
# ─────────────────────────────────────────────

import os
import requests, time
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from redis_om import HashModel, get_redis_connection
from starlette.requests import Request

load_dotenv()  # reads REDIS_HOST, REDIS_PORT, REDIS_PASSWORD from .env

app = FastAPI()

# Allow the React frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)

# Uses the same Redis instance as Inventory for simplicity.
# In production each service would have its own database.
redis = get_redis_connection(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)


# Order model stored as a Redis Hash.
# status lifecycle: pending → completed | refunded
class Order(HashModel):
    product_id: str
    price: float
    fee: float    # always 20 % of price
    total: float  # price + fee
    quantity: int
    status: str

    class Meta:
        database = redis


# ── Routes ───────────────────────────────────

@app.get('/orders/{pk}')
def get(pk: str):
    # The frontend polls this endpoint to watch an order's status change
    return Order.get(pk)


@app.post('/orders')
async def create(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    # body must contain: { "id": <product_pk>, "quantity": <int> }

    # Ask the Inventory service for the current product price
    product = requests.get(f"http://localhost:8000/products/{body['id']}")
    data = product.json()

    order = Order(
        product_id=data['id'],
        price=data['price'],
        fee=data['price'] * 0.2,
        total=data['price'] * 1.2,
        quantity=body.get('quantity', 1),
        status='pending'
    )
    order.save()

    # Process the order in the background so the HTTP response returns immediately.
    # The client can then poll GET /orders/{pk} to watch the status update.
    background_tasks.add_task(order_completed, order)

    return order


# ── Background task ───────────────────────────

def order_completed(order: Order):
    # Simulate payment processing delay
    time.sleep(5)

    order.status = 'completed'
    order.save()

    # Publish the completed order to the Redis stream.
    # The Inventory consumer picks this up and decrements the product stock.
    redis.xadd('order_completed', order.model_dump())
