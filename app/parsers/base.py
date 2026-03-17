from abc import ABC, abstractmethod
import httpx
from typing import List

class BaseParser(ABC):
    """
    Абстрактний базовий клас для всіх парсерів.
    Вимагає від дочірніх класів реалізації конкретних методів.
    """
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @abstractmethod
    async def parse_offers(self, url: str) -> List:
        """Метод для парсингу оферів"""
        pass

    @abstractmethod
    async def parse_comments(self, url: str, date_to: str | None = None) -> List:
        """Метод для парсингу коментарів"""
        pass