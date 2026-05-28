# ─────────────────────────────────────────────
# Inventory Service  –  runs on port 8000
#
# Responsibilities:
#   • Store and manage products in Redis
#   • Expose a REST API for CRUD operations
#   • The Payment service calls GET /products/{pk}
#     when a new order is placed
# ─────────────────────────────────────────────

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_om import HashModel, get_redis_connection

load_dotenv()  # reads REDIS_HOST, REDIS_PORT, REDIS_PASSWORD from .env

app = FastAPI()

# Allow the React frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)

# Each microservice can use its own database.
# Here we reuse Redis for simplicity, but it could be Postgres, MongoDB, etc.
redis = get_redis_connection(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)


# HashModel stores each field as a Redis hash.
# redis-om auto-generates a unique `pk` (ULID) for every saved instance.
class Product(HashModel):
    name: str
    price: float
    quantity: int

    class Meta:
        database = redis


# ── Routes ───────────────────────────────────

@app.get("/products")
def all():
    # all_pks() returns every stored primary key; we format each one
    return [format(pk) for pk in Product.all_pks()]


def format(pk: str):
    # Reshape the raw HashModel into a plain dict with a friendlier "id" key
    product = Product.get(pk)
    return {
        "id": product.pk,
        "name": product.name,
        "price": product.price,
        "quantity": product.quantity
    }


@app.post("/products")
def create(product: Product):
    # FastAPI deserialises the request body into a Product instance automatically
    return product.save()


@app.get("/products/{pk}")
def get(pk: str):
    # Return the same formatted shape used by the list endpoint
    # so the Payment service always receives {"id": ..., "price": ...}
    return format(pk)


@app.delete("/products/{pk}")
def delete(pk: str):
    return Product.delete(pk)
