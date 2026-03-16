# Використовуємо офіційний образ Python 3.11
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Забороняємо Python створювати .pyc файли та буферизувати вивід
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Копіюємо файл із залежностями
COPY requirements.txt .

# Встановлюємо Python-залежності
RUN pip install --no-cache-dir -r requirements.txt

# Встановлюємо Playwright та системні залежності для браузера (Chromium)
RUN playwright install --with-deps chromium

# Копіюємо весь код проєкту в контейнер
COPY . .