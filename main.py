from fastapi import FastAPI
from app.database import test_connection

app = FastAPI(title="請假系統 API")


@app.on_event("startup")
def startup():
    test_connection()


@app.get("/")
def root():
    return {"success": True, "data": "請假系統 API 運行中"}
