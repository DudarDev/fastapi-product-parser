from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.routes import router as api_router

# Lifespan - це новий спосіб у FastAPI для керування подіями старту та зупинки
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Логіка, яка виконується при запуску сервера
    await connect_to_mongo()
    
    yield # Тут сервер працює і приймає запити
    
    # Логіка, яка виконується при вимкненні сервера
    await close_mongo_connection()

# Ініціалізація FastAPI
app = FastAPI(
    title="Product Parser API",
    description="Асинхронний сервіс для парсингу продуктів та відгуків (Hotline, Comfy, Brain)",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "API парсера успішно працює! MongoDB підключена."
    }

app.include_router(api_router)    