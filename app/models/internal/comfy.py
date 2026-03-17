from pydantic import BaseModel

class ComfyRawReview(BaseModel):
    """
    Приблизна структура даних, яку повертає API відгуків Comfy.
    """
    mark: int | float | None = None
    plus: str | None = None
    minus: str | None = None
    text: str | None = None
    published_at: str | None = None