from pydantic import BaseModel

class HotlineRawOffer(BaseModel):
    """
    Модель для сирих даних, які ми знайдемо в HTML або JSON Hotline.
    Назви полів можуть бути будь-якими, головне, щоб ми могли їх розпарсити.
    """
    shop_name: str | None = None
    price_raw: str | float | None = None
    title: str | None = None
    condition: str | None = None  # наприклад, "Новий", "Б/В"
    redirect_url: str | None = None  # /go/price/...
    direct_url: str | None = None