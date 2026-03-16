from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Клас конфігурації. Pydantic автоматично зчитає змінні з середовища 
    (наприклад, ті, що ми вказали в docker-compose.yml).
    """
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "parser_db"

    # Налаштування для ігнорування зайвих змінних середовища
    model_config = SettingsConfigDict(extra="ignore")

# Створюємо глобальний екземпляр налаштувань
settings = Settings()