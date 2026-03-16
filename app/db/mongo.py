from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    """
    Клас для зберігання глобального стану клієнта бази даних.
    """
    client: AsyncIOMotorClient | None = None
    db = None

# Глобальний об'єкт бази даних, який ми будемо імпортувати в інші модулі
mongodb = Database()

async def connect_to_mongo():
    """Створює підключення до MongoDB."""
    logger.info("Підключення до MongoDB...")
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)
    mongodb.db = mongodb.client[settings.MONGO_DB_NAME]
    logger.info("Успішно підключено до MongoDB!")

async def close_mongo_connection():
    """Закриває підключення до MongoDB."""
    logger.info("Закриття підключення до MongoDB...")
    if mongodb.client:
        mongodb.client.close()
    logger.info("Підключення закрито!")