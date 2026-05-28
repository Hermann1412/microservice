import os
import requests, time
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
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

# micro services can use a different database than the main application
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
        
@app.get('/orders/{pk}')
def get(pk: str):
    return Order.get(pk)

@app.post('/orders')
async def create(request: Request, background_tasks: BackgroundTasks):
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
    background_tasks.add_task(order_completed, order)

    return order


def order_completed(order: Order):
  time.sleep(5)  # simulate a long process
  order.status = 'completed'
  order.save()
  redis.xadd('order_completed', order.dict(), '*')
