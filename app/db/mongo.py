import os
from motor.motor_asyncio import AsyncIOMotorClient

# Беремо налаштування з docker-compose.yml (або ставимо дефолтні)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "parser_db")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

# Створюємо єдиний екземпляр бази для всього додатку
db_instance = MongoDB()

async def connect_to_mongo():
    """Підключення до бази даних при старті сервера"""
    try:
        db_instance.client = AsyncIOMotorClient(MONGO_URI)
        db_instance.db = db_instance.client[MONGO_DB_NAME]
        print("✅ Успішно підключено до MongoDB!")
    except Exception as e:
        print(f"❌ Помилка підключення до MongoDB: {e}")

async def close_mongo_connection():
    """Відключення від бази даних при зупинці сервера"""
    if db_instance.client:
        db_instance.client.close()
        print("🔌 Відключено від MongoDB.")