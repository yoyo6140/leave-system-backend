import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine, test_connection, Base
from app import models  # 確保所有 model 都被載入
from app.routers import auth
from app.routers.users import router as users_router
from app.routers.leaves import router as leaves_router
from app.routers.quota import router as quota_router
from app.routers.overview import router as overview_router
from app.routers.chat import router as chat_router

from app.routers.kb import router as kb_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    test_connection()
    yield


app = FastAPI(title="請假系統 API", lifespan=lifespan)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://leave-system-frontend-two.vercel.app",
    "https://leaves-system.yoyodev.win",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users_router)
app.include_router(leaves_router)
app.include_router(quota_router)
app.include_router(overview_router)
app.include_router(chat_router)
app.include_router(kb_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": "HTTP_ERROR", "message": exc.detail}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "請求資料格式錯誤"
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": message}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "伺服器發生錯誤"}},
    )


@app.get("/")
def root():
    return {"success": True, "data": "請假系統 API 運行中"}
