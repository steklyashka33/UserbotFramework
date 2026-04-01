FROM python:3.11-slim

# Настройка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Установка зависимостей отдельно для кэширования слоев
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода проекта
COPY . .

# Команда для запуска проекта
CMD ["python", "main.py"]
