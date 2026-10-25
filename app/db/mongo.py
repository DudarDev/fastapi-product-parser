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
        db_instance.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        # Швидка перевірка доступності сервера MongoDB (таймаут 2 сек замість зависання на 30 сек)
        await db_instance.client.admin.command('ping')
        db_instance.db = db_instance.client[MONGO_DB_NAME]
        print("✅ Успішно підключено до MongoDB!")
    except Exception as e:
        print(f"⚠️ MongoDB недоступна ({e}). Сервіс працює в автономному режимі без збереження в БД.")
        db_instance.db = None

async def close_mongo_connection():
    """Відключення від бази даних при зупинці сервера"""
    if db_instance.client:
        db_instance.client.close()
        print("🔌 Відключено від MongoDB.")

        # ДОДАЄМО ЦЮ ФУНКЦІЮ ДЛЯ DEPENDENCY INJECTION:
async def get_db():
    """
    Генератор, який видає об'єкт бази даних для кожного запиту.
    Це дозволяє легко підміняти базу на тестову (Mock) при написанні Unit-тестів.
    """
    yield db_instance.db