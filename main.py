import logging

from fastapi import FastAPI

from request_logging import setup_request_logging
from routers import auth, transactions, statistics


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="个人记账 API")

setup_request_logging(app)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(statistics.router)


@app.get("/")
def home():
    return {"message": "欢迎使用个人记账 API"}
