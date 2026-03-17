def clean_url(url: str) -> str:
    """
    Очищає URL відповідно до вимог: 
    без префіксів мови (/ua/) та без слешу в кінці.
    """
    url = url.strip()
    
    # Видаляємо слеш у кінці, якщо він є
    if url.endswith("/"):
        url = url[:-1]
    
    # Видаляємо маркер мови після домену
    url = url.replace(".ua/ua/", ".ua/")
    url = url.replace(".com.ua/ua/", ".com.ua/")
    
    return url