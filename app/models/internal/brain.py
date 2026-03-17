from pydantic import BaseModel

class BrainRawReview(BaseModel):
    """
    Приблизна структура даних, яку повертає API відгуків Brain.
    """
    rating: int | None = None
    text_good: str | None = None
    text_bad: str | None = None
    text_general: str | None = None
    date_created: str | None = None