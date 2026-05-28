
import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_om import HashModel, get_redis_connection
from starlette.requests import Request

load_dotenv()

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=['http://localhost:3000'],
  allow_methods=['*'],
  allow_headers=['*']
)

#this could have been a different database, micro service can use different database than the main application, but for simplicity we are using redis for both
redis = get_redis_connection(
  host=os.getenv("REDIS_HOST"),
  port=int(os.getenv("REDIS_PORT")),
  password=os.getenv("REDIS_PASSWORD"),
  decode_responses=True
)

class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str  # pending, completed, refunded

    class Meta:
        database = redis


@app.post('/orders')
async def create(request: Request):
    body = await request.json()
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

    return order