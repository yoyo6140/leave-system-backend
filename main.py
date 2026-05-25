from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, test_connection, Base
from app import models  # 確保所有 model 都被載入
from app.routers import auth
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    test_connection()
    yield


app = FastAPI(title="請假系統 API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"success": True, "data": "請假系統 API 運行中"}
