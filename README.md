# atg-inn-check-bot

Telegram-бот на aiogram v3 для проверки компаний по ИНН через DaData API.  
Деплой: Amvera, режим: webhook, веб-фреймворк: FastAPI + uvicorn.

---

## Переменные окружения

| Переменная          | Обязательна | Описание                                      |
|---------------------|-------------|-----------------------------------------------|
| `TELEGRAM_BOT_TOKEN`| ✅           | Токен Telegram-бота (от @BotFather)           |
| `DADATA_API_KEY`    | ✅           | API-ключ DaData                               |
| `DADATA_SECRET_KEY` | ❌           | Secret-ключ DaData (опционально)              |
| `WEBHOOK_URL`       | ✅           | Базовый URL сервиса (без `/tg/webhook`)       |
| `PORT`              | ❌           | Порт сервера (по умолчанию `3000`)            |

---

## Запуск локально

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Задайте переменные окружения
export TELEGRAM_BOT_TOKEN=<ваш токен>
export DADATA_API_KEY=<ваш ключ>
export WEBHOOK_URL=https://your-ngrok-or-domain.example.com
export PORT=3000

# 3. Запустите тесты
pytest -q

# 4. Запустите сервер
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Для локального тестирования webhook можно использовать [ngrok](https://ngrok.com/):

```bash
ngrok http 3000
# Скопируйте HTTPS URL и установите его в WEBHOOK_URL
```

---

## Деплой на Amvera

1. Создайте проект в [Amvera](https://amvera.ru/), выберите тип **«Веб-сервис»**.
2. Добавьте переменные окружения (Secrets) в настройках проекта:
   - `TELEGRAM_BOT_TOKEN`
   - `DADATA_API_KEY`
   - `WEBHOOK_URL` — укажите публичный URL вашего сервиса, например `https://my-bot.amvera.io`
3. Задеплойте код — Amvera автоматически соберёт Docker-образ и запустит:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

Webhook Telegram регистрируется автоматически при старте приложения на endpoint `POST /tg/webhook`.  
Healthcheck доступен по `GET /health`.

---

## Структура проекта

```
app/
  main.py           # FastAPI приложение + webhook wiring + setWebhook
  bot.py            # Handlers, keyboards, FSM states (aiogram v3)
  dadata_client.py  # Async httpx клиент DaData + TTLCache 15 мин
  formatters.py     # Форматирование карточки / деталей / филиалов
  rate_limit.py     # Rate limit: 25 req/sec глобальный + per-user
tests/
  test_validation.py  # Unit-тесты валидации ИНН
  test_formatters.py  # Unit-тесты форматирования карточки
requirements.txt
Dockerfile
```
