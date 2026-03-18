from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.db.mongo import connect_to_mongo, close_mongo_connection

# Lifespan - це сучасний метод FastAPI для виконання коду при старті та зупинці сервера
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Виконується при запуску сервера
    await connect_to_mongo()
    yield
    # Виконується при вимкненні сервера
    await close_mongo_connection()

app = FastAPI(
    title="Product Parser API",
    description="Асинхронний сервіс для парсингу продуктів",
    version="1.0.0",
    lifespan=lifespan
)

# Підключаємо наші роути (ендпоінти)
app.include_router(router)