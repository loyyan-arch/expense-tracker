import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from request_logging import setup_request_logging
from routers import auth, transactions, statistics, health


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="个人记账 API")

@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
):
    errors = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": errors}),
    )

setup_request_logging(app)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(statistics.router)
app.include_router(health.router)


@app.get("/")
def home():
    return {"message": "欢迎使用个人记账 API",
            "version": "1.0.0",}
