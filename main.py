from fastapi import FastAPI
from app.database import engine, test_connection
from app import models

app = FastAPI(title="請假系統 API")


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=engine)
    test_connection()


@app.get("/")
def root():
    return {"success": True, "data": "請假系統 API 運行中"}
