from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def clean_url(url: str) -> str:
    """
    Очищає URL відповідно до вимог: 
    - видаляє маркери мови (/ua/, /ru/, /uk/);
    - очищає UTM та трекінгові параметри;
    - прибирає якорі (#);
    - видаляє зайві слеші у кінці.
    """
    url = url.strip()
    if not url:
        return url

    parsed = urlparse(url)
    path = parsed.path
    
    # Видаляємо маркер мови після домену або на початку шляху
    for lang in ('/ua/', '/ru/', '/uk/'):
        if path.startswith(lang):
            path = path[len(lang)-1:]
    path = path.replace('/ua/', '/').replace('/ru/', '/').replace('/uk/', '/')
    
    # Прибираємо слеш у кінці шляху, якщо шлях довший за '/'
    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]

    # Фільтруємо аналітичні параметри (utm_*, ref, gclid, fbclid тощо)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {
        k: v for k, v in query_params.items()
        if not k.lower().startswith("utm_") and k.lower() not in ("ref", "source", "fbclid", "gclid")
    }
    new_query = urlencode(filtered_params, doseq=True)

    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        new_query,
        ""  # видаляємо фрагмент (#)
    ))

    # Видаляємо слеш у кінці, якщо він залишився
    if cleaned.endswith("/"):
        cleaned = cleaned[:-1]

    return cleaned