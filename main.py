from fastapi import FastAPI

from routers import auth, transactions, statistics


app = FastAPI(title="个人记账 API")

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(statistics.router)


@app.get("/")
def home():
    return {"message": "欢迎使用个人记账 API"}
